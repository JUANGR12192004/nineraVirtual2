from django.contrib import admin

from . import models


@admin.register(models.InferenceResult)
class InferenceResultAdmin(admin.ModelAdmin):
    list_display = ("id", "uploaded_at", "status")
    search_fields = ("status",)
    list_filter = ("status", "uploaded_at")
