import asyncio

from asgiref.sync import sync_to_async
from rest_framework import permissions


def try_convert_operator(operator_instance):
    """
    Helper function which attempts to convert a given permissions operator (i.e., AND, OR, NOT) and any sub-operators
    to their async equivalent. This addresses issues with mixed operator types, where a sync operator (e.g., AND)
    does not await the result of an async sub-operator. If the given parameter is NOT an operator, then this function
    returns the original argument unchanged.
    """
    if not is_perm_operator(operator_instance):
        return operator_instance
    if is_async_perm_operator(operator_instance):
        # Avoid mixed async/sync operators within the operands of the given async operator
        if isinstance(operator_instance, (AAND, AOR)):
            operator_instance.op1 = try_convert_operator(operator_instance.op1)
            operator_instance.op2 = try_convert_operator(operator_instance.op2)
        else:
            operator_instance.op1 = try_convert_operator(operator_instance.op1)
        return operator_instance
    # Convert sync operator types to async
    if isinstance(operator_instance, permissions.AND):
        operator_class = AAND
        operands = [operator_instance.op1, operator_instance.op2]
    elif isinstance(operator_instance, permissions.OR):
        operator_class = AOR
        operands = [operator_instance.op1, operator_instance.op2]
    else:
        operator_class = ANOT
        operands = [operator_instance.op1]
    operands = [
        try_convert_operator(operand)
        for operand in operands
    ]
    return operator_class(*operands)


def is_perm_operator(operator_instance):
    """
    Helper function which checks whether the given parameter is a permissions operator (i.e., AND, OR, NOT).
    """
    return isinstance(operator_instance, (permissions.AND, permissions.OR, permissions.NOT))


def is_async_perm_operator(operator_instance):
    """
    Helper function which checks whether the given parameter is an async permissions operator (i.e., AAND, AOR, ANOT).
    """
    return isinstance(operator_instance, (AAND, AOR, ANOT))


class AsyncOperandHolderMixin:
    """
    Async version of rest framework's operand holder mixin. This uses the async versions of permissions operators,
    rather than the sync equivalents.
    """
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
    """
    Mixin containing common methods for permissions logic operators with two operands.
    """
    def get_async_has_perm(self):
        async_has_perm_a = (
            self.op1.has_permission
            if asyncio.iscoroutinefunction(self.op1.has_permission) else sync_to_async(self.op1.has_permission)
        )
        async_has_perm_b = (
            self.op2.has_permission
            if asyncio.iscoroutinefunction(self.op2.has_permission) else sync_to_async(self.op2.has_permission)
        )
        return async_has_perm_a, async_has_perm_b

    def get_async_has_obj_perm(self):
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
    """
    Mixin containing common methods for permissions logic operators with one operand.
    """
    def get_async_has_perm(self):
        return (
            self.op1.has_permission
            if asyncio.iscoroutinefunction(self.op1.has_permission)
            else sync_to_async(self.op1.has_permission)
        )

    def get_async_has_obj_perm(self):
        return (
            self.op1.has_object_permission
            if asyncio.iscoroutinefunction(self.op1.has_object_permission)
            else sync_to_async(self.op1.has_object_permission)
        )


class AsyncSingleOperandHolder(AsyncOperandHolderMixin, permissions.SingleOperandHolder):
    """
    Extension to the rest framework single operand holder which uses async operators.
    """
    pass


class AsyncOperandHolder(AsyncOperandHolderMixin, permissions.OperandHolder):
    """
    Extension to the rest framework operand holder which uses async operators.
    """
    pass


class AAND(AsyncLogicOperatorMixin, permissions.AND):
    """
    Asynchronous logical AND operator for permissions checks, based on the synchronous equivalent defined by rest
    framework.
    """
    async def has_permission(self, request, view):
        async_has_perm_a, async_has_perm_b = self.get_async_has_perm()
        return (
            await async_has_perm_a(request, view) and await async_has_perm_b(request, view)
        )

    async def has_object_permission(self, request, view, obj):
        async_obj_perm_a, async_obj_perm_b = self.get_async_has_obj_perm()
        return (
            await async_obj_perm_a(request, view, obj) and
            await async_obj_perm_b(request, view, obj)
        )


class AOR(AsyncLogicOperatorMixin, permissions.OR):
    """
    Asynchronous logical OR operator for permissions checks, based on the synchronous equivalent defined by rest
    framework.
    """
    async def has_permission(self, request, view):
        async_has_perm_a, async_has_perm_b = self.get_async_has_perm()
        return (
            await async_has_perm_a(request, view) or
            await async_has_perm_b(request, view)
        )

    async def has_object_permission(self, request, view, obj):
        async_has_perm_a, async_has_perm_b = self.get_async_has_perm()
        async_obj_perm_a, async_obj_perm_b = self.get_async_has_obj_perm()
        return (
            await async_has_perm_a(request, view)
            and await async_obj_perm_a(request, view, obj)
        ) or (
            await async_has_perm_b(request, view)
            and await async_obj_perm_b(request, view, obj)
        )


class ANOT(AsyncSingleLogicOperatorMixin, permissions.NOT):
    """
    Asynchronous logical NOT operator for permissions checks, based on the synchronous equivalent defined by rest
    framework.
    """
    async def has_permission(self, request, view):
        async_has_perm = self.get_async_has_perm()
        return not await async_has_perm(request, view)

    async def has_object_permission(self, request, view, obj):
        async_obj_perm = self.get_async_has_obj_perm()
        return not await async_obj_perm(request, view, obj)


class AsyncBasePermissionMetaClass(AsyncOperandHolderMixin, permissions.BasePermissionMetaclass):
    """
    Extension to the rest framework base permission metaclass which uses async operators.
    """
    pass


class AsyncBasePermission(permissions.BasePermission, metaclass=AsyncBasePermissionMetaClass):
    """
    Asynchronous base permission which can be combined with other permissions using logical operators.
    """
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
