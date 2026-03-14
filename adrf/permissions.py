import asyncio

from asgiref.sync import async_to_sync, sync_to_async
from rest_framework import permissions

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
    def __init__(self, op1, op2):
        super().__init__(op1, op2)
        self.op1_has_perm_is_async = asyncio.iscoroutinefunction(op1.has_permission)
        self.op2_has_perm_is_async = asyncio.iscoroutinefunction(op2.has_permission)
        self.op1_obj_perm_is_async = asyncio.iscoroutinefunction(op1.has_object_permission)
        self.op2_obj_perm_is_async = asyncio.iscoroutinefunction(op2.has_object_permission)

    def _get_async_has_perm(self):
        async_has_perm_a = (
            self.op1.has_permission if self.op1_has_perm_is_async else sync_to_async(self.op1.has_permission)
        )
        async_has_perm_b = (
            self.op2.has_permission if self.op2_has_perm_is_async else sync_to_async(self.op2.has_permission)
        )
        return async_has_perm_a, async_has_perm_b

    def _get_async_has_obj_perm(self):
        async_obj_perm_a = (
            self.op1.has_object_permission
            if self.op1_obj_perm_is_async else sync_to_async(self.op1.has_object_permission)
        )
        async_obj_perm_b = (
            self.op2.has_object_permission
            if self.op2_obj_perm_is_async else sync_to_async(self.op2.has_object_permission)
        )
        return async_obj_perm_a, async_obj_perm_b


class AsyncSingleLogicOperatorMixin:
    def __init__(self, op1):
        super().__init__(op1)
        self.op1_has_perm_is_async = asyncio.iscoroutinefunction(op1.has_permission)
        self.op1_obj_perm_is_async = asyncio.iscoroutinefunction(op1.has_object_permission)

    def _get_async_has_perm(self):
        return self.op1.has_permission if self.op1_has_perm_is_async else sync_to_async(self.op1.has_permission)

    def _get_async_has_obj_perm(self):
        return (
            self.op1.has_object_permission
            if self.op1_obj_perm_is_async else sync_to_async(self.op1.has_object_permission)
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
