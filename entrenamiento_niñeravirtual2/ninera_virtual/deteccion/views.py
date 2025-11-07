from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .forms import UploadForm
from .models import InferenceResult
from .services import get_models, run_inference
from .web_views import get_logged_user


def upload_view(request: HttpRequest) -> HttpResponse:
    """Procesa archivos subidos y muestra el resultado."""
    if not get_logged_user(request):
        return redirect("deteccion:web_login")

    form = UploadForm(request.POST or None, request.FILES or None)
    context = {"form": form, "user": get_logged_user(request)}

    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["file"]
        upload.seek(0)

        inference = InferenceResult.objects.create(
            input_file=upload,
            notes=form.cleaned_data.get("notes", ""),
            status=InferenceResult.STATUS_PENDING,
        )

        try:
            models = get_models()
            payload = run_inference(inference.input_file.path, models)
            inference.output_data = payload
            inference.status = InferenceResult.STATUS_PROCESSED
        except Exception as exc:  # pragma: no cover
            inference.output_data = {"error": str(exc)}
            inference.status = InferenceResult.STATUS_FAILED
            context["model_error"] = str(exc)

        inference.save(update_fields=["output_data", "status"])
        payload_data = inference.output_data or {}
        context.update(
            {
                "result": inference,
                "payload": payload_data,
                "payload_models": payload_data.get("models_used", []),
                "payload_detections": payload_data.get("detections", []),
            }
        )
        return render(request, "deteccion/resultado.html", context)

    return redirect("deteccion:web_dashboard")
