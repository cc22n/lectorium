# Skill: Testing — Patrones del proyecto

## Framework
- Django TestCase para tests con BD
- pytest como runner alternativo (opcional)
- Archivos: `tests.py` o `tests/` en cada app

## Que testear prioritariamente

### 1. Modelos — transiciones de fase
```python
class TestClubTransitions(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="test1234")
        self.book = Book.objects.create(title="Test Book", author="Author")

    def test_valid_transition_open_to_reading(self):
        club = create_club(status="OPEN")
        club.transition_to(ClubStatus.READING)
        self.assertEqual(club.status, ClubStatus.READING)
        self.assertIsNotNone(club.reading_starts_at)

    def test_invalid_transition_raises(self):
        club = create_club(status="OPEN")
        with self.assertRaises(ValueError):
            club.transition_to(ClubStatus.DISCUSSION)

    def test_cancel_from_any_phase(self):
        for status in [ClubStatus.OPEN, ClubStatus.READING, ClubStatus.SUBMISSION]:
            club = create_club(status=status)
            club.cancel()
            self.assertEqual(club.status, ClubStatus.CANCELLED)
```

### 2. Modelos — limites de usuario
```python
class TestUserLimits(TestCase):
    def test_can_create_club_respects_max(self):
        user = create_user()
        # Crear 2 clubes
        create_club_with_membership(user, role="CREATOR")
        create_club_with_membership(user, role="CREATOR")
        self.assertFalse(user.can_create_club())

    def test_can_join_club_respects_max(self):
        user = create_user()
        for _ in range(3):
            create_club_with_membership(user, role="MEMBER")
        self.assertFalse(user.can_join_club())

    def test_created_counts_in_active(self):
        user = create_user()
        create_club_with_membership(user, role="CREATOR")  # 1
        create_club_with_membership(user, role="CREATOR")  # 2
        create_club_with_membership(user, role="MEMBER")   # 3
        self.assertFalse(user.can_join_club())  # ya tiene 3
```

### 3. Modelos — abandono y cancelacion
```python
class TestMembership(TestCase):
    def test_leave_deactivates(self):
        membership = create_membership()
        membership.leave()
        self.assertFalse(membership.is_active)

    def test_leave_cancels_club_if_below_threshold(self):
        club = create_club_with_n_members(4, status="READING")
        # Sacar 2 miembros para quedar en 2
        club.memberships.filter(role="MEMBER").first().leave()
        club.memberships.filter(role="MEMBER", is_active=True).first().leave()
        club.refresh_from_db()
        # Quedan 2 (creador + 1), debajo del umbral de 3
        self.assertEqual(club.status, ClubStatus.CANCELLED)
```

### 4. Vistas — permisos
```python
class TestClubViews(TestCase):
    def test_join_requires_login(self):
        resp = self.client.post(f"/clubs/{club.pk}/join/")
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_cannot_join_full_club(self):
        self.client.login(username="test", password="test1234")
        club = create_full_club()
        resp = self.client.post(f"/clubs/{club.pk}/join/")
        # Should show error message
        self.assertContains(resp, "no acepta", status_code=302)

    def test_creator_cannot_leave(self):
        self.client.login(username="creator", password="test1234")
        resp = self.client.post(f"/clubs/{club.pk}/leave/")
        # Creator should not be able to leave
```

## Helpers para tests
Crear un archivo `apps/clubs/test_helpers.py` con factories:
```python
def create_user(username="testuser", **kwargs):
    return User.objects.create_user(
        username=username, password="testpass1234", **kwargs
    )

def create_book(**kwargs):
    defaults = {"title": "Test Book", "author": "Test Author"}
    defaults.update(kwargs)
    return Book.objects.create(**defaults)

def create_club(creator=None, book=None, status="OPEN", **kwargs):
    if not creator:
        creator = create_user(username=f"creator_{uuid4().hex[:6]}")
    if not book:
        book = create_book()
    defaults = {
        "name": "Test Club",
        "description": "Test",
        "book": book,
        "creator": creator,
        "min_members": 5,
        "max_members": 20,
        "reading_duration_days": 30,
        "submission_duration_days": 7,
        "review_duration_days": 3,
        "discussion_duration_days": 7,
        "open_until": timezone.now() + timedelta(days=30),
        "status": status,
    }
    defaults.update(kwargs)
    club = Club.objects.create(**defaults)
    Membership.objects.create(user=creator, club=club, role="CREATOR")
    return club
```

## Ejecutar tests
```bash
python manage.py test                          # todos
python manage.py test apps.clubs               # solo clubs
python manage.py test apps.clubs.tests.TestClubTransitions  # clase especifica
```
