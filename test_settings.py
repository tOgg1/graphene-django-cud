import os

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = 1
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    'graphene_django_cud',
    'graphene_django_cud.tests',
    'graphene_django',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'django_test.sqlite',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
    },
]

GRAPHENE = {
    'SCHEMA': 'graphene_django_cud.tests.schema.schema'
}

STATIC_URL = '/static/'
STATIC_ROOT = 'static/'
ROOT_URLCONF = 'graphene_django_cud.tests.urls'
