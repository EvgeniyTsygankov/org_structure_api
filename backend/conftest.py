"""Фикстуры для тестирования api приложения."""

from typing import Any

import pytest
from rest_framework.test import APIClient

from company.models import Department, Employee


@pytest.fixture
def api_client() -> APIClient:
    """Фикстура тестового клиента API REST Framework."""
    return APIClient()


@pytest.fixture
def sample_structure() -> dict[str, Any]:
    """Создает тестовую структуру подразделений.

    Формирует трехуровневое дерево и добавляет сотрудника.
    """
    root = Department.objects.create(name='Головной офис')
    child = Department.objects.create(name='Отдел разработки', parent=root)
    sub_child = Department.objects.create(
        name='Backend направление', parent=child
    )

    employee = Employee.objects.create(
        department=sub_child,
        full_name='Сидоров Алексей Петрович',
        position='Backend Developer',
    )

    return {
        'root': root,
        'child': child,
        'sub_child': sub_child,
        'employee': employee,
    }
