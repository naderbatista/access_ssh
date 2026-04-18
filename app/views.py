import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings

from app.forms import LoginForm, OperationForm
from app.services.ssh_service import (
    test_ssh_connection, run_ssh_command, run_command_via_su, check_is_root,
)
from app.services.telnet_service import (
    test_telnet_connection, run_telnet_command, run_command_via_su_telnet,
    check_is_root_telnet,
)
from app.services.command_builder import (
    build_create_user_command,
    build_change_password_command,
    build_change_group_command,
    build_delete_user_command,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento ação → função construtora de comando
# Cada função recebe os dados limpos do formulário e retorna a string do comando.
# ---------------------------------------------------------------------------
ACTION_MAP = {
    'create': lambda d: build_create_user_command(
        d['target_username'], d['target_password'], d['group_name'],
    ),
    'password': lambda d: build_change_password_command(
        d['target_username'], d['target_password'],
    ),
    'group': lambda d: build_change_group_command(
        d['target_username'], d['group_name'],
    ),
    'delete': lambda d: build_delete_user_command(
        d['target_username'],
    ),
}

ACTION_LABELS = {
    'create': 'criar usuário',
    'password': 'alterar senha',
    'group': 'alterar grupo',
    'delete': 'excluir usuário',
}


@require_GET
def index(request):
    """Página principal — renderiza a tela única."""
    is_authenticated = request.session.get('ssh_authenticated', False)
    is_root = request.session.get('ssh_is_root', False)
    return render(request, 'app/index.html', {
        'login_form': LoginForm(),
        'operation_form': OperationForm(),
        'is_authenticated': is_authenticated,
        'is_root': is_root,
        'conn_host': settings.SSH_HOST,
        'ssh_port': settings.SSH_PORT,
        'telnet_port': settings.TELNET_PORT,
    })


@require_POST
def ssh_login(request):
    """Valida conexão (SSH ou Telnet) com usuário comum."""
    form = LoginForm(request.POST)

    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'message': 'Preencha todos os campos corretamente.',
            'error': str(form.errors),
        })

    data = form.cleaned_data
    host = data['host'].strip()
    port = data['port']
    protocol = data['protocol']

    try:
        if protocol == 'telnet':
            logger.info("Testando Telnet: usuário '%s' em %s:%d", data['common_username'], host, port)
            test_telnet_connection(host, port, data['common_username'], data['common_password'])
        else:
            logger.info("Testando SSH: usuário comum '%s' em %s:%d", data['common_username'], host, port)
            test_ssh_connection(host, port, data['common_username'], data['common_password'])
    except Exception as exc:
        logger.warning("Falha na conexão %s: %s", protocol.upper(), str(exc))
        return JsonResponse({
            'success': False,
            'message': f'Falha na autenticação {protocol.upper()}.',
            'error': str(exc),
        })

    request.session['ssh_authenticated'] = True
    request.session['ssh_common_user'] = data['common_username']
    request.session['ssh_common_pass'] = data['common_password']
    request.session['conn_host'] = host
    request.session['conn_port'] = port
    request.session['conn_protocol'] = protocol

    # Detectar se o usuário já é root
    try:
        if protocol == 'telnet':
            is_root = check_is_root_telnet(host, port, data['common_username'], data['common_password'])
        else:
            is_root = check_is_root(host, port, data['common_username'], data['common_password'])
    except Exception:
        is_root = False

    request.session['ssh_is_root'] = is_root

    return JsonResponse({
        'success': True,
        'message': 'Autenticação realizada com sucesso.',
        'is_root': is_root,
    })


