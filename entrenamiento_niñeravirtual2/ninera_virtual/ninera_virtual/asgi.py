import os
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ninera_virtual.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Importar rutas de WS de forma tolerante; si fallan, usar lista vacía sin romper ASGI
try:
    from .routing import websocket_urlpatterns  # type: ignore
except Exception:
    logging.exception("[asgi] No se pudieron importar rutas WS; usando lista vacía")
    websocket_urlpatterns = []  # type: ignore

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
