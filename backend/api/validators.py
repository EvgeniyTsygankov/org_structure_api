"""Модуль валидаторов для api приложения."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from company.models import Department
from core.constants import (
    DEPARTMENT_NAME_MAX_LEN,
    EMPLOYEE_FULL_NAME_MAX_LEN,
    EMPLOYEE_POSITION_MAX_LEN,
)


def validate_name_department(value: str) -> str:
    """Валидация наименования подразделения."""
    cleaned_value: str = value.strip()
    if not cleaned_value:
        raise serializers.ValidationError(
            'Наименование подразделения не должно быть пустым.'
        )
    if len(cleaned_value) < 1 or len(cleaned_value) > DEPARTMENT_NAME_MAX_LEN:
        raise serializers.ValidationError(
            'Наименование подразделения должно содержать '
            f'от 1 до {DEPARTMENT_NAME_MAX_LEN} символов. '
            f'Сейчас {len(cleaned_value)}'
        )
    return cleaned_value


def validate_not_self_parent(
    instance: Department | None, parent: Department | None
) -> Department | None:
    """Проверяет, что подразделение не является собственным родителем."""
    if instance and parent and instance.pk == parent.pk:
        raise serializers.ValidationError(
            'Невозможно установить подразделение как собственное '
            'родительское подразделение.'
        )
    return parent


def validate_no_circular_dependency(
    instance: Department | None, parent: Department | None
) -> Department | None:
    """Проверяет, не создаст ли новый parent циклическую зависимость."""
    if instance and parent:
        current: Department | None = parent
        while current:
            if current.pk == instance.pk:
                raise serializers.ValidationError(
                    'Невозможно родительское подразделение сделать потомком.'
                )
            current = current.parent
    return parent


def validate_unique_name_per_parent(
    name: str, parent: Department | None, instance: Department | None = None
) -> str:
    """Проверяет уникальность наименования в рамках одного подразделения."""
    queryset = Department.objects.filter(name=name, parent=parent)
    if instance:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise serializers.ValidationError(
            'Аналогичное наименование потомка уже существует под '
            'текущим родительским подразделением.'
        )
    return name


def validate_full_name_employee(value: str) -> str:
    """Валидация ФИО сотрудника."""
    cleaned_value: str = value.strip()
    if not cleaned_value:
        raise serializers.ValidationError(
            'ФИО сотрудника не должно быть пустым.'
        )
    if (
        len(cleaned_value) < 1
        or len(cleaned_value) > EMPLOYEE_FULL_NAME_MAX_LEN
    ):
        raise serializers.ValidationError(
            f'ФИО должно содержать от 1 до {EMPLOYEE_FULL_NAME_MAX_LEN} '
            f'символов. Сейчас {len(cleaned_value)}'
        )
    return cleaned_value


def validate_position_employee(value: str) -> str:
    """Валидация должности сотрудника."""
    cleaned_value: str = value.strip()
    if not cleaned_value:
        raise serializers.ValidationError(
            'Поле должности сотрудника не должно быть пустым.'
        )
    if (
        len(cleaned_value) < 1
        or len(cleaned_value) > EMPLOYEE_POSITION_MAX_LEN
    ):
        raise serializers.ValidationError(
            'Поле должности сотрудника должно содержать от 1 до '
            f'{EMPLOYEE_POSITION_MAX_LEN} символов. '
            f'Сейчас {len(cleaned_value)}'
        )
    return cleaned_value


def validate_department_deletion(
    mode: str, reassign_id_param: str | None, current_department_id: int
) -> int | None:
    """Валидирует параметры удаления подразделения.

    Возвращает ID подразделения для переназначения сотрудников или None.
    """
    if mode not in {'cascade', 'reassign'}:
        raise ValidationError(
            {'mode': 'Допустимые режимы: "cascade" или "reassign".'}
        )

    if mode == 'cascade':
        return None

    if not reassign_id_param:
        raise ValidationError(
            {
                'reassign_to_department_id': 'Параметр обязателен при '
                'mode=reassign.'
            }
        )

    try:
        reassign_id: int = int(reassign_id_param)
    except ValueError:
        raise ValidationError(
            {'reassign_to_department_id': 'ID должен быть числом.'}
        ) from None

    if reassign_id == current_department_id:
        raise ValidationError(
            {
                'reassign_to_department_id': 'Нельзя переводить сотрудников в '
                ' удаляемый отдел.'
            }
        )

    if not Department.objects.filter(id=reassign_id).exists():
        raise ValidationError(
            {
                'reassign_to_department_id': 'Подразделение с '
                f'id={reassign_id} не существует.'
            }
        )

    return reassign_id
