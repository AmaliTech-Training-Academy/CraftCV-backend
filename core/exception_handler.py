from rest_framework import status
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None or not isinstance(response.data, dict):
        return response

    if "detail" in response.data:
        response.data = {"error": response.data["detail"]}

    view = context.get("view")
    if view is not None and view.__class__.__module__ == "apps.cv_builder.views":
        messages = {
            status.HTTP_400_BAD_REQUEST: "Invalid CV data.",
            status.HTTP_401_UNAUTHORIZED: "Authentication is required to access CV data.",
            status.HTTP_403_FORBIDDEN: "You do not have permission to access this CV data.",
            status.HTTP_404_NOT_FOUND: "CV resource not found.",
        }
        response.data["message"] = messages.get(
            response.status_code,
            "The CV request could not be completed.",
        )

    return response
