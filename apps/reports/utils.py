from apps.clubs.models import ClubMode
from .models import Report, VerificationAnswer


def user_can_discuss(user, club):
    """
    Devuelve (can_discuss: bool, verification: VerificationAnswer | None).
    Segun el modo del club determina si el usuario puede participar en el debate.
    """
    if club.mode == ClubMode.FREE:
        return True, None

    if club.mode == ClubMode.STRICT:
        has_report = Report.objects.filter(user=user, club=club).exists()
        return has_report, None

    # RELAXED o MODERATE: existe un VerificationAnswer?
    verification = VerificationAnswer.objects.filter(user=user, club=club).first()

    if club.mode == ClubMode.RELAXED:
        return bool(verification), verification

    # MODERATE: necesita aprobacion del creador
    return bool(verification and verification.passed), verification
