from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.clubs.models import ClubStatus, ClubMode, Membership, MemberRole
from apps.clubs.tests import make_user, make_club, add_members
from .models import Report, Reaction, ReactionType, VerificationAnswer, ContentFlag, FlagContentType
from .utils import user_can_discuss

User = get_user_model()


def make_club_with_members(creator, status=ClubStatus.SUBMISSION, mode=ClubMode.FREE):
    club = make_club(creator, status=status, mode=mode)
    add_members(club, 4)  # creator + 4 = 5 miembros
    return club


# ==============================================================
# TESTS DE VERIFICACION (user_can_discuss)
# ==============================================================

class UserCanDiscussTests(TestCase):

    def setUp(self):
        self.creator = make_user("creator")
        self.user = make_user("member")

    def test_free_mode_always_allowed(self):
        club = make_club_with_members(self.creator, mode=ClubMode.FREE)
        can, _ = user_can_discuss(self.user, club)
        self.assertTrue(can)

    def test_strict_mode_requires_report(self):
        club = make_club_with_members(self.creator, mode=ClubMode.STRICT)
        can, _ = user_can_discuss(self.user, club)
        self.assertFalse(can)

    def test_strict_mode_allows_after_report(self):
        club = make_club_with_members(self.creator, mode=ClubMode.STRICT)
        Report.objects.create(user=self.user, club=club, text="Mi reflexion")
        can, _ = user_can_discuss(self.user, club)
        self.assertTrue(can)

    def test_relaxed_mode_requires_confirmation(self):
        club = make_club_with_members(self.creator, mode=ClubMode.RELAXED)
        can, _ = user_can_discuss(self.user, club)
        self.assertFalse(can)

    def test_relaxed_mode_allows_after_confirmation(self):
        club = make_club_with_members(self.creator, mode=ClubMode.RELAXED)
        VerificationAnswer.objects.create(
            user=self.user, club=club,
            answers={"confirmed": True}, passed=True,
        )
        can, _ = user_can_discuss(self.user, club)
        self.assertTrue(can)

    def test_moderate_mode_requires_approval(self):
        club = make_club_with_members(self.creator, mode=ClubMode.MODERATE)
        VerificationAnswer.objects.create(
            user=self.user, club=club,
            answers={"0": "respuesta"}, passed=False,
        )
        can, _ = user_can_discuss(self.user, club)
        self.assertFalse(can)

    def test_moderate_mode_allows_after_approval(self):
        club = make_club_with_members(self.creator, mode=ClubMode.MODERATE)
        VerificationAnswer.objects.create(
            user=self.user, club=club,
            answers={"0": "respuesta"}, passed=True,
        )
        can, _ = user_can_discuss(self.user, club)
        self.assertTrue(can)


# ==============================================================
# TESTS DE ENTREGA DE REPORTES
# ==============================================================

class SubmitReportViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.creator = make_user("creator")
        self.member_user = make_user("member")
        self.club = make_club_with_members(self.creator, status=ClubStatus.SUBMISSION)
        Membership.objects.get_or_create(
            user=self.member_user, club=self.club,
            defaults={"role": MemberRole.MEMBER},
        )

    def test_submit_requires_login(self):
        url = reverse("reports:submit", kwargs={"club_pk": self.club.pk})
        resp = self.client.get(url)
        self.assertRedirects(resp, f"/accounts/login/?next={url}", fetch_redirect_response=False)

    def test_submit_shows_form_in_submission_phase(self):
        self.client.login(username="member", password="password123")
        url = reverse("reports:submit", kwargs={"club_pk": self.club.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_submit_creates_report(self):
        self.client.login(username="member", password="password123")
        url = reverse("reports:submit", kwargs={"club_pk": self.club.pk})
        self.client.post(url, {"text": "Mi reflexion sobre el libro."})
        self.assertEqual(
            Report.objects.filter(user=self.member_user, club=self.club).count(), 1
        )

    def test_submit_prevents_duplicate(self):
        Report.objects.create(user=self.member_user, club=self.club, text="Primero")
        self.client.login(username="member", password="password123")
        url = reverse("reports:submit", kwargs={"club_pk": self.club.pk})
        self.client.post(url, {"text": "Segundo intento"})
        self.assertEqual(
            Report.objects.filter(user=self.member_user, club=self.club).count(), 1
        )

    def test_submit_blocked_in_reading_phase(self):
        self.club.status = ClubStatus.READING
        self.club.save(update_fields=["status"])
        self.client.login(username="member", password="password123")
        url = reverse("reports:submit", kwargs={"club_pk": self.club.pk})
        self.client.post(url, {"text": "Intento en fase incorrecta"})
        self.assertFalse(
            Report.objects.filter(user=self.member_user, club=self.club).exists()
        )

    def test_non_member_cannot_submit(self):
        outsider = make_user("outsider")
        self.client.login(username="outsider", password="password123")
        url = reverse("reports:submit", kwargs={"club_pk": self.club.pk})
        self.client.post(url, {"text": "Intento de no miembro"})
        self.assertFalse(
            Report.objects.filter(user=outsider, club=self.club).exists()
        )


# ==============================================================
# TESTS DE REACCIONES
# ==============================================================

class ReactionViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.creator = make_user("creator")
        self.member_user = make_user("member")
        self.club = make_club_with_members(self.creator, status=ClubStatus.REVIEW)
        Membership.objects.get_or_create(
            user=self.member_user, club=self.club,
            defaults={"role": MemberRole.MEMBER},
        )
        self.report_author = make_user("author")
        Membership.objects.get_or_create(
            user=self.report_author, club=self.club,
            defaults={"role": MemberRole.MEMBER},
        )
        self.report = Report.objects.create(
            user=self.report_author, club=self.club, text="Reporte de prueba"
        )

    def test_toggle_creates_reaction(self):
        self.client.login(username="member", password="password123")
        url = reverse("reports:react", kwargs={"report_pk": self.report.pk})
        self.client.post(url, {"type": ReactionType.LIKE})
        self.assertTrue(
            Reaction.objects.filter(
                user=self.member_user, report=self.report, type=ReactionType.LIKE
            ).exists()
        )

    def test_toggle_removes_existing_reaction(self):
        Reaction.objects.create(
            user=self.member_user, report=self.report, type=ReactionType.LIKE
        )
        self.client.login(username="member", password="password123")
        url = reverse("reports:react", kwargs={"report_pk": self.report.pk})
        self.client.post(url, {"type": ReactionType.LIKE})
        self.assertFalse(
            Reaction.objects.filter(
                user=self.member_user, report=self.report, type=ReactionType.LIKE
            ).exists()
        )

    def test_reaction_blocked_in_submission_phase(self):
        self.club.status = ClubStatus.SUBMISSION
        self.club.save(update_fields=["status"])
        self.client.login(username="member", password="password123")
        url = reverse("reports:react", kwargs={"report_pk": self.report.pk})
        resp = self.client.post(url, {"type": ReactionType.LIKE})
        self.assertEqual(resp.status_code, 403)


# ==============================================================
# TESTS DE VERIFY MODERATE (bug: usuario aprobado veia pantalla pendiente)
# ==============================================================

class VerifyModerateRedirectTests(TestCase):
    """
    Cubre el bug donde un usuario ya aprobado en modo MODERATE
    visitaba /verify/ y siempre veia la pantalla de pendiente.
    """

    def setUp(self):
        self.client = Client()
        self.creator = make_user("mod_creator")
        self.member = make_user("mod_member")
        self.club = make_club(
            self.creator,
            status=ClubStatus.REVIEW,
            mode=ClubMode.MODERATE,
            verification_questions=["Quien es el protagonista?", "Donde ocurre la historia?"],
        )
        add_members(self.club, 4)
        Membership.objects.get_or_create(
            user=self.member, club=self.club,
            defaults={"role": MemberRole.MEMBER},
        )

    def test_approved_user_in_review_redirects_to_club_detail(self):
        """Usuario aprobado en fase REVIEW debe ir al detalle del club, no a la pantalla de espera."""
        VerificationAnswer.objects.create(
            user=self.member, club=self.club,
            answers={"0": "el protagonista", "1": "en la ciudad"},
            passed=True,
        )
        self.client.login(username="mod_member", password="password123")
        url = reverse("reports:verify", kwargs={"club_pk": self.club.pk})
        resp = self.client.get(url)
        self.assertRedirects(
            resp,
            reverse("clubs:detail", kwargs={"pk": self.club.pk}),
            fetch_redirect_response=False,
        )

    def test_approved_user_in_discussion_redirects_to_debate(self):
        """Usuario aprobado en fase DISCUSSION debe ir directo al debate."""
        self.club.status = ClubStatus.DISCUSSION
        self.club.save(update_fields=["status"])
        VerificationAnswer.objects.create(
            user=self.member, club=self.club,
            answers={"0": "el protagonista", "1": "en la ciudad"},
            passed=True,
        )
        self.client.login(username="mod_member", password="password123")
        url = reverse("reports:verify", kwargs={"club_pk": self.club.pk})
        resp = self.client.get(url)
        self.assertRedirects(
            resp,
            reverse("reports:discussion", kwargs={"club_pk": self.club.pk}),
            fetch_redirect_response=False,
        )

    def test_pending_user_sees_waiting_screen(self):
        """Usuario con respuestas aun sin aprobar debe ver pantalla de espera."""
        VerificationAnswer.objects.create(
            user=self.member, club=self.club,
            answers={"0": "no se", "1": "tampoco"},
            passed=False,
        )
        self.client.login(username="mod_member", password="password123")
        url = reverse("reports:verify", kwargs={"club_pk": self.club.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["mode"], "moderate_pending")

    def test_new_user_sees_question_form(self):
        """Usuario sin respuestas previas debe ver el formulario de preguntas."""
        self.client.login(username="mod_member", password="password123")
        url = reverse("reports:verify", kwargs={"club_pk": self.club.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["mode"], "moderate_form")


# ==============================================================
# TESTS DE RATE LIMITING EN FLAGS
# ==============================================================

class FlagRateLimitTests(TestCase):
    """Verifica que un usuario no pueda crear mas de 5 flags por dia."""

    def setUp(self):
        self.client = Client()
        self.creator = make_user("flag_creator")
        self.member = make_user("flag_member")
        self.club = make_club_with_members(self.creator, status=ClubStatus.DISCUSSION)
        Membership.objects.get_or_create(
            user=self.member, club=self.club,
            defaults={"role": MemberRole.MEMBER},
        )
        self.report = Report.objects.create(
            user=self.creator, club=self.club, text="Reporte para flagear"
        )

    def _flag_url(self):
        return reverse("reports:flag", kwargs={"club_pk": self.club.pk})

    def _post_flag(self, content_id=None):
        cid = content_id or self.report.pk
        return self.client.post(self._flag_url(), {
            "content_type": "report",
            "content_id": str(cid),
            "reason": "Contenido inapropiado",
        })

    def test_flag_allowed_under_limit(self):
        """El primer flag del dia debe mostrar el formulario (200) sin problema."""
        self.client.login(username="flag_member", password="password123")
        url = self._flag_url() + f"?type={FlagContentType.REPORT}&id={self.report.pk}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_flag_blocked_after_daily_limit(self):
        """Tras 5 flags en el dia, el siguiente POST debe ser rechazado."""
        # Crear 5 flags directamente en la BD con el tipo correcto
        for i in range(5):
            ContentFlag.objects.create(
                reported_by=self.member,
                content_type=FlagContentType.REPORT,
                content_id=self.report.pk + i,
                reason="test",
            )
        self.client.login(username="flag_member", password="password123")
        resp = self.client.post(
            self._flag_url() + f"?type={FlagContentType.REPORT}&id={self.report.pk}",
            {
                "content_type": FlagContentType.REPORT,
                "content_id": str(self.report.pk),
                "reason": "intento extra",
            },
        )
        # Debe redirigir con mensaje de limite (sin crear flag adicional)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ContentFlag.objects.filter(reported_by=self.member).count(), 5
        )
