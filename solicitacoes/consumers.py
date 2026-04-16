import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GestorSolicitacaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated or user.perfilusuario.nivel != "gestor":
            await self.close()
            return

        self.contrato = user.perfilusuario.contrato
        self.group_name = f"gestor_{self.contrato}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def nova_solicitacao(self, event):
        await self.send(text_data=json.dumps({
            "type": "nova_solicitacao",
            "message": event["message"],
        }))


class PortariaConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print("🔥 PORTARIA CONECTOU")

    self.group_name = "portaria"

    await self.channel_layer.group_add(
        self.group_name,
        self.channel_name
    )

    await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def nova_solicitacao(self, event):
        await self.send(text_data=json.dumps({
            "type": "nova_solicitacao",
            "message": event.get("message", ""),
            "id": event.get("id")
        }))