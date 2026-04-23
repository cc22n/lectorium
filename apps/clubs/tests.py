from datetime import timedelta

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.books.models import Book
from .models import Club, ClubStatus, Membership, MemberRole

_IN_MEMORY_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

User = get_user_model()


# ==============================================================
# HELPERS
# ==============================================================

def make_user(username="testuser", password="password123"):
    return User.objects.create_user(
        username=username,
        password=password,
        email=f"{username}@test.com",
    )


def make_book(title="Test Book"):
    return Book.objects.create(
        title=title,
        author="Autor Test",
        is_manual_entry=True,
    )


def make_club(creator, book=None, status=ClubStatus.OPEN, **kwargs):
    if book is None:
        book = make_book()
    defaults = {
        "name": "Club de prueba",
        "description": "Descripcion de prueba",
        "book": book,
        "creator": creator,
        "min_members": 5,
        "max_members": 10,
        "reading_duration_days": 14,
        "submission_duration_days": 7,
        "review_duration_days": 5,
        "discussion_duration_days": 7,
        "open_until": timezone.now() + timedelta(days=7),
        "status": status,
    }
    defaults.update(kwargs)
    club = Club.objects.create(**defaults)
    # Crear membresia del creador
    Membership.objects.create(user=creator, club=club, role=MemberRole.CREATOR)
    return club


def add_members(club, count):
    """Agrega N miembros activos al club."""
    users = []
    for i in range(count):
        u = make_user(f"member_{club.pk}_{i}")
        Membership.objects.create(user=u, club=club, role=MemberRole.MEMBER)
        users.append(u)
    return users


# ==============================================================
# TESTS DE MODELOS
# ==============================================================

class ClubModelTests(TestCase):

    def setUp(self):
        self.creator = make_user("creator")
        self.club = make_club(self.creator)

    def test_active_members_count_includes_creator(self):
        self.assertEqual(self.club.active_members_count, 1)

    def test_has_reached_minimum_false_initially(self):
        self.assertFalse(self.club.has_reached_minimum)

    def test_has_reached_minimum_true_after_enough_members(self):
        add_members(self.club, 4)  # creator + 4 = 5
        self.assertTrue(self.club.has_reached_minimum)

    def test_is_full_false_initially(self):
        self.assertFalse(self.club.is_full)

    def test_is_full_true_at_max(self):
        add_members(self.club, 9)  # creator + 9 = 10
        self.assertTrue(self.club.is_full)

    def test_transition_open_to_reading(self):
        self.club.transition_to(ClubStatus.READING)
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, ClubStatus.READING)
        self.assertIsNotNone(self.club.submission_starts_at)
        self.assertIsNotNone(self.club.closes_at)

    def test_transition_calculates_dates_correctly(self):
        self.club.transition_to(ClubStatus.READING)
        self.club.refresh_from_db()
        expected_submission = self.club.reading_starts_at + timedelta(days=14)
        self.assertAlmostEqual(
            self.club.submission_starts_at.timestamp(),
            expected_submission.timestamp(),
            delta=5,
        )

    def test_transition_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.club.transition_to(ClubStatus.DISCUSSION)

    def test_full_lifecycle_transitions(self):
        self.club.transition_to(ClubStatus.READING)
        self.club.transition_to(ClubStatus.SUBMISSION)
        self.club.transition_to(ClubStatus.REVIEW)
        self.club.transition_to(ClubStatus.DISCUSSION)
        self.club.transition_to(ClubStatus.CLOSED)
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, ClubStatus.CLOSED)

    def test_cancel_from_any_active_status(self):
        self.club.transition_to(ClubStatus.READING)
        self.club.cancel()
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, ClubStatus.CANCELLED)

    def test_should_cancel_for_low_members_false_in_open(self):
        """OPEN no se cancela por baja membresia."""
        self.assertFalse(self.club.should_cancel_for_low_members())

    def test_should_cancel_for_low_members_true_in_reading(self):
        self.club.transition_to(ClubStatus.READING)
        # Solo queda el creador (1 miembro <= umbral 3)
        self.assertTrue(self.club.should_cancel_for_low_members())

    def test_can_accept_members_returns_false_when_full(self):
        add_members(self.club, 9)
        self.assertFalse(self.club.can_accept_members())

    def test_can_accept_members_returns_false_when_not_open(self):
        self.club.transition_to(ClubStatus.READING)
        self.assertFalse(self.club.can_accept_members())


class MembershipTests(TestCase):

    def setUp(self):
        self.creator = make_user("creator")
        self.club = make_club(self.creator, status=ClubStatus.READING)
        # Agregar suficientes miembros para evitar cancelacion por umbral
        self.members = add_members(self.club, 4)

    def test_leave_marks_membership_inactive(self):
        m = Membership.objects.get(user=self.members[0], club=self.club)
        m.leave()
        m.refresh_from_db()
        self.assertFalse(m.is_active)

    def test_leave_cancels_club_below_threshold(self):
        """Si quedan <= 3 activos el club se cancela."""
        # creator + 4 members = 5. Eliminar 2 deja 3 (threshold) → cancela
        Membership.objects.get(user=self.members[0], club=self.club).leave()
        Membership.objects.get(user=self.members[1], club=self.club).leave()
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, ClubStatus.CANCELLED)


# ==============================================================
# TESTS DE VISTAS
# ==============================================================

class JoinViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.creator = make_user("creator")
        self.user = make_user("joiner")
        self.club = make_club(self.creator)

    def test_join_requires_login(self):
        url = reverse("clubs:join", kwargs={"pk": self.club.pk})
        resp = self.client.post(url)
        self.assertRedirects(resp, f"/accounts/login/?next={url}", fetch_redirect_response=False)

    def test_join_open_club_succeeds(self):
        self.client.login(username="joiner", password="password123")
        url = reverse("clubs:join", kwargs={"pk": self.club.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Membership.objects.filter(user=self.user, club=self.club, is_active=True).exists()
        )

    def test_join_full_club_fails(self):
        add_members(self.club, 9)  # llena el club (max=10, ya hay creator)
        self.client.login(username="joiner", password="password123")
        url = reverse("clubs:join", kwargs={"pk": self.club.pk})
        self.client.post(url)
        # No debe crear membresia
        self.assertFalse(
            Membership.objects.filter(user=self.user, club=self.club).exists()
        )

    def test_join_transitions_to_reading_at_minimum(self):
        """Al unirse el miembro que completa el minimo, debe pasar a READING."""
        add_members(self.club, 3)  # creator + 3 = 4 (necesita 5)
        self.client.login(username="joiner", password="password123")
        url = reverse("clubs:join", kwargs={"pk": self.club.pk})
        self.client.post(url)
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, ClubStatus.READING)

    def test_cannot_join_non_open_club(self):
        self.club.transition_to(ClubStatus.READING)
        self.client.login(username="joiner", password="password123")
        url = reverse("clubs:join", kwargs={"pk": self.club.pk})
        self.client.post(url)
        self.assertFalse(
            Membership.objects.filter(user=self.user, club=self.club).exists()
        )


class LeaveViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.creator = make_user("creator")
        self.club = make_club(self.creator)
        self.member = make_user("member")
        Membership.objects.create(user=self.member, club=self.club, role=MemberRole.MEMBER)

    def test_member_can_leave(self):
        self.client.login(username="member", password="password123")
        url = reverse("clubs:leave", kwargs={"pk": self.club.pk})
        self.client.post(url)
        m = Membership.objects.get(user=self.member, club=self.club)
        self.assertFalse(m.is_active)

    def test_creator_cannot_leave(self):
        self.client.login(username="creator", password="password123")
        url = reverse("clubs:leave", kwargs={"pk": self.club.pk})
        self.client.post(url)
        m = Membership.objects.get(user=self.creator, club=self.club)
        self.assertTrue(m.is_active)


class DetailViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.creator = make_user("creator")
        self.club = make_club(self.creator)

    def test_detail_accessible_without_login(self):
        url = reverse("clubs:detail", kwargs={"pk": self.club.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_detail_shows_club_name(self):
        url = reverse("clubs:detail", kwargs={"pk": self.club.pk})
        resp = self.client.get(url)
        self.assertContains(resp, self.club.name)

    def test_detail_404_for_nonexistent_club(self):
        url = reverse("clubs:detail", kwargs={"pk": 99999})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


# ==============================================================
# TESTS DEL CONSUMER WEBSOCKET (phase-gate y membership)
# ==============================================================

class _ScopeMiddleware:
    """Inyecta user y url_route en el scope WebSocket para testing sin auth middleware."""
    def __init__(self, inner, user, club_pk):
        self.inner = inner
        self.user = user
        self.club_pk = club_pk

    async def __call__(self, scope, receive, send):
        scope = {
            **scope,
            "user": self.user,
            "url_route": {"kwargs": {"club_pk": str(self.club_pk)}},
        }
        await self.inner(scope, receive, send)


@override_settings(CHANNEL_LAYERS=_IN_MEMORY_CHANNEL_LAYERS)
class DiscussionConsumerTests(TransactionTestCase):
    """
    Tests para el phase-gate y membership-gate del WebSocket consumer.
    Usa TransactionTestCase porque las pruebas async no pueden compartir
    la transaccion de TestCase.
    """

    def setUp(self):
        from apps.clubs.consumers import DiscussionConsumer
        self.Consumer = DiscussionConsumer
        self.creator = make_user("ws_creator")
        self.member = make_user("ws_member")
        self.outsider = make_user("ws_outsider")
        self.club = make_club(self.creator, status=ClubStatus.OPEN)
        add_members(self.club, 4)
        Membership.objects.get_or_create(
            user=self.member, club=self.club,
            defaults={"role": MemberRole.MEMBER},
        )

    def _make_communicator(self, user, club_pk=None):
        from channels.testing import WebsocketCommunicator
        pk = club_pk or self.club.pk
        app = _ScopeMiddleware(self.Consumer.as_asgi(), user, pk)
        return WebsocketCommunicator(app, f"/ws/clubs/{pk}/discussion/")

    async def test_rejects_connection_when_club_not_in_discussion(self):
        """Consumer debe cerrar la conexion si el club no esta en fase DISCUSSION."""
        communicator = self._make_communicator(self.member)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_accepts_member_in_discussion_phase(self):
        """Consumer acepta a un miembro activo cuando el club esta en DISCUSSION."""
        await sync_to_async(self.club.transition_to)(ClubStatus.READING)
        await sync_to_async(self.club.transition_to)(ClubStatus.SUBMISSION)
        await sync_to_async(self.club.transition_to)(ClubStatus.REVIEW)
        await sync_to_async(self.club.transition_to)(ClubStatus.DISCUSSION)
        communicator = self._make_communicator(self.member)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_rejects_non_member_in_discussion_phase(self):
        """Consumer rechaza conexiones de usuarios que no son miembros activos."""
        await sync_to_async(self.club.transition_to)(ClubStatus.READING)
        await sync_to_async(self.club.transition_to)(ClubStatus.SUBMISSION)
        await sync_to_async(self.club.transition_to)(ClubStatus.REVIEW)
        await sync_to_async(self.club.transition_to)(ClubStatus.DISCUSSION)
        communicator = self._make_communicator(self.outsider)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()
