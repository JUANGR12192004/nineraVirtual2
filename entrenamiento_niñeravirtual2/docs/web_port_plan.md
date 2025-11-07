# Plan de migración web - Niñera Virtual

## Objetivo
Construir una versión web equivalente a la aplicación de escritorio (Tkinter) que permita desplegarse en Render como servicio web manteniendo autenticación, manejo de cámaras/videos, detección de riesgos, alertas y métricas.

## Componentes actuales (legacy)
- **AuthWindow (Tkinter)**: login/registro, validaciones, mensajes, navegación al dashboard.
- **CCTVMonitoringSystem**: panel principal con columnas para fuentes de video, vista en tiempo real, alertas, métricas, zonas y exportación CSV.
- **Servicios**: detección YOLO, zonas poligonales, alertas Telegram, almacenamiento de imágenes, historial.

## Requerimientos para la versión web
1. **Autenticación web**
   - Formularios de login y registro con estilo equivalente.
   - Persistir usuarios en la misma base SQLite/DB configurada (idealmente migrar a Django auth o crear vistas personalizadas sobre users).
   - Gestión de sesiones Django.

2. **Dashboard web**
   - Layout responsivo con sidebar (fuentes, zonas) y panel principal (video, alertas, métricas).
   - Endpoint(s) para listar/agregar/eliminar fuentes de video (uploads o streams).
   - Componente para visualizar frames en tiempo real (requiere streaming MJPEG o WebSocket).

3. **Procesamiento e inferencia**
   - Servicios Django que reutilicen deteccion/services para ejecutar YOLO.
   - Tareas asíncronas para manejo de video continuo (posible integración con Celery/Redis o servicios websockets).

4. **Alertas y métricas**
   - API REST (Django REST Framework) para registrar y consultar alertas.
   - Tablero web que consuma estas APIs vía fetch/WebSocket.
   - Envío Telegram mantenerse activo desde servicios backend.

5. **Zonas y configuraciones**
   - CRUD web para zonas poligonales por cámara.
   - Persistencia en BD (nueva tabla zones).

6. **Historial y exportación**
   - Página con tabla de alertas y botón CSV.
   - Endpoint para descarga.

7. **Preparación para Render**
   - Variables de entorno (SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL, tokens Telegram).
   - STATIC_ROOT, collectstatic, almacenamiento de modelos .pt (S3 o repositorio).
   - Procfile (web: gunicorn ninera_virtual.wsgi), ender.yaml opcional.
   - Documentación de despliegue en README.

## Entregables intermedios
1. **Infraestructura Django**
   - Integrar Django REST Framework, canales para WebSocket (opcional) y Whitenoise.
   - Configurar settings modulares (local/prod).
2. **UI**
   - Plantillas base con layout (Tailwind/Bootstrap o CSS custom).
   - Componentes HTML: login, register, dashboard, historial.
   - JS para interacciones (fetch, websockets, modales).
3. **Servicios**
   - Vistas/serializers para usuarios (registro manual si no se usa auth).
   - Endpoints para cámaras, alertas, zonas.
   - Worker para inferencia (usar Celery + Redis) o alternativa síncrona (limitada).
4. **Testing y docs**
   - Pruebas unitarias para servicios clave.
   - Guías de ejecución local y despliegue.

## Consideraciones
- Streaming en web: evaluar opencv + StreamingHttpResponse con MJPEG o integrar servicios RTSP?WebRTC.
- Manejo de archivos: usar MEDIA_ROOT configurado, puede necesitar storage en Render (S3).
- Seguridad: proteger endpoints con autenticación (session/csrf o token).
- Rendimiento: Torch en Render puede requerir plan con GPU o uso de CPU (más lento).

## Próximos pasos
1. Migrar autenticación a Django (o crear vistas custom) y crear plantillas equivalentes de login/registro.
2. Construir dashboard estático para replicar el layout (sin funcionalidad) y luego conectar APIs.
3. Implementar endpoints REST para fuentes y alertas, integrando servicios existentes.
4. Añadir streaming básico (al menos reproducción de archivos subidos) y pipeline de inferencia.
5. Ajustar settings para despliegue y documentar el proceso.

