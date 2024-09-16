"""
WSGI config for graphene_django_cud project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os

from django_ws import get_websocket_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_settings")

application = get_websocket_application()
