from rest_framework import permissions

from apps.core.permissions_helpers import is_patient_admin


class IsPatientAdminOrClinicianReadOnly(permissions.BasePermission):
    """
    - patient_admin group:
        * full CRUD on patients
    - clinicians (have clinician_profile):
        * read-only (list/retrieve)
        * further scoped by queryset (only their patients)
    - others:
        * no access
    """

    def has_permission(self, request, view) -> bool:
        """
        Check if user has permission to access patient endpoints.

        Args:
            request: HTTP request object
            view: The view being accessed

        Returns:
            True if user has appropriate permissions, False otherwise
        """
        user = request.user
        # TODO remove and use IsAuthenticated permission
        if not user.is_authenticated:
            return False

        admin = is_patient_admin(user)
        clinician = user.has_clinician_profile

        if request.method in permissions.SAFE_METHODS:
            return admin or clinician

        return admin


class IsPatientAdminOrClinicianForDepartment(permissions.BasePermission):
    """
    - patient_admin: can view stats for any department
    - clinician: can only view stats for their own department (via ?department= query param)
    """

    def has_permission(self, request, view) -> bool:
        """
        Check if user can access clinician patient counts.

        Args:
            request: HTTP request object
            view: The view being accessed

        Returns:
            True if user has appropriate permissions, False otherwise
        """
        user = request.user

        department_id_str = request.query_params.get("department")

        # patient admin: full access
        if is_patient_admin(user):
            return True

        # clinician: only if their department matches query param department
        if user.has_clinician_profile:
            if department_id_str:
                try:
                    department_id = int(department_id_str)
                    clinician = user.clinician_profile
                    if clinician.department_id == department_id:
                        return True
                except (ValueError, TypeError):
                    return False

        return False
