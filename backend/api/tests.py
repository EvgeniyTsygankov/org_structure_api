"""Тесты для бизнес-логики и эндпоинтов api приложения."""

from typing import Any, cast

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from company.models import Department, Employee

pytestmark = pytest.mark.django_db


def test_get_department_tree_recursion(
    api_client: APIClient, sample_structure: dict[str, Any]
) -> None:
    """Тест рекурсивного вывода дерева компании."""
    root_id = sample_structure['root'].pk
    url = reverse('api:department-detail', kwargs={'pk': root_id})

    response = cast(
        Response,
        api_client.get(url, {'depth': 3, 'include_employees': 'true'}),
    )

    assert response.status_code == status.HTTP_200_OK
    data = cast(dict[str, Any], response.data)

    assert data['id'] == root_id
    assert len(data['children']) == 1

    child_data = data['children'][0]
    assert child_data['id'] == sample_structure['child'].pk
    assert len(child_data['children']) == 1

    sub_child_data = child_data['children'][0]
    assert sub_child_data['id'] == sample_structure['sub_child'].pk
    assert len(sub_child_data['employees']) == 1
    assert (
        sub_child_data['employees'][0]['full_name']
        == 'Сидоров Алексей Петрович'
    )


def test_unique_name_per_parent_validation(
    api_client: APIClient, sample_structure: dict[str, Any]
) -> None:
    """Тест валидатора уникальности имени подразделения у одного родителя."""
    url = reverse('api:department-create')

    payload = {
        'name': 'Отдел разработки',
        'parent_id': sample_structure['root'].pk,
    }

    response = cast(
        Response, api_client.post(url, data=payload, format='json')
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_circular_dependency_protection(
    api_client: APIClient, sample_structure: dict[str, Any]
) -> None:
    """Тест защиты от создания циклической зависимости в дереве при PATCH."""
    root_id = sample_structure['root'].pk
    sub_child_id = sample_structure['sub_child'].pk

    url = reverse('api:department-detail', kwargs={'pk': root_id})

    payload = {'parent_id': sub_child_id}

    response = cast(
        Response, api_client.patch(url, data=payload, format='json')
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_delete_department_mode_reassign(
    api_client: APIClient, sample_structure: dict[str, Any]
) -> None:
    """Тест удаления подразделения в режиме reassign."""
    root_id = sample_structure['root'].pk
    sub_child_id = sample_structure['sub_child'].pk

    base_url = reverse('api:department-detail', kwargs={'pk': sub_child_id})
    url = f'{base_url}?mode=reassign&reassign_to_department_id={root_id}'

    response = cast(Response, api_client.delete(url))
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert not Department.objects.filter(id=sub_child_id).exists()

    employee = Employee.objects.get(id=sample_structure['employee'].pk)
    assert employee.department == sample_structure['root']
