from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("deteccion", "0001_initial"),
    ]

    operations = [
        # Asegura el nuevo campo en InferenceResult incluso si no existe 0002_add_output_text
        migrations.AddField(
            model_name="inferenceresult",
            name="output_text",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="StreamAlert",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Alerta de streaming",
                "verbose_name_plural": "Alertas de streaming",
            },
        ),
    ]
