from django.db import models


class InferenceResult(models.Model):
    """Almacena resultados de inferencia y metadatos asociados."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_PROCESSED, "Procesado"),
        (STATUS_FAILED, "Fallido"),
    ]

    input_file = models.FileField(upload_to="deteccion/uploads/")
    output_data = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Resultado de inferencia"
        verbose_name_plural = "Resultados de inferencia"

    def __str__(self) -> str:
        return f"Inferencia {self.pk} - {self.get_status_display()}"


class StreamAlert(models.Model):
    """Alerta generada desde el streaming en tiempo real.

    Guarda solo texto y timestamp para mantenerlo ligero en Render Free.
    """

    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alerta de streaming"
        verbose_name_plural = "Alertas de streaming"

    def __str__(self) -> str:  # pragma: no cover - presentacional
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} · {self.text[:48]}"
