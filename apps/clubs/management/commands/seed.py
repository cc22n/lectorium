"""
Comando de gestion: carga datos de prueba para desarrollo.

Uso:
    python manage.py seed
    python manage.py seed --flush   # elimina datos existentes primero
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.books.models import Book
from apps.clubs.models import Club, ClubStatus, ClubMode, Membership, MemberRole
from apps.reports.models import Report, Reaction, ReactionType, DiscussionTopic

User = get_user_model()


class Command(BaseCommand):
    help = "Carga datos de prueba para desarrollo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Elimina datos existentes antes de crear nuevos",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Eliminando datos existentes...")
            Report.objects.all().delete()
            Membership.objects.all().delete()
            Club.objects.all().delete()
            Book.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING("Datos eliminados."))

        self.stdout.write("Creando datos de prueba...")

        # ---- Usuarios ----
        users = self._create_users()

        # ---- Libros ----
        books = self._create_books()

        # ---- Clubes ----
        self._create_open_club(users, books[0])
        self._create_reading_club(users, books[1])
        self._create_submission_club(users, books[2])
        self._create_review_club(users, books[3])
        self._create_discussion_club(users, books[4])
        self._create_closed_club(users, books[5])

        self.stdout.write(self.style.SUCCESS(
            "\nSeed completado!\n"
            "  Usuarios: admin / user1..user5 (password: lectorium123)\n"
            "  6 clubes creados en diferentes fases."
        ))

    # ------------------------------------------------------------------

    def _create_users(self):
        users = []
        # Admin
        if not User.objects.filter(username="admin").exists():
            u = User.objects.create_superuser(
                username="admin", email="admin@lectorium.dev",
                password="lectorium123",
                display_name="Administrador",
            )
            users.append(u)
            self.stdout.write(f"  Superusuario: admin")

        for i in range(1, 6):
            uname = f"user{i}"
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(
                    username=uname,
                    email=f"{uname}@lectorium.dev",
                    password="lectorium123",
                    display_name=f"Usuario {i}",
                )
                users.append(u)
                self.stdout.write(f"  Usuario: {uname}")
            else:
                users.append(User.objects.get(username=uname))

        return users

    def _create_books(self):
        books_data = [
            ("Cien anos de soledad", "Gabriel Garcia Marquez", "9780060883287"),
            ("El amor en los tiempos del colera", "Gabriel Garcia Marquez", ""),
            ("1984", "George Orwell", "9780451524935"),
            ("Don Quijote de la Mancha", "Miguel de Cervantes", ""),
            ("El nombre de la rosa", "Umberto Eco", "9780156001311"),
            ("Ficciones", "Jorge Luis Borges", ""),
        ]
        books = []
        for title, author, isbn in books_data:
            b, _ = Book.objects.get_or_create(
                title=title,
                defaults={"author": author, "isbn": isbn, "is_manual_entry": True},
            )
            books.append(b)
            self.stdout.write(f"  Libro: {title}")
        return books

    def _get_users(self, n=5):
        return list(User.objects.filter(is_superuser=False)[:n])

    def _add_members(self, club, users, count):
        for u in users[:count]:
            Membership.objects.get_or_create(
                user=u, club=club,
                defaults={"role": MemberRole.MEMBER},
            )

    def _create_open_club(self, users, book):
        creator = users[0] if users else User.objects.filter(is_superuser=False).first()
        club, created = Club.objects.get_or_create(
            name="Magico realismo latinoamericano",
            defaults={
                "description": "Exploramos el realismo magico en la literatura latinoamericana.",
                "book": book,
                "creator": creator,
                "min_members": 5,
                "max_members": 12,
                "reading_duration_days": 21,
                "submission_duration_days": 7,
                "review_duration_days": 5,
                "discussion_duration_days": 7,
                "open_until": timezone.now() + timedelta(days=10),
                "status": ClubStatus.OPEN,
                "mode": ClubMode.FREE,
            },
        )
        if created:
            Membership.objects.get_or_create(
                user=creator, club=club, defaults={"role": MemberRole.CREATOR}
            )
            self._add_members(club, users[1:], 2)
            self.stdout.write(f"  Club OPEN: {club.name}")

    def _create_reading_club(self, users, book):
        creator = users[1] if len(users) > 1 else users[0]
        club, created = Club.objects.get_or_create(
            name="Distopias clasicas",
            defaults={
                "description": "Lectura grupal de clasicos distopicos.",
                "book": book,
                "creator": creator,
                "min_members": 5,
                "max_members": 10,
                "reading_duration_days": 14,
                "submission_duration_days": 7,
                "review_duration_days": 5,
                "discussion_duration_days": 5,
                "open_until": timezone.now() - timedelta(days=3),
                "reading_starts_at": timezone.now() - timedelta(days=3),
                "submission_starts_at": timezone.now() + timedelta(days=11),
                "review_starts_at": timezone.now() + timedelta(days=18),
                "discussion_starts_at": timezone.now() + timedelta(days=23),
                "closes_at": timezone.now() + timedelta(days=28),
                "status": ClubStatus.READING,
                "mode": ClubMode.STRICT,
            },
        )
        if created:
            Membership.objects.get_or_create(
                user=creator, club=club, defaults={"role": MemberRole.CREATOR}
            )
            self._add_members(club, [u for u in users if u != creator], 4)
            self.stdout.write(f"  Club READING: {club.name}")

    def _create_submission_club(self, users, book):
        creator = users[2] if len(users) > 2 else users[0]
        club, created = Club.objects.get_or_create(
            name="El Quijote contemporaneo",
            defaults={
                "description": "Relectura del Quijote con ojos modernos.",
                "book": book,
                "creator": creator,
                "min_members": 5,
                "max_members": 10,
                "reading_duration_days": 30,
                "submission_duration_days": 7,
                "review_duration_days": 5,
                "discussion_duration_days": 7,
                "open_until": timezone.now() - timedelta(days=35),
                "reading_starts_at": timezone.now() - timedelta(days=35),
                "submission_starts_at": timezone.now() - timedelta(days=5),
                "review_starts_at": timezone.now() + timedelta(days=2),
                "discussion_starts_at": timezone.now() + timedelta(days=7),
                "closes_at": timezone.now() + timedelta(days=14),
                "status": ClubStatus.SUBMISSION,
                "mode": ClubMode.MODERATE,
                "verification_questions": [
                    "Cual es el nombre completo del protagonista?",
                    "Que representa Sancho Panza en la obra?",
                ],
            },
        )
        if created:
            Membership.objects.get_or_create(
                user=creator, club=club, defaults={"role": MemberRole.CREATOR}
            )
            self._add_members(club, [u for u in users if u != creator], 4)
            self.stdout.write(f"  Club SUBMISSION: {club.name}")

    def _create_review_club(self, users, book):
        creator = users[0]
        club, created = Club.objects.get_or_create(
            name="Eco y el medioevo",
            defaults={
                "description": "Lectura del clasico de Umberto Eco.",
                "book": book,
                "creator": creator,
                "min_members": 5,
                "max_members": 15,
                "reading_duration_days": 21,
                "submission_duration_days": 7,
                "review_duration_days": 5,
                "discussion_duration_days": 7,
                "open_until": timezone.now() - timedelta(days=35),
                "reading_starts_at": timezone.now() - timedelta(days=35),
                "submission_starts_at": timezone.now() - timedelta(days=14),
                "review_starts_at": timezone.now() - timedelta(days=7),
                "discussion_starts_at": timezone.now() + timedelta(days=2),
                "closes_at": timezone.now() + timedelta(days=9),
                "status": ClubStatus.REVIEW,
                "mode": ClubMode.RELAXED,
            },
        )
        if created:
            Membership.objects.get_or_create(
                user=creator, club=club, defaults={"role": MemberRole.CREATOR}
            )
            members = [u for u in users if u != creator][:4]
            self._add_members(club, members, 4)
            # Crear reportes para los miembros
            for m in members:
                Report.objects.get_or_create(
                    user=m, club=club,
                    defaults={"text": f"Reflexion de {m.display_name} sobre El nombre de la rosa."},
                )
            # Algunos temas propuestos
            DiscussionTopic.objects.get_or_create(
                club=club, user=creator,
                text="El papel de la religion en la novela",
            )
            DiscussionTopic.objects.get_or_create(
                club=club, user=members[0] if members else creator,
                text="Los laberintos como metafora del conocimiento",
            )
            self.stdout.write(f"  Club REVIEW: {club.name}")

    def _create_discussion_club(self, users, book):
        creator = users[1] if len(users) > 1 else users[0]
        club, created = Club.objects.get_or_create(
            name="Borges y el infinito",
            defaults={
                "description": "Exploramos los mundos posibles de Borges.",
                "book": book,
                "creator": creator,
                "min_members": 5,
                "max_members": 10,
                "reading_duration_days": 14,
                "submission_duration_days": 7,
                "review_duration_days": 5,
                "discussion_duration_days": 7,
                "open_until": timezone.now() - timedelta(days=30),
                "reading_starts_at": timezone.now() - timedelta(days=30),
                "submission_starts_at": timezone.now() - timedelta(days=16),
                "review_starts_at": timezone.now() - timedelta(days=9),
                "discussion_starts_at": timezone.now() - timedelta(days=4),
                "closes_at": timezone.now() + timedelta(days=3),
                "status": ClubStatus.DISCUSSION,
                "mode": ClubMode.FREE,
            },
        )
        if created:
            Membership.objects.get_or_create(
                user=creator, club=club, defaults={"role": MemberRole.CREATOR}
            )
            members = [u for u in users if u != creator][:4]
            self._add_members(club, members, 4)
            for m in members:
                Report.objects.get_or_create(
                    user=m, club=club,
                    defaults={"text": f"Mi lectura de Ficciones: {m.display_name}."},
                )
            self.stdout.write(f"  Club DISCUSSION: {club.name}")

    def _create_closed_club(self, users, book):
        creator = users[2] if len(users) > 2 else users[0]
        club, created = Club.objects.get_or_create(
            name="Clasicos latinoamericanos I",
            defaults={
                "description": "Club ya finalizado.",
                "book": book,
                "creator": creator,
                "min_members": 5,
                "max_members": 10,
                "reading_duration_days": 14,
                "submission_duration_days": 7,
                "review_duration_days": 5,
                "discussion_duration_days": 7,
                "open_until": timezone.now() - timedelta(days=60),
                "reading_starts_at": timezone.now() - timedelta(days=60),
                "submission_starts_at": timezone.now() - timedelta(days=46),
                "review_starts_at": timezone.now() - timedelta(days=39),
                "discussion_starts_at": timezone.now() - timedelta(days=34),
                "closes_at": timezone.now() - timedelta(days=27),
                "status": ClubStatus.CLOSED,
                "mode": ClubMode.FREE,
            },
        )
        if created:
            Membership.objects.get_or_create(
                user=creator, club=club, defaults={"role": MemberRole.CREATOR}
            )
            self._add_members(club, [u for u in users if u != creator], 4)
            self.stdout.write(f"  Club CLOSED: {club.name}")
