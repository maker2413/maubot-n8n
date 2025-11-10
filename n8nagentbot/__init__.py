from typing import Type
from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper


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
