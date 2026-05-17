"""Главный модуль маршрутизации проекта core."""

from django.urls import include, path

urlpatterns = [
    path('api/', include('api.urls')),
]
