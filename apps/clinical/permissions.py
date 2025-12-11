from rest_framework import permissions


# Use DRY


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
            user.is_authenticated and user.groups.filter(name="patient_admin").exists()
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


class IsPatientAdminOrClinicianForDepartment(permissions.BasePermission):
    """
    - patient_admin: can view stats for any department
    - clinician: can only view stats for their own department (self-only scoping happens in view)
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        department_id = view.kwargs.get("department_id")

        # patient admin: full access
        if user.groups.filter(name="patient_admin").exists():
            return True

        # clinician: only if their department matches path department
        if hasattr(user, "clinician_profile"):
            clinician = user.clinician_profile
            if clinician.department_id == department_id:
                return True

        return False
