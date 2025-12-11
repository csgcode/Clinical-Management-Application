from rest_framework.permissions import BasePermission


class IsPatientAdminOrClinician(BasePermission):
    """
    Allows access only to:
    - Users in 'patient_admin' group
    - Clinicians (have clinician_profile)

    Actual scoping rules (linked patient, self clinician) are enforced
    in the view's perform_create and queryset.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.groups.filter(name="patient_admin").exists():
            return True

        if hasattr(user, "clinician_profile"):
            return True

        return False
