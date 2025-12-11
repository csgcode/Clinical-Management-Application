from rest_framework.permissions import BasePermission

from apps.core.permissions_helpers import is_patient_admin, is_clinician


class IsPatientAdminOrClinician(BasePermission):
    """
    Allows access only to:
    - Users in 'patient_admin' group
    - Clinicians (have clinician_profile)

    Actual scoping rules (linked patient, self clinician) are enforced
    in the view's perform_create and queryset.
    """

    def has_permission(self, request, view) -> bool:
        """
        Check if user is admin or clinician.

        Args:
            request: HTTP request object
            view: The view being accessed

        Returns:
            True if user is admin or clinician, False otherwise
        """
        user = request.user
        if not user or not user.is_authenticated:
            return False

        return is_patient_admin(user) or is_clinician(user)
