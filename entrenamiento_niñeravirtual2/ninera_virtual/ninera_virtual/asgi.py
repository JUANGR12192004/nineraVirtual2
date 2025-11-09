import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ninera_virtual.settings")

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application
    from .routing import websocket_urlpatterns

    django_asgi_app = get_asgi_application()
    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": URLRouter(websocket_urlpatterns),
        }
    )
except Exception:
    # Fallback sin Channels
    from django.core.asgi import get_asgi_application

    application = get_asgi_application()
