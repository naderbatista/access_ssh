import logging
import re
import time
import paramiko

logger = logging.getLogger(__name__)

# Timeout padrão para conexão e execução (em segundos)
_CONNECT_TIMEOUT = 10
_EXEC_TIMEOUT = 30

# Regex para remover sequências ANSI/escape do terminal
_ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?\x07|\r')


def _strip_ansi(text: str) -> str:
    """Remove sequências de escape ANSI e \r do texto."""
    return _ANSI_RE.sub('', text)


def _create_client(host: str, port: int, username: str, password: str) -> paramiko.SSHClient:
    """Cria e retorna um SSHClient conectado."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=port,
        username=username,
        password=password,
        timeout=_CONNECT_TIMEOUT,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def test_ssh_connection(host: str, port: int, username: str, password: str) -> bool:
    """Testa se as credenciais estão corretas abrindo e fechando uma conexão."""
    client = _create_client(host, port, username, password)
    try:
        transport = client.get_transport()
        if transport and transport.is_active():
            return True
        raise Exception('Transporte SSH inativo após conexão.')
    finally:
        client.close()


def check_is_root(host: str, port: int, username: str, password: str) -> bool:
    """Verifica se o usuário conectado é root (UID 0)."""
    out, _ = run_ssh_command(host, port, username, password, 'id -u')
    return out.strip() == '0'


def run_ssh_command(
    host: str, port: int, username: str, password: str, command: str,
) -> tuple[str, str]:
    """Executa um comando remoto e retorna (stdout, stderr) como strings."""
    client = _create_client(host, port, username, password)
    try:
        logger.info("Executando comando SSH em %s@%s:%d", username, host, port)
        stdin, stdout, stderr = client.exec_command(command, timeout=_EXEC_TIMEOUT)
        stdin.close()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        return out, err
    finally:
        client.close()


def run_command_via_su(
    host: str, port: int,
    common_user: str, common_pass: str,
    root_pass: str,
    command: str,
) -> tuple[str, str]:
    """Executa um comando remoto usando 'su' para elevar a root."""
    from django.conf import settings as _settings

    su_cmd = _settings.CMD_SU_LOGIN

    marker_ready = '___SHELL_READY___'
    marker_verify = '___SU_OK___'
    marker_done = '___CMD_DONE___'

    client = _create_client(host, port, common_user, common_pass)
    try:
        shell = client.invoke_shell(width=200, height=50)
        shell.settimeout(_EXEC_TIMEOUT)

        time.sleep(1.0)
        _recv_all(shell)

        shell.send("bind 'set enable-bracketed-paste off' 2>/dev/null; "
                    "printf '%s\\n'\n" % marker_ready)
        raw = _wait_for(shell, marker_ready, timeout=5)
        logger.debug("Shell pronto: %s", _strip_ansi(raw)[-100:])
        time.sleep(0.3)
        _recv_all(shell)

        logger.info("Enviando: %s", su_cmd)
        shell.send(su_cmd + '\n')

        pw_output = _wait_for(shell, 'assword', timeout=15)
        pw_clean = _strip_ansi(pw_output)
        logger.debug("Prompt de senha recebido: %s", pw_clean[-100:])

        if 'assword' not in pw_clean.lower():
            raise Exception(
                'Prompt de senha do su não apareceu. '
                f'Saída recebida: {pw_clean[-200:]}'
            )

        shell.send(root_pass + '\n')

        time.sleep(2.0)
        auth_output = _strip_ansi(_recv_all(shell))
        logger.debug("Saída pós-senha: %s", auth_output[-200:])

        auth_lower = auth_output.lower()
        for fail_word in ('failure', 'falha', 'incorrect', 'denied', 'wrong password',
                          'authentication failure', 'su: permission denied'):
            if fail_word in auth_lower:
                raise Exception(f'Falha na autenticação root via su: {auth_output.strip()}')

        shell.send(f"echo {marker_verify}$(id -u)\n")
        verify_raw = _wait_for(shell, marker_verify, timeout=10)
        verify_clean = _strip_ansi(verify_raw)
        logger.debug("Saída verificação: %s", verify_clean)

        uid = ''
        for line in verify_clean.splitlines():
            line_s = line.strip()

            if 'echo' in line_s or '$(' in line_s:
                continue
            if marker_verify in line_s:
                uid = line_s.split(marker_verify)[-1].strip()
                break

        if uid != '0':
            logger.error("Verificação de root falhou: id -u retornou '%s'", uid)
            raise Exception(
                f'su executado mas não elevou para root. '
                f'id -u retornou: {uid or "(vazio)"}. '
                'Verifique a senha root.'
            )

        logger.info("Confirmado root (id -u=0). Executando comando.")

        shell.send(command + '\n')
        time.sleep(0.5)

        shell.send(f"echo {marker_done}$?\n")

        cmd_raw = _wait_for(shell, marker_done, timeout=_EXEC_TIMEOUT)
        cmd_clean = _strip_ansi(cmd_raw)

        if marker_done not in cmd_clean:
            logger.warning("Timeout esperando marcador de fim. Saída parcial: %s", cmd_clean[-300:])

        stdout_lines = []
        exit_code = 0
        cmd_stripped = command.strip()

        for line in cmd_clean.splitlines():
            line_s = line.strip()

            if marker_done in line_s:
                after = line_s.split(marker_done)[-1].strip()
                if after.isdigit():
                    exit_code = int(after)
                break

            if not line_s:
                continue
            if line_s == cmd_stripped:
                continue
            if marker_verify in line_s or marker_done in line_s:
                continue
            if f'echo {marker_done}' in line_s or f'echo {marker_verify}' in line_s:
                continue

            if re.match(r'^.*[@:~]\s*[#$%]\s*$', line_s):
                continue

            stdout_lines.append(line)

        stdout_text = '\n'.join(stdout_lines).strip()
        stderr_text = ''

        if exit_code != 0:
            stderr_text = f'Comando retornou código de saída {exit_code}'

        return stdout_text, stderr_text

    finally:
        client.close()


def _recv_all(shell, bufsize: int = 65536) -> str:

    data = ''
    while shell.recv_ready():
        data += shell.recv(bufsize).decode('utf-8', errors='replace')
    return data


def _wait_for(shell, needle: str, timeout: int = 15, bufsize: int = 65536) -> str:

    collected = ''
    deadline = time.time() + timeout
    while time.time() < deadline:
        if shell.recv_ready():
            chunk = shell.recv(bufsize).decode('utf-8', errors='replace')
            collected += chunk
            if needle in _strip_ansi(collected):
                return collected
        time.sleep(0.15)
    # Timeout — retornar o que temos
    return collected
