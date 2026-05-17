"""Представления для api приложения."""

from typing import Any

from django.db import transaction
from django.db.models import Prefetch
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.serializers import (
    DepartmentCreateSerializer,
    DepartmentTreeSerializer,
    DepartmentUpdateSerializer,
    EmployeeCreateSerializer,
)
from api.validators import (
    validate_department_deletion,
    validate_no_circular_dependency,
    validate_not_self_parent,
)
from company.models import Department, Employee
from core.constants import MAX_DEPTH


class DepartmentCreateView(CreateAPIView):
    """Представление создания подразделения."""

    queryset = Department.objects.all()
    serializer_class = DepartmentCreateSerializer

    def perform_create(self, serializer: DepartmentCreateSerializer) -> None:
        """Связываем создаваемое подразделение с родителем из JSON-body."""
        request: Request = self.request  # type: ignore[assignment]
        data = request.data if isinstance(request.data, dict) else {}
        parent_id = data.get('parent_id')

        if parent_id:
            parent_department = get_object_or_404(Department, id=parent_id)
            serializer.save(parent=parent_department)
        else:
            serializer.save()


class EmployeeCreateView(CreateAPIView):
    """Представление создания сотрудника."""

    queryset = Employee.objects.all()
    serializer_class = EmployeeCreateSerializer

    def perform_create(self, serializer: EmployeeCreateSerializer) -> None:
        """Связываем сотрудника с подразделением, ID которого передан в URL."""
        department_id = self.kwargs.get('pk')
        department = get_object_or_404(Department, id=department_id)
        serializer.save(department=department)


class DepartmentDetailUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """Представление для работы с конкретным подразделением.

    GET, PATCH, DELETE.
    """

    queryset = Department.objects.all()

    def get_serializer_class(self) -> Any:
        """Динамически выбирает сериализатор в зависимости от HTTP-метода."""
        if self.request.method == 'PATCH':
            return DepartmentUpdateSerializer
        return DepartmentTreeSerializer

    def get_serializer_context(self) -> dict[str, Any]:
        """Формирует контекст для дерева (используется при GET-запросе)."""
        context = super().get_serializer_context()
        if self.request.method == 'GET':
            request: Request = self.request  # type: ignore[assignment]
            try:
                depth = int(request.query_params.get('depth', '1'))
                depth = max(1, min(depth, MAX_DEPTH))
            except ValueError:
                depth = 1

            include_param = request.query_params.get(
                'include_employees', 'true'
            ).lower()
            include_employees = include_param != 'false'

            context.update(
                {
                    'max_depth': depth,
                    'current_depth': 1,
                    'include_employees': include_employees,
                }
            )
        return context

    def get_queryset(self) -> QuerySet[Department]:
        """Оптимизирует SQL-запросы через prefetch_related только для GET."""
        queryset = super().get_queryset()

        if self.request.method != 'GET':
            return queryset

        try:
            depth = max(
                1,
                min(int(self.request.query_params.get('depth', 1)), MAX_DEPTH),
            )
        except ValueError:
            depth = 1

        include_param = self.request.query_params.get(
            'include_employees', 'true'
        ).lower()
        include_employees = include_param != 'false'

        lookups: list[str | Prefetch[Any]] = []
        current_lookup = ''

        for i in range(depth):
            current_lookup = (
                f'{current_lookup}__children' if i > 0 else 'children'
            )
            lookups.append(current_lookup)

            if include_employees:
                prefetch_path = (
                    f'{current_lookup}__employees' if i > 0 else 'employees'
                )
                lookups.append(
                    Prefetch(
                        prefetch_path,
                        queryset=Employee.objects.all().order_by('full_name'),
                    )
                )

        return queryset.prefetch_related(*lookups)

    def partial_update(
        self, request: Request, *args: Any, **kwargs: Any
    ) -> Response:
        """Перехватываем PATCH-запрос для ручного обновления связи."""
        instance: Department = self.get_object()

        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        data = request.data if isinstance(request.data, dict) else {}

        if 'parent_id' in data:
            parent_id = data.get('parent_id')
            if parent_id is None:
                instance.parent = None
            else:
                parent_department = get_object_or_404(Department, id=parent_id)

                validate_not_self_parent(instance, parent_department)
                validate_no_circular_dependency(instance, parent_department)

                instance.parent = parent_department

        serializer.save()
        return Response(serializer.data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Реализация логики удаления (cascade / reassign)."""
        instance: Department = self.get_object()

        mode = request.query_params.get('mode', 'cascade').lower()
        reassign_id_param = request.query_params.get(
            'reassign_to_department_id'
        )

        reassign_id = validate_department_deletion(
            mode=mode,
            reassign_id_param=reassign_id_param,
            current_department_id=instance.pk,
        )

        if mode == 'cascade':
            instance.delete()

        elif mode == 'reassign' and reassign_id is not None:
            with transaction.atomic():
                Employee.objects.filter(department=instance).update(
                    department_id=reassign_id
                )
                instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
