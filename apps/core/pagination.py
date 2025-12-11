"""
Centralized pagination configuration for all API endpoints.

Uses LimitOffsetPagination with standard settings to ensure
consistent pagination behavior across the application.
"""

from rest_framework.pagination import LimitOffsetPagination


class StandardPagination(LimitOffsetPagination):
    """
    Standard pagination configuration for all list endpoints.

    Provides:
    - default_limit: 20 items per page
    - max_limit: 100 items per page (prevents abuse)
    - Offset/limit query parameters for flexibility
    """

    default_limit = 20
    max_limit = 100
