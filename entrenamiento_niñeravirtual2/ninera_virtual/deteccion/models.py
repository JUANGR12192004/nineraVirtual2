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
