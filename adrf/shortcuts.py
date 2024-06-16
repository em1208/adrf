from django.http import Http404

def _get_queryset(klass):
    """
    Return a QuerySet or a Manager.
    Duck typing in action: any class with a `get()` method (for
    get_object_or_404) or a `filter()` method (for get_list_or_404) might do
    the job.
    """
    # If it is a model class or anything else with ._default_manager
    if hasattr(klass, "_default_manager"):
        return klass._default_manager.all()
    return klass

async def aget_object_or_404(klass, *args, **kwargs):
    """See get_object_or_404()."""
    queryset = _get_queryset(klass)
    if not hasattr(queryset, "aget"):
        klass__name = (
            klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        )
        raise ValueError(
            "First argument to aget_object_or_404() must be a Model, Manager, or "
            f"QuerySet, not '{klass__name}'."
        )
    try:
        return await queryset.aget(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise Http404(f"No {queryset.model._meta.object_name} matches the given query.")