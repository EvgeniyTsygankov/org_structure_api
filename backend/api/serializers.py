"""Сериализаторы для приложения api."""

from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from api.validators import (
    validate_full_name_employee,
    validate_name_department,
    validate_no_circular_dependency,
    validate_not_self_parent,
    validate_position_employee,
    validate_unique_name_per_parent,
)
from company.models import Department, Employee


class EmployeeListSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор для вывода сотрудников в дереве."""

    class Meta:
        """Мета-класс сериализатора EmployeeList."""

        model = Employee
        fields = ('id', 'full_name', 'position', 'created_at')


class EmployeeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания сотрудников."""

    full_name = serializers.CharField(validators=[validate_full_name_employee])
    position = serializers.CharField(validators=[validate_position_employee])
    department_id = serializers.PrimaryKeyRelatedField(
        source='department',
        read_only=True,
    )

    class Meta:
        """Мета-класс для настройки сериализатора EmployeeCreate."""

        model = Employee
        fields = (
            'id',
            'full_name',
            'position',
            'department_id',
            'hired_at',
            'created_at',
        )
        read_only_fields = ('created_at',)


class DepartmentBaseSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для подразделений."""

    name = serializers.CharField(validators=[validate_name_department])
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent', read_only=True
    )

    class Meta:
        """Мета-класс для настройки сериализатора DepartmentBase."""

        model = Department
        fields = ('id', 'name', 'parent_id', 'created_at')
        read_only_fields = ('created_at',)


class DepartmentCreateSerializer(DepartmentBaseSerializer):
    """Сериализатор для создания подразделений."""

    class Meta(DepartmentBaseSerializer.Meta):
        """Наследуем настройки Meta от базового класса."""

        pass

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Валидация при создании нового подразделения."""
        attrs = super().validate(attrs)

        name: str = attrs.get('name', '')
        parent: Department | None = attrs.get('parent')

        validate_unique_name_per_parent(name, parent)

        return attrs


class DepartmentUpdateSerializer(DepartmentBaseSerializer):
    """Сериализатор для обновления подразделений."""

    class Meta(DepartmentBaseSerializer.Meta):
        """Наследуем настройки Meta от базового класса."""

        pass

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Валидация при обновлении (защита дерева от циклов)."""
        attrs = super().validate(attrs)
        instance: Department = self.instance  # type: ignore[assignment]

        name: str = attrs.get('name', instance.name)
        parent: Department | None = attrs.get('parent', instance.parent)

        validate_not_self_parent(instance, parent)
        validate_no_circular_dependency(instance, parent)
        validate_unique_name_per_parent(name, parent, instance)

        return attrs


class DepartmentTreeSerializer(serializers.ModelSerializer):
    """Сериализатор вывода дерева подразделений до заданной глубины."""

    employees = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        """Мета-класс сериализатора DepartmentTree."""

        model = Department
        fields = ('id', 'name', 'employees', 'children')

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Инициализация сериализатора."""
        super().__init__(*args, **kwargs)

        include_employees: bool = self.context.get('include_employees', True)

        if not include_employees and 'employees' in self.fields:
            self.fields.pop('employees')

    def get_employees(self, obj: Department) -> list[dict[str, Any]] | None:
        """Получает отсортированный список сотрудников."""
        include_employees: bool = self.context.get('include_employees', True)
        if not include_employees:
            return None

        employees_manager = getattr(obj, 'employees', None)
        if employees_manager is None:
            return []

        employees = employees_manager.all().order_by('full_name')
        return cast(
            list[dict[str, Any]],
            EmployeeListSerializer(employees, many=True).data,
        )

    def get_children(self, obj: Department) -> list[dict[str, Any]]:
        """Рекурсивно собирает поддерево до указанной глубины depth."""
        max_depth: int = self.context.get('max_depth', 1)
        current_depth: int = self.context.get('current_depth', 1)

        if current_depth >= max_depth:
            return []

        child_context = self.context.copy()
        child_context['current_depth'] = current_depth + 1

        children_manager = getattr(obj, 'children', None)
        if children_manager is None:
            return []

        serializer = DepartmentTreeSerializer(
            children_manager.all(), many=True, context=child_context
        )

        return cast(list[dict[str, Any]], serializer.data)
