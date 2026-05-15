"""Конфигурация приложения company."""

from django.apps import AppConfig


class CompanyConfig(AppConfig):
    """Конфигурационный класс для приложения company."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "company"
