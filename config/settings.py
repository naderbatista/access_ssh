import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'change_me')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

# ---------------------------------------------------------------------------
# Host SSH remoto — configurado via .env
# ---------------------------------------------------------------------------
SSH_HOST = os.getenv('SSH_HOST', '')
SSH_PORT = int(os.getenv('SSH_PORT', '22'))
TELNET_PORT = int(os.getenv('TELNET_PORT', '23'))

# ---------------------------------------------------------------------------
# Comandos remotos — configuráveis via .env
# Placeholders: {username}, {password}, {group}
# ---------------------------------------------------------------------------
CMD_SU_LOGIN = os.getenv(
    'CMD_SU_LOGIN',
    'su -',
)
CMD_CREATE_USER = os.getenv(
    'CMD_CREATE_USER',
    'useradd -m -s /bin/bash -G {group} {username} && echo {username}:{password} | chpasswd',
)
CMD_CHANGE_PASSWORD = os.getenv(
    'CMD_CHANGE_PASSWORD',
    'echo {username}:{password} | chpasswd',
)
CMD_CHANGE_GROUP = os.getenv(
    'CMD_CHANGE_GROUP',
    'usermod -g {group} {username}',
)
CMD_DELETE_USER = os.getenv(
    'CMD_DELETE_USER',
    'userdel -r {username}',
)

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# Sessão — armazenamento em arquivo para evitar necessidade de banco de dados
# ---------------------------------------------------------------------------
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
_sessions_default = str(BASE_DIR / '.sessions')
SESSION_FILE_PATH = os.getenv('SESSION_FILE_PATH', _sessions_default)
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Sem banco de dados para regras de negócio
DATABASES = {}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
