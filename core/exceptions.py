from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .ml import ModelNotReadyError


def api_exception_handler(exc, context):
    """A missing model file is a 'not ready yet' condition (503), not a server bug (500)."""
    if isinstance(exc, ModelNotReadyError):
        return Response(
            {"status": "model_not_ready", "message": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return exception_handler(exc, context)