@require_POST
def execute_action(request):
    """Executa uma ação administrativa via SSH no host remoto."""
    # Verificar autenticação
    if not request.session.get('ssh_authenticated'):
        return JsonResponse({
            'success': False,
            'message': 'Autenticação principal não realizada.',
        }, status=403)

    form = OperationForm(request.POST)
    if not form.is_valid():
        all_errors = form.errors.get('__all__')
        if all_errors:
            msg = '; '.join(str(e) for e in all_errors)
        else:
            msg = '; '.join(
                f"{k}: {', '.join(str(e) for e in v)}"
                for k, v in form.errors.items()
            )
        return JsonResponse({
            'success': False,
            'message': msg or 'Dados inválidos.',
        })

    data = form.cleaned_data
    action = data['action']
    label = ACTION_LABELS.get(action, action)

    # Construir comando
    builder = ACTION_MAP.get(action)
    if not builder:
        return JsonResponse({
            'success': False,
            'message': f'Ação desconhecida: {action}',
        })

    command = builder(data)
    logger.info("Executando ação '%s' para usuário '%s'", label, data['target_username'])

    host = request.session.get('conn_host', settings.SSH_HOST)
    port = request.session.get('conn_port', settings.SSH_PORT)
    protocol = request.session.get('conn_protocol', 'ssh')
    is_root = request.session.get('ssh_is_root', False)
    common_user = request.session.get('ssh_common_user', '')
    common_pass = request.session.get('ssh_common_pass', '')

    if is_root:
        # Usuário logado já é root — executar diretamente
        run_user = common_user
        run_pass = common_pass
    else:
        # Precisa da senha root via modal
        root_pass = data.get('root_password', '').strip()

        if not root_pass:
            return JsonResponse({
                'success': False,
                'message': 'Senha root é obrigatória para executar operações.',
            })

    # Validar grupo antes de executar (ações que usam grupo)
    if action in ('create', 'group') and data.get('group_name'):
        try:
            if is_root:
                if protocol == 'telnet':
                    groups_out, _ = run_telnet_command(host, port, run_user, run_pass, "cut -d: -f1 /etc/group | sort")
                else:
                    groups_out, _ = run_ssh_command(host, port, run_user, run_pass, "cut -d: -f1 /etc/group | sort")
            else:
                if protocol == 'telnet':
                    groups_out, _ = run_command_via_su_telnet(host, port, common_user, common_pass, root_pass, "cut -d: -f1 /etc/group | sort")
                else:
                    groups_out, _ = run_command_via_su(host, port, common_user, common_pass, root_pass, "cut -d: -f1 /etc/group | sort")
            available = [g.strip() for g in groups_out.splitlines() if g.strip()]
            if data['group_name'] not in available:
                return JsonResponse({
                    'success': False,
                    'message': f"O grupo '{data['group_name']}' não existe no servidor.",
                    'group_not_found': True,
                })
        except Exception as exc:
            logger.warning("Falha ao listar grupos: %s", str(exc))

    # Executar via protocolo escolhido
    try:
        if is_root:
            if protocol == 'telnet':
                stdout, stderr = run_telnet_command(host, port, run_user, run_pass, command)
            else:
                stdout, stderr = run_ssh_command(host, port, run_user, run_pass, command)
        else:
            if protocol == 'telnet':
                stdout, stderr = run_command_via_su_telnet(host, port, common_user, common_pass, root_pass, command)
            else:
                stdout, stderr = run_command_via_su(host, port, common_user, common_pass, root_pass, command)
    except Exception as exc:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao {label}.',
            'error': str(exc),
            'data': {'command': command, 'stdout': '', 'stderr': ''},
        })

    # Se stderr não vazio e stdout vazio, considerar falha
    if stderr and not stdout:
        return JsonResponse({
            'success': False,
            'message': f'Falha ao {label}.',
            'data': {'command': command, 'stdout': stdout, 'stderr': stderr},
        })

    return JsonResponse({
        'success': True,
        'message': f'{label.capitalize()} realizado com sucesso.',
        'data': {'command': command, 'stdout': stdout, 'stderr': stderr},
    })


@require_POST
def ssh_logout(request):
    """Encerra a sessão SSH — limpa credenciais da sessão."""
    request.session.flush()
    return JsonResponse({'success': True, 'message': 'Sessão encerrada.'})


@require_POST
def list_groups(request):
    """Lista os grupos disponíveis no servidor remoto."""
    if not request.session.get('ssh_authenticated'):
        return JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=403)

    host = request.session.get('conn_host', settings.SSH_HOST)
    port = request.session.get('conn_port', settings.SSH_PORT)
    protocol = request.session.get('conn_protocol', 'ssh')
    is_root = request.session.get('ssh_is_root', False)
    common_user = request.session.get('ssh_common_user', '')
    common_pass = request.session.get('ssh_common_pass', '')
    group_cmd = "cut -d: -f1 /etc/group | sort"

    try:
        if is_root:
            if protocol == 'telnet':
                stdout, _ = run_telnet_command(host, port, common_user, common_pass, group_cmd)
            else:
                stdout, _ = run_ssh_command(host, port, common_user, common_pass, group_cmd)
        else:
            import json as _json
            try:
                body = _json.loads(request.body)
            except (ValueError, _json.JSONDecodeError):
                body = {}

            root_pass = body.get('root_password', '').strip()
            if not root_pass:
                return JsonResponse({'success': False, 'message': 'Senha root é obrigatória.'})

            if protocol == 'telnet':
                stdout, _ = run_command_via_su_telnet(host, port, common_user, common_pass, root_pass, group_cmd)
            else:
                stdout, _ = run_command_via_su(host, port, common_user, common_pass, root_pass, group_cmd)

        groups = [g.strip() for g in stdout.splitlines() if g.strip()]
        return JsonResponse({'success': True, 'groups': groups})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)})
