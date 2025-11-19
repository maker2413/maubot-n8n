from typing import Type
from maubot import Plugin, MessageEvent
from maubot.handlers import command, event
from mautrix.types import EventType, MessageType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
import aiohttp
import time


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
        self.config.load_and_update()
        self.log.info(f"N8n Agent Bot started, webhook URL: {self.config['n8n_webhook_url']}")

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def _check_whitelist(self, evt: MessageEvent) -> bool:
        if not self.config["enable_whitelist"]:
            return True

        if evt.sender in self.config["whitelist_users"]:
            return True

        return False

    async def _should_process_message(self, evt: MessageEvent) -> bool:
        """Determine if this message should trigger the agent."""
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

        # Check if it starts with the trigger command
        if self.config["trigger_command"] and message.startswith(self.config["trigger_command"]):
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

    @event.on(EventType.ROOM_MESSAGE)
    async def message_handler(self, evt: MessageEvent) -> None:
        """Handle incoming messages and forward to n8n agent."""

        if not await self._should_process_message(evt):
            return

        await evt.mark_read()
        message = evt.content.body

        # Send typing indicator if enabled
        if self.config["send_typing"]:
            await self.client.set_typing(evt.room_id, timeout=30000)

        self.log.debug("****Made it here!****")
        time.sleep(3)

        if self.config["send_typing"]:
            await self.client.set_typing(evt.room_id, timeout=0)

        return

    def get_trigger_command(self) -> str:
        return self.config["trigger_command"]

    @command.new(name=get_trigger_command, help="Command to trigger agent")
    async def trigger_agent(self, evt: MessageEvent) -> None:
        """Trigger agent with trigger command."""
        #self.message_handler(self, evt)
        await evt.respond("Hello world!")
