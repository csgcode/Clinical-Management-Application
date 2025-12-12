"""
Core permission helper functions
"""


def is_patient_admin(user) -> bool:
    """
    Check if user is in the 'patient_admin' group.

    Args:
        user: Django User instance.

    Returns:
        True if user is authenticated and in 'patient_admin' group, False otherwise.
    """
    return user.is_authenticated and user.groups.filter(name="patient_admin").exists()


def is_clinician(user) -> bool:
    """
    Check if user has an associated clinician profile.

    Args:
        user: Django User instance.

    Returns:
        True if user is authenticated and has clinician_profile, False otherwise.
    """
    return user.is_authenticated and user.has_clinician_profile


def get_user_role_type(user) -> str:
    """
    Determine the user's role type.

    Args:
        user: Django User instance.

    Returns:
        One of: "admin", "clinician", "unknown"
    """
    if not user.is_authenticated:
        return "unknown"

    if is_patient_admin(user):
        return "admin"

    if is_clinician(user):
        return "clinician"

    return "unknown"
