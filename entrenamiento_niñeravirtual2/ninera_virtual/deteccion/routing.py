from django.urls import path

from .consumers_ws import StreamConsumer


websocket_urlpatterns = [
    path("ws/stream", StreamConsumer.as_asgi()),
]
