from typing import Any, Type
import aiohttp
from maubot import Plugin, MessageEvent
from maubot.handlers import command, event
from mautrix.types import EventType, MessageType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("n8n_webhook_url")
        helper.copy("enable_whitelist")
        helper.copy("whitelist_users")
        helper.copy("trigger_on_mention")
        helper.copy("trigger_on_dm")
        helper.copy("trigger_command")
        helper.copy("send_typing")


class N8nAgentBot(Plugin):
    async def start(self) -> None:
        if not self.config:
            self.log.debug("⚠️ Agent error: config not found!")
            return

        self.config.load_and_update()
        self.log.info(f"N8n Agent Bot started, webhook URL: {self.config['n8n_webhook_url']}")


    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config


    async def _check_whitelist(self, evt: MessageEvent) -> bool:
        if not self.config:
            return False

        if not self.config["enable_whitelist"]:
            return True

        if evt.sender in self.config["whitelist_users"]:
            return True

        return False


    async def _should_process_message(self, evt: MessageEvent) -> bool:
        """Determine if this message should trigger the agent."""
        if not self.config:
            return False

        # Ignore our own messages
        if evt.sender == self.client.mxid:
            return False

        # Only process text messages
        if evt.content.msgtype != MessageType.TEXT:
            return False

        #Check whitelist
        if not await self._check_whitelist(evt):
            return False

        message = evt.content.body
        if not isinstance(message, str):
            return False

        # Check if it starts with the trigger command
        if self.config["trigger_command"]:
            trigger = self.config["trigger_command"]

            if isinstance(trigger, str):
                if message.startswith(trigger):
                    return True

        # Check if we're in a DM (room with only 2 members)
        if self.config["trigger_on_dm"]:
            try:
                members = await self.client.get_joined_members(evt.room_id)
                if len(members) == 2:
                    return True
            except Exception as e:
                self.log.warning(f"Failed to get room members: {e}")

        # Check if bot was mentioned
        if self.config["trigger_on_mention"]:
            bot_mention = self.client.mxid
            if bot_mention in message:
                return True

        return False


    async def _trigger_workflow(self, msg: str, evt: MessageEvent) -> None:
        if not self.config:
            await evt.respond("⚠️ Agent error: config not found!")
            return

        # Prepare payload for n8n
        payload = {
            "message": msg,
            "sender": evt.sender,
            "sender_name": evt.content.get("body", "Unknown"),
            "room_id": evt.room_id,
            "event_id": evt.event_id,
            "timestamp": evt.timestamp,
        }

        # Send to n8n webhook
        try:
            webhook_url = self.config["n8n_webhook_url"]
            self.log.debug(f"Sending message to n8n: {msg[:50]}...")

            async with aiohttp.ClientSession() as session:
                async with session.get(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
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

        return


    @event.on(EventType.ROOM_MESSAGE)
    async def message_handler(self, evt: MessageEvent) -> None:
        """Handle incoming messages and forward to n8n agent."""
        if not self.config:
            await evt.respond("⚠️ Agent error: config not found!")
            return

        if not await self._should_process_message(evt):
            return

        await evt.mark_read()
        message = evt.content.body

        if not isinstance(message, str):
            return

        if self.config["trigger_command"]:
            trigger = self.config["trigger_command"]

            if isinstance(trigger, str):
                if message.startswith(trigger):
                    message = message[len(self.config["trigger_command"]):].strip()

        # Send typing indicator if enabled
        if self.config["send_typing"]:
            await self.client.set_typing(evt.room_id, timeout=30000)

        await self._trigger_workflow(message, evt)

        # Stop typing indicator
        if self.config["send_typing"]:
            await self.client.set_typing(evt.room_id, timeout=0)

        return


    @command.new(name="status", help="Command to get the status of agent.")
    async def trigger_agent(self, evt: MessageEvent) -> None:
        """Trigger agent with trigger command."""
        await evt.respond("Hello world!")
