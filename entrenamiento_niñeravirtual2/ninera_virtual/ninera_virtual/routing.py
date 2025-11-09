from django.urls import path

from deteccion.routing import websocket_urlpatterns as deteccion_ws


websocket_urlpatterns = [
    *deteccion_ws,
]

