import asyncio

from asgiref.sync import sync_to_async
from rest_framework import permissions


def try_convert_operator(operator_instance):
    if not is_perm_operator(operator_instance):
        return operator_instance
    if isinstance(operator_instance, permissions.AND):
        operator_class = AAND
        operands = [operator_instance.op1, operator_instance.op2]
    elif isinstance(operator_instance, permissions.OR):
        operator_class = AOR
        operands = [operator_instance.op1, operator_instance.op2]
    elif isinstance(operator_instance, permissions.NOT):
        operator_class = ANOT
        operands = [operator_instance.op1]
    else:
        raise TypeError(
            f"Cannot translate sync operator class '{operator_instance.__class__.__name__}' to async"
        )
    operands = [
        try_convert_operator(operand)
        for operand in operands
    ]
    return operator_class(*operands)


def is_perm_operator(operator_instance):
    return isinstance(operator_instance, (permissions.AND, permissions.OR, permissions.NOT))


def is_async_perm_operator(operator_instance):
    return isinstance(operator_instance, (AAND, AOR, ANOT))


class AsyncOperandHolderMixin:
    def __and__(self, other):
        return AsyncOperandHolder(AAND, self, other)

    def __or__(self, other):
        return AsyncOperandHolder(AOR, self, other)

    def __rand__(self, other):
        return AsyncOperandHolder(AAND, other, self)

    def __ror__(self, other):
        return AsyncOperandHolder(AOR, other, self)

    def __invert__(self):
        return AsyncSingleOperandHolder(ANOT, self)


class AsyncLogicOperatorMixin:
    def _get_async_has_perm(self):
        async_has_perm_a = (
            self.op1.has_permission
            if asyncio.iscoroutinefunction(self.op1.has_permission) else sync_to_async(self.op1.has_permission)
        )
        async_has_perm_b = (
            self.op2.has_permission
            if asyncio.iscoroutinefunction(self.op2.has_permission) else sync_to_async(self.op2.has_permission)
        )
        return async_has_perm_a, async_has_perm_b

    def _get_async_has_obj_perm(self):
        async_obj_perm_a = (
            self.op1.has_object_permission
            if asyncio.iscoroutinefunction(self.op1.has_object_permission)
            else sync_to_async(self.op1.has_object_permission)
        )
        async_obj_perm_b = (
            self.op2.has_object_permission
            if asyncio.iscoroutinefunction(self.op2.has_object_permission)
            else sync_to_async(self.op2.has_object_permission)
        )
        return async_obj_perm_a, async_obj_perm_b


class AsyncSingleLogicOperatorMixin:
    def _get_async_has_perm(self):
        return (
            self.op1.has_permission
            if asyncio.iscoroutinefunction(self.op1.has_permission)
            else sync_to_async(self.op1.has_permission)
        )

    def _get_async_has_obj_perm(self):
        return (
            self.op1.has_object_permission
            if asyncio.iscoroutinefunction(self.op1.has_object_permission)
            else sync_to_async(self.op1.has_object_permission)
        )


class AsyncSingleOperandHolder(AsyncOperandHolderMixin, permissions.SingleOperandHolder):
    pass


class AsyncOperandHolder(AsyncOperandHolderMixin, permissions.OperandHolder):
    pass


class AAND(AsyncLogicOperatorMixin, permissions.AND):
    async def has_permission(self, request, view):
        async_has_perm_a, async_has_perm_b = self._get_async_has_perm()
        return (
            await async_has_perm_a(request, view) and await async_has_perm_b(request, view)
        )

    async def has_object_permission(self, request, view, obj):
        async_obj_perm_a, async_obj_perm_b = self._get_async_has_obj_perm()
        return (
            await async_obj_perm_a(request, view, obj) and
            await async_obj_perm_b(request, view, obj)
        )


class AOR(AsyncLogicOperatorMixin, permissions.OR):
    async def has_permission(self, request, view):
        async_has_perm_a, async_has_perm_b = self._get_async_has_perm()
        return (
            await async_has_perm_a(request, view) or
            await async_has_perm_b(request, view)
        )

    async def has_object_permission(self, request, view, obj):
        async_has_perm_a, async_has_perm_b = self._get_async_has_perm()
        async_obj_perm_a, async_obj_perm_b = self._get_async_has_obj_perm()
        return (
            await async_has_perm_a(request, view)
            and await async_obj_perm_a(request, view, obj)
        ) or (
            await async_has_perm_b(request, view)
            and await async_obj_perm_b(request, view, obj)
        )


class ANOT(AsyncSingleLogicOperatorMixin, permissions.NOT):
    async def has_permission(self, request, view):
        async_has_perm = self._get_async_has_perm()
        return not await async_has_perm(request, view)

    async def has_object_permission(self, request, view, obj):
        async_obj_perm = self._get_async_has_obj_perm()
        return not await async_obj_perm(request, view, obj)


class AsyncBasePermissionMetaClass(AsyncOperandHolderMixin, permissions.BasePermissionMetaclass):
    pass


class AsyncBasePermission(permissions.BasePermission, metaclass=AsyncBasePermissionMetaClass):
    async def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

    async def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True
