from typing import Type
from maubot import Plugin, MessageEvent
from maubot.handlers import command, event
from mautrix.types import EventType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
import aiohttp


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("n8n_webhook_url")
        helper.copy("trigger_on_mention")
        helper.copy("trigger_on_dm")
        helper.copy("trigger_command")
        helper.copy("send_typing")


class N8nAgentBot(Plugin):
    async def start(self) -> None:
        self.config.load_and_update()
        self.log.info(f"N8n Agent Bot started, webhook URL: {self.config['n8n_webhook_url']}")

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @command.new("hello")
    async def hello_world(self, evt: MessageEvent) -> None:
        await evt.reply("Hello, World!")

    @event.on(EventType.ROOM_MESSAGE)
    async def message_handler(self, evt: MessageEvent) -> None:
        """Handle incoming messages and forward to n8n agent."""

        # Get the message content
        message = evt.content.body

        # Prepare payload for n8n
        payload = {
            "message": message,
            "sender": evt.sender,
            "sender_name": evt.content.get("body", "Unknown"),
            "room_id": evt.room_id,
            "event_id": evt.event_id,
            "timestamp": evt.timestamp,
        }

        # Send to n8n webhook
        try:
            webhook_url = self.config["n8n_webhook_url"]
            self.log.debug(f"Sending message to n8n: {message[:50]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        self.log.info(f"Successfully triggered n8n agent for message from {evt.sender}")
                        # n8n will handle sending the response back to Matrix
                    else:
                        error_text = await resp.text()
                        self.log.error(f"n8n webhook returned status {resp.status}: {error_text}")
                        await evt.respond(f"⚠️ Agent error: Received status {resp.status} from workflow")
        except aiohttp.ClientError as e:
            self.log.error(f"Network error calling n8n webhook: {e}")
            await evt.respond("⚠️ Agent error: Unable to reach workflow service")
        except Exception as e:
            self.log.error(f"Unexpected error calling n8n webhook: {e}")
            await evt.respond(f"⚠️ Agent error: {str(e)}")
        finally:
            # Stop typing indicator
            if self.config["send_typing"]:
                await self.client.set_typing(evt.room_id, typing=False)
