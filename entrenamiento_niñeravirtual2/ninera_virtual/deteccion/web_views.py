from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.http import StreamingHttpResponse

from .forms import UploadForm, WebLoginForm, WebRegisterForm
from .legacy.config import DatabaseConnection, UserRepository
from .models import InferenceResult, StreamAlert


SESSION_KEY = "legacy_user"


def get_logged_user(request: HttpRequest) -> Dict | None:
    return _user_from_session(request)


def _get_user_repo() -> UserRepository:
    return UserRepository(DatabaseConnection.get_instance())


def _user_from_session(request: HttpRequest) -> Dict | None:
    return request.session.get(SESSION_KEY)


def _login_user(request: HttpRequest, user: Dict) -> None:
    request.session[SESSION_KEY] = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }


def _logout_user(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)


def web_login(request: HttpRequest) -> HttpResponse:
    if _user_from_session(request):
        return redirect("deteccion:web_dashboard")

    form = WebLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        repo = _get_user_repo()
        user = repo.verify_credentials(form.cleaned_data["email"], form.cleaned_data["password"])
        if user:
            _login_user(request, user)
            messages.success(request, f"¡Bienvenido {user['name']}! Has iniciado sesión correctamente.")
            return redirect("deteccion:web_dashboard")
        messages.error(request, "Credenciales inválidas. Revisa tus datos.")
    return render(request, "auth/login.html", {"form": form})


def web_register(request: HttpRequest) -> HttpResponse:
    if _user_from_session(request):
        return redirect("deteccion:web_dashboard")

    form = WebRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        repo = _get_user_repo()
        try:
            repo.create_user(
                form.cleaned_data["name"],
                form.cleaned_data["email"],
                form.cleaned_data["password"],
            )
        except Exception as exc:
            messages.error(request, f"No se pudo crear la cuenta: {exc}")
        else:
            messages.success(request, "Cuenta creada con éxito. Inicia sesión con tus datos.")
            return redirect("deteccion:web_login")
    return render(request, "auth/register.html", {"form": form})


def web_logout(request: HttpRequest) -> HttpResponse:
    _logout_user(request)
    messages.info(request, "Sesión finalizada.")
    return redirect("deteccion:web_login")


def export_alerts_csv(request: HttpRequest) -> HttpResponse:
    """Exporta alertas de streaming a CSV sin bloquear (streaming)."""
    def rows():
        yield "timestamp,alerta\n"
        for a in StreamAlert.objects.order_by("-created_at").iterator():
            # Escapar comas y saltos de línea simples
            text = (a.text or "").replace("\n", " ").replace(",", ";")
            yield f"{a.created_at:%Y-%m-%d %H:%M:%S},{text}\n"

    resp = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="alertas_streaming.csv"'
    return resp


@dataclass
class MetricCounters:
    total: int = 0
    knife: int = 0
    stairs: int = 0
    stove: int = 0
    pot: int = 0
    zone: int = 0
    high: int = 0
    scissors: int = 0

    def bump(self, detection: str) -> None:
        label = detection.lower()
        self.total += 1
        if "cuchillo" in label or "knife" in label:
            self.knife += 1
        if "escalera" in label or "stairs" in label:
            self.stairs += 1
        if "estufa" in label or "cocina" in label:
            self.stove += 1
        if "olla" in label or "pot" in label:
            self.pot += 1
        if "zona" in label:
            self.zone += 1
        if "sobre" in label or "alto" in label:
            self.high += 1
        if "tijera" in label or "scissors" in label:
            self.scissors += 1


def _build_metrics(results: List[InferenceResult]) -> MetricCounters:
    counters = MetricCounters()
    for result in results:
        payload = result.output_data or {}
        detections = payload.get("detections") or []
        for det in detections:
            counters.bump(str(det))
        if payload.get("error"):
            counters.total += 1
    return counters


def _build_metrics_from_alerts(alerts: List[StreamAlert]) -> MetricCounters:
    counters = MetricCounters()
    for a in alerts:
        text = (a.text or "").lower()
        # Heurística simple por palabras clave
        if not text:
            continue
        # contar por clases conocidas
        for token in [
            "knife",
            "cuchillo",
            "kitchen",
            "cocina",
            "cooker",
            "stove",
            "horno",
            "oven",
            "pot",
            "olla",
            "stairs",
            "escalera",
            "scissors",
            "tijera",
        ]:
            if token in text:
                counters.bump(token)
        counters.total += 1
    return counters


def web_dashboard(request: HttpRequest) -> HttpResponse:
    user = _user_from_session(request)
    if not user:
        return redirect("deteccion:web_login")

    recent_alerts = list(StreamAlert.objects.order_by("-created_at")[:12])
    recent_results = InferenceResult.objects.order_by("-uploaded_at")[:3]
    # Métricas a partir de alertas persistidas (stream)
    metrics = _build_metrics_from_alerts(recent_alerts)
    context = {
        "user": user,
        "alerts": recent_alerts or recent_results,
        "metrics": metrics,
        "upload_form": UploadForm(),
    }
    return render(request, "dashboard/index.html", context)
