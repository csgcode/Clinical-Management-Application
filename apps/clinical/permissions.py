from rest_framework import permissions


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

    def _is_patient_admin(self, user) -> bool:
        return (
            user.is_authenticated
            and user.groups.filter(name="patient_admin").exists()
        )

    def _is_clinician(self, user) -> bool:
        return user.is_authenticated and hasattr(user, "clinician_profile")

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        is_admin = self._is_patient_admin(user)
        is_clinician = self._is_clinician(user)

        if request.method in permissions.SAFE_METHODS:
            return is_admin or is_clinician

        # non-safe methods (POST, PUT, PATCH, DELETE) only for admins
        return is_admin
