"""Модели для приложения company."""

from django.db import models

from core.constants import (
    DEPARTMENT_NAME_MAX_LEN,
    EMPLOYEE_FULL_NAME_MAX_LEN,
    EMPLOYEE_POSITION_MAX_LEN,
)


class Department(models.Model):
    """Модель подразделения."""

    name = models.CharField(
        verbose_name='Подразделение',
        max_length=DEPARTMENT_NAME_MAX_LEN,
        blank=False,
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name='Родительское подразделение',
        blank=True,
        null=True,
        related_name='children',
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
    )

    class Meta:
        """Мета-класс для модели подразделения."""

        ordering = ('name',)
        constraints = (
            models.UniqueConstraint(
                fields=['parent', 'name'],
                name='unique_name_per_parent',
            ),
        )

    def __str__(self):
        """Строковое представление названия подразделения."""
        return self.name

    def save(self, *args, **kwargs):
        """Тримминг пробелов в названии подразделения."""
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)


class Employee(models.Model):
    """Модель сотрудника."""

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        verbose_name='Подразделение',
        related_name='employees',
    )
    full_name = models.CharField(
        verbose_name='Сотрудник',
        max_length=EMPLOYEE_FULL_NAME_MAX_LEN,
        blank=False,
    )
    position = models.CharField(
        verbose_name='Должность',
        max_length=EMPLOYEE_POSITION_MAX_LEN,
        blank=False,
    )
    hired_at = models.DateField(
        verbose_name='Дата найма',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
    )

    def __str__(self):
        """Строковое представление сотрудника."""
        return self.full_name
