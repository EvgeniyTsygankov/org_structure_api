"""Маршруты для api приложения."""

from django.urls import path

from api.views import (
    DepartmentCreateView,
    DepartmentDetailUpdateDeleteView,
    EmployeeCreateView,
)

app_name = 'api'

urlpatterns = [
    path(
        'departments/',
        DepartmentCreateView.as_view(),
        name='department-create',
    ),
    path(
        'departments/<int:pk>/',
        DepartmentDetailUpdateDeleteView.as_view(),
        name='department-detail',
    ),
    path(
        'departments/<int:pk>/employees/',
        EmployeeCreateView.as_view(),
        name='employee-create',
    ),
]
