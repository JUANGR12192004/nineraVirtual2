from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("deteccion", "0002_add_output_text"),
    ]

    operations = [
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
