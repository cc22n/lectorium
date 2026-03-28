# Skill: WebSockets — Debate en tiempo real

## Stack
- Django Channels 4.x
- channels-redis como backend
- Daphne como servidor ASGI (produccion)
- runserver funciona para dev (Django 5+ soporta ASGI)

## Arquitectura
WebSockets SOLO se usa para el debate (fase DISCUSSION).
Todo lo demas es HTTP normal con HTMX.

## Configuracion existente
```python
# config/settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# config/asgi.py — ya preparado, descomentar websocket routing
```

## Implementacion necesaria

### 1. Consumer del debate
```python
# apps/clubs/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

class DebateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.club_id = self.scope["url_route"]["kwargs"]["club_id"]
        self.room_group = f"debate_{self.club_id}"

        # Verificar que el usuario es miembro y el club esta en DISCUSSION
        if not await self.can_participate():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive_json(self, content):
        message = content.get("message", "").strip()
        if not message:
            return

        user = self.scope["user"]
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "debate_message",
                "message": message,
                "username": user.display_name or user.username,
                "user_id": user.id,
            }
        )

    async def debate_message(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def can_participate(self):
        from .models import Club, ClubStatus, Membership
        user = self.scope["user"]
        if user.is_anonymous:
            return False
        try:
            club = Club.objects.get(pk=self.club_id, status=ClubStatus.DISCUSSION)
            return Membership.objects.filter(
                user=user, club=club, is_active=True
            ).exists()
        except Club.DoesNotExist:
            return False
```

### 2. Routing
```python
# apps/clubs/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/debate/(?P<club_id>\d+)/$", consumers.DebateConsumer.as_asgi()),
]
```

### 3. Actualizar ASGI
```python
# config/asgi.py
from apps.clubs.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

### 4. Template del debate (JavaScript vanilla)
```html
<div id="debate-messages" class="space-y-2 max-h-96 overflow-y-auto"></div>
<input id="debate-input" type="text" placeholder="Escribe un mensaje...">

<script>
const clubId = {{ club.id }};
const ws = new WebSocket(`ws://${window.location.host}/ws/debate/${clubId}/`);

ws.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const div = document.createElement('div');
    div.innerHTML = `<strong>${data.username}:</strong> ${data.message}`;
    document.getElementById('debate-messages').appendChild(div);
};

document.getElementById('debate-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && this.value.trim()) {
        ws.send(JSON.stringify({message: this.value.trim()}));
        this.value = '';
    }
});
</script>
```

## Consideraciones
- Los mensajes del debate NO se persisten en base de datos (decision de diseno)
- Cuando el club pasa a CLOSED, el WebSocket se desconecta
- Para dev sin Redis: usar InMemoryChannelLayer (solo 1 proceso)
```python
# Para dev sin Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```
