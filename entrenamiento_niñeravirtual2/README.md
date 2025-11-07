## Niñera Virtual 2

Estructura base para un proyecto Django enfocado en detección usando modelos PyTorch y una interfaz web ligera.

### Requisitos
- Python 3.10+
- [pipenv](https://pipenv.pypa.io/) o `pip`

#### Instalación rápida
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements-win.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
```

### Variables de entorno
1. Copia `ninera_virtual/.env.example` a `ninera_virtual/.env`.
2. Define `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DATABASE_URL` (por defecto usa SQLite) y las rutas de modelos/medios. Usa `LEGACY_DB_PATH` si quieres forzar la ubicación del SQLite utilizado por el módulo legacy/web.
3. Para despliegues agrega `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` y deja que Render complete `RENDER_EXTERNAL_URL`.

### Migraciones y servidor local
```bash
python ninera_virtual/manage.py migrate
python ninera_virtual/manage.py runserver
```

### Despliegue en Render
El repositorio incluye `render.yaml` en la raíz:
- Crea automáticamente una base de datos Postgres gratuita (`ninera-virtual-db`) y expone su cadena en `DATABASE_URL`.
- Despliega el servicio web con `gunicorn ninera_virtual.wsgi:application --chdir ninera_virtual`.
- Ejecuta `python ninera_virtual/manage.py collectstatic --noinput` durante el build para servir archivos con WhiteNoise.
- Asegura `DJANGO_DEBUG=False`, genera `DJANGO_SECRET_KEY` y define `PYTHON_VERSION`.

Pasos:
1. Sube el repo a GitHub/GitLab.
2. En Render selecciona **New + Blueprint** y apunta al archivo `render.yaml`.
3. Opcional: adjunta un Render Disk si necesitas persistir los modelos `.pt` o la base SQLite del módulo legacy. Configura `LEGACY_DB_PATH` apuntando a ese disco; si se omite, se crea un archivo dentro del workspace (se pierde en cada redeploy).
4. Ejecuta `python ninera_virtual/manage.py migrate` desde el dashboard tras el primer deploy para crear las tablas.

### Interfaz legacy (Tkinter)
El proyecto original de escritorio vive en `ninera_virtual/deteccion/legacy`.
```bash
python ninera_virtual/manage.py run_legacy_gui
```
El módulo reutiliza la base SQLite (`ninera_virtual.db`) y guarda alertas en `media/alertas_img/`.

### Estructura destacada
- `ml_models/`: modelos `.pt` y utilidades de carga.
- `ninera_virtual/`: proyecto Django y app `deteccion`.
- `media/`: archivos subidos (configurable vía `MEDIA_ROOT`).
- `templates/` y `static/`: assets del dashboard web.
- `tests/`: pruebas unitarias.

Adapta este esqueleto según tus necesidades (Docker, CI/CD, etc.). El stack actual es totalmente compatible con despliegues en Render, Railway o cualquier host WSGI.
