from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InferenceResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("input_file", models.FileField(upload_to="deteccion/uploads/")),
                ("output_data", models.JSONField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("pending", "Pendiente"),
                            ("processed", "Procesado"),
                            ("failed", "Fallido"),
                        ],
                        default="pending",
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-uploaded_at"],
                "verbose_name": "Resultado de inferencia",
                "verbose_name_plural": "Resultados de inferencia",
            },
        ),
    ]

