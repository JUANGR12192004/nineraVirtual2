from django.urls import path

from . import views, web_views

app_name = "deteccion"

urlpatterns = [
    path("", web_views.web_dashboard, name="web_dashboard"),
    path("login/", web_views.web_login, name="web_login"),
    path("register/", web_views.web_register, name="web_register"),
    path("logout/", web_views.web_logout, name="web_logout"),
    path("procesar/", views.upload_view, name="upload"),
]
