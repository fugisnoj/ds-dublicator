import os
import logging
import discord
from discord import Webhook, File, Embed
import aiohttp
from dotenv import load_dotenv
from collections import deque

load_dotenv()
TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # URL вебхука целевого канала
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID'))  # ID целевого канала

if not TOKEN or not WEBHOOK_URL or not TARGET_CHANNEL_ID:
    raise SystemExit('TOKEN, WEBHOOK_URL и TARGET_CHANNEL_ID должны быть установлены в .env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('duplicator')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True


class ForwardBot(discord.Client):
    def __init__(self, webhook_url, target_channel_id, **options):
        super().__init__(intents=intents, **options)
        self.webhook_url = webhook_url
        self.target_channel_id = target_channel_id
        self._recent_forwarded = deque(maxlen=2000)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (id={self.user.id})')

    async def on_message(self, message: discord.Message):
        # Игнорируем сообщения от ботов
        if message.author.bot:
            return

        # Игнорируем сообщения в целевом канале (чтобы не повторять свои пересланные сообщения)
        if message.channel.id == self.target_channel_id:
            return

        # Проверяем кэш, чтобы не пересылать одно и то же сообщение дважды
        if message.id in self._recent_forwarded:
            return

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.webhook_url, session=session)

            # Подготовка файлов
            files = [await a.to_file() for a in message.attachments] if message.attachments else []

            # Подготовка эмбедов
            embeds = [Embed.from_dict(e.to_dict()) for e in message.embeds] if message.embeds else []

            try:
                await webhook.send(
                    content=message.content if message.content else None,
                    username=str(message.author),
                    avatar_url=message.author.display_avatar.url,
                    files=files,
                    embeds=embeds,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                # Добавляем ID исходного сообщения в кэш
                self._recent_forwarded.append(message.id)
            except Exception:
                logger.exception('Ошибка при пересылке сообщения')


if __name__ == '__main__':
    bot = ForwardBot(webhook_url=WEBHOOK_URL, target_channel_id=TARGET_CHANNEL_ID)
    bot.run(TOKEN)
