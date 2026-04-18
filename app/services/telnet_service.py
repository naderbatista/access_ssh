import logging
import re
import time

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 10
_EXEC_TIMEOUT = 30

_ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?\x07|\r')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


def _get_telnet():
    try:
        import telnetlib
        return telnetlib
    except ImportError:
        raise RuntimeError(
            'Módulo telnetlib não disponível neste ambiente Python. '
            'Utilize o protocolo SSH ou Python < 3.13.'
        )


def _send(tn, cmd: str) -> None:
    tn.write(cmd.encode('utf-8') + b'\n')


def _read_all(tn) -> bytes:
    time.sleep(0.25)
    try:
        return tn.read_very_eager()
    except Exception:
        return b''


def _wait_for(tn, marker: bytes, timeout: int = 10) -> bytes:
    return tn.read_until(marker, timeout=timeout)


def _create_client(host: str, port: int, username: str, password: str):
    """Cria uma conexão Telnet e realiza o login interativo."""
    telnetlib = _get_telnet()
    tn = telnetlib.Telnet(host, port, timeout=_CONNECT_TIMEOUT)

    # Aguardar prompt de login  (ex: "login:", "Login:")
    out = tn.read_until(b'login:', timeout=_CONNECT_TIMEOUT)
    if not out:
        tn.close()
        raise Exception('Timeout aguardando prompt de login Telnet.')

    _send(tn, username)

    # Aguardar prompt de senha
    out = tn.read_until(b'assword:', timeout=_CONNECT_TIMEOUT)
    if not out:
        tn.close()
        raise Exception('Timeout aguardando prompt de senha Telnet.')

    _send(tn, password)

    # Aguardar shell do usuário
    time.sleep(1.5)
    welcome = _read_all(tn).decode('utf-8', errors='replace')

    lower = welcome.lower()
    if 'login incorrect' in lower or 'login:' in lower or 'authentication failure' in lower:
        tn.close()
        raise Exception('Falha na autenticação Telnet: usuário ou senha incorretos.')

    return tn


def test_telnet_connection(host: str, port: int, username: str, password: str) -> bool:
    """Testa a conexão Telnet, retorna True se bem-sucedida."""
    tn = _create_client(host, port, username, password)
    try:
        return True
    finally:
        try:
            _send(tn, 'exit')
        except Exception:
            pass
        tn.close()


def check_is_root_telnet(host: str, port: int, username: str, password: str) -> bool:
    """Verifica se o usuário conectado via Telnet é root (UID 0)."""
    out, _ = run_telnet_command(host, port, username, password, 'id -u')
    return out.strip() == '0'


def run_telnet_command(
    host: str, port: int, username: str, password: str, command: str,
) -> tuple[str, str]:
    """Executa um comando remoto via Telnet e retorna (stdout, stderr)."""
    tn = _create_client(host, port, username, password)
    marker = '___TELNET_CMD_DONE___'
    try:
        _read_all(tn)
        _send(tn, command)
        _send(tn, f"echo '{marker}'")

        raw = _wait_for(tn, marker.encode(), timeout=_EXEC_TIMEOUT)
        time.sleep(0.3)
        extra = _read_all(tn)

        full = _strip_ansi((raw + extra).decode('utf-8', errors='replace'))
        # Extrair saída antes do marcador, descartar o próprio comando
        parts = full.split(marker)
        stdout = parts[0].strip()
        # Remover a linha do próprio echo command (primeira linha)
        lines = stdout.splitlines()
        if lines and command.strip() in lines[0]:
            lines = lines[1:]
        return '\n'.join(lines).strip(), ''
    finally:
        try:
            _send(tn, 'exit')
        except Exception:
            pass
        tn.close()


def run_command_via_su_telnet(
    host: str, port: int,
    common_user: str, common_pass: str,
    root_pass: str,
    command: str,
) -> tuple[str, str]:
    """Executa um comando via Telnet elevando privilégios com 'su'."""
    from django.conf import settings as _settings
    su_cmd = _settings.CMD_SU_LOGIN

    marker_su_ok = '___SU_TELNET_OK___'
    marker_done = '___TELNET_DONE___'

    tn = _create_client(host, port, common_user, common_pass)
    try:
        _read_all(tn)

        # Desabilitar bracketed-paste para evitar ruído no terminal
        _send(tn, "bind 'set enable-bracketed-paste off' 2>/dev/null")
        time.sleep(0.4)
        _read_all(tn)

        # Elevar para root via su
        _send(tn, su_cmd)
        pw_raw = _wait_for(tn, b'assword:', timeout=10)
        if not pw_raw:
            raise Exception('Timeout aguardando prompt de senha do su.')

        _send(tn, root_pass)
        time.sleep(0.8)
        _read_all(tn)

        # Verificar se a elevação foi bem-sucedida
        _send(tn, f"printf '%s\\n' '{marker_su_ok}'")
        su_out = _wait_for(tn, marker_su_ok.encode(), timeout=5)
        if marker_su_ok not in _strip_ansi(su_out.decode('utf-8', errors='replace')):
            raise Exception('Falha na elevação su: senha root incorreta ou sem permissão.')

        _read_all(tn)

        # Executar o comando
        _send(tn, command)
        _send(tn, f"echo '{marker_done}'")

        raw = _wait_for(tn, marker_done.encode(), timeout=_EXEC_TIMEOUT)
        time.sleep(0.3)
        extra = _read_all(tn)

        full = _strip_ansi((raw + extra).decode('utf-8', errors='replace'))
        parts = full.split(marker_done)
        stdout = parts[0].strip()
        # Remover a linha do próprio echo do command
        lines = stdout.splitlines()
        if lines and command.strip() in lines[0]:
            lines = lines[1:]
        return '\n'.join(lines).strip(), ''
    finally:
        try:
            _send(tn, 'exit')
            _send(tn, 'exit')
        except Exception:
            pass
        tn.close()
