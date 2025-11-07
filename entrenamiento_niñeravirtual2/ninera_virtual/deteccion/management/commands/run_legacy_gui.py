from __future__ import annotations

from django.core.management.base import BaseCommand

from ...legacy import run as run_legacy_app


class Command(BaseCommand):
    help = "Ejecuta la aplicación legacy de Niñera Virtual (interfaz Tkinter)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando Niñera Virtual legacy..."))
        run_legacy_app()
