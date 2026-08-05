from channels.generic.websocket import JsonWebsocketConsumer


class NotificationConsumer(JsonWebsocketConsumer):
    GROUP_PREFIX = "notifications"

    async def connect(self):
        user = self.scope.get("user")
        if user is None or getattr(user, "is_anonymous", True):
            await self.close()
            return

        self.user_id = user.id
        self.group_name = f"{NotificationConsumer.GROUP_PREFIX}_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name is not None and self.channel_layer is not None:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def notification_new(self, event):
        await self.send_json(event["payload"])