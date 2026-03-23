from pathlib import Path
import os
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG') == 'True'
ALLOWED_HOSTS = ['172.16.0.60', 'localhost', '127.0.0.1', '54.242.113.40']
LOGIN_REDIRECT_URL = '/pos-login/'

# CONFIGURAÇÕES ENVIO DE EMAIL (GMAIL SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
    
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = 'FleetControl <fleetcontrol.app@gmail.com>'
SERVER_EMAIL = EMAIL_HOST_USER

# Outras configurações importantes
EMAIL_TIMEOUT = 30
SERVER_EMAIL = DEFAULT_FROM_EMAIL  # Para emails de erro do Django

# URLs de autenticação
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'


#ASGI_APPLICATION = "fleetcontrol.asgi.application"
ASGI_APPLICATION = "core.asgi.application"


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'core',
    'tailwind',
    'theme',
    #'django_browser_reload',
    'motoristas.apps.MotoristasConfig',
    'movimentacoes',
    'veiculos',
    'contas',
    'contratos',
    'financeiro',
    'solicitacoes.apps.SolicitacoesConfig',
    'channels',
    'solicitantes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #"django_browser_reload.middleware.BrowserReloadMiddleware",

]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],   
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'contas.context_processors.perfil_usuario',
                'contas.context_processors.pendencias_gestor',
                'core.context_processors.solicitacoes_sidebar',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
    }
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True

# Ativa o sistema de internacionalização (i18n) e localização (l10n)
USE_I18N = True 
USE_L10N = True 

# Força o uso do separador de milhares
USE_THOUSAND_SEPARATOR = True 
# Define o separador de milhares como ponto
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','  #
# Define como os números são agrupados (padrão 3 em 3)
NUMBER_GROUPING = (3, 0)

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TAILWIND_APP_NAME = 'theme'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

SESSION_COOKIE_AGE = 60 * 60  # Se o usuário ficar 1h sem mexer → desloga
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False