import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class DiscussionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer para el debate en tiempo real del club.
    Canal por club: discussion_{club_pk}
    Solo miembros activos pueden conectarse y enviar mensajes.
    """

    async def connect(self):
        self.club_pk = self.scope["url_route"]["kwargs"]["club_pk"]
        self.group_name = f"discussion_{self.club_pk}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        is_member = await self._is_active_member()
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Notificar al grupo que el usuario se conecto
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_joined",
                "username": self.user.display_name or self.user.username,
            },
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")

        if action == "message":
            text = data.get("text", "").strip()
            if not text or len(text) > 1000:
                return

            is_discussion = await self._is_club_in_discussion()
            if not is_discussion:
                await self.send(json.dumps({
                    "type": "error",
                    "message": "El debate ha terminado.",
                }))
                return

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "text": text,
                    "username": self.user.display_name or self.user.username,
                    "user_pk": self.user.pk,
                },
            )

        elif action == "close_discussion":
            is_creator = await self._is_creator()
            if is_creator:
                success = await self._close_club()
                if success:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "discussion_closed"},
                    )

    # --- Handlers de eventos del grupo ---

    async def chat_message(self, event):
        await self.send(json.dumps({
            "type": "message",
            "text": event["text"],
            "username": event["username"],
            "user_pk": event["user_pk"],
        }))

    async def user_joined(self, event):
        await self.send(json.dumps({
            "type": "user_joined",
            "username": event["username"],
        }))

    async def discussion_closed(self, event):
        await self.send(json.dumps({"type": "discussion_closed"}))

    # --- Helpers de base de datos ---

    @database_sync_to_async
    def _is_active_member(self):
        from apps.clubs.models import Membership
        return Membership.objects.filter(
            user=self.user, club_id=self.club_pk, is_active=True
        ).exists()

    @database_sync_to_async
    def _is_creator(self):
        from apps.clubs.models import Membership, MemberRole
        return Membership.objects.filter(
            user=self.user,
            club_id=self.club_pk,
            is_active=True,
            role=MemberRole.CREATOR,
        ).exists()

    @database_sync_to_async
    def _is_club_in_discussion(self):
        from apps.clubs.models import Club, ClubStatus
        return Club.objects.filter(
            pk=self.club_pk, status=ClubStatus.DISCUSSION
        ).exists()

    @database_sync_to_async
    def _close_club(self):
        from apps.clubs.models import Club, ClubStatus
        try:
            club = Club.objects.get(pk=self.club_pk)
            if club.status == ClubStatus.DISCUSSION:
                club.transition_to(ClubStatus.CLOSED)
                return True
        except Club.DoesNotExist:
            pass
        return False
