import shlex
from django.conf import settings


def _q(value: str) -> str:
    return shlex.quote(value)


def build_create_user_command(username: str, password: str, group: str) -> str:
    return settings.CMD_CREATE_USER.format(
        username=_q(username),
        password=_q(password),
        group=_q(group),
    )


def build_change_password_command(username: str, new_password: str) -> str:
    return settings.CMD_CHANGE_PASSWORD.format(
        username=_q(username),
        password=_q(new_password),
    )


def build_change_group_command(username: str, new_group: str) -> str:
    return settings.CMD_CHANGE_GROUP.format(
        username=_q(username),
        group=_q(new_group),
    )


def build_delete_user_command(username: str) -> str:
    return settings.CMD_DELETE_USER.format(
        username=_q(username),
    )
