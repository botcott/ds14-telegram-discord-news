import json
import logging
import os
import re
import subprocess
from urllib.parse import quote
from discord.ext import commands
from dotenv import load_dotenv

with open(f"{os.path.dirname(__file__)}/config/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

load_dotenv()

# .json
NOTIF_CHANNEL = int(cfg["notif_channel"])
DS14_CHANGES_CHANNEL = int(cfg["ds14_changes_channel"])
TELEGRAM_CHAT_ID = cfg["telegram_chat_id"]

# .env
TELEGRAM_BOT_TOKEN = "8322759875:AAEV_FusretTvAyS65G_ev07zcZrynrHpto"

def handle_headers(m):
    hashes = m.group(1)
    text = m.group(2).strip()
    if len(hashes) > 1:
        return f'<b>{text}</b>\n'
    else:
        return f'<b>{text}</b>'

class TelegramDiscordCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id not in (NOTIF_CHANNEL, DS14_CHANGES_CHANNEL):
            return

        content = message.content

        # Обработка упоминаний каналов
        channel_mentions = re.findall(r'<#(\d+)>', content)
        for ch_id in channel_mentions:
            channel_obj = self.bot.get_channel(int(ch_id))
            ch_name = channel_obj.name if channel_obj else "неизвестный-канал"
            content = content.replace(f'<#{ch_id}>', f'канал "{ch_name}"')

        # Замена текстовых кодов эмодзи на реальные символы
        emoji_map = {
            ":hammer_pick:": "🛠️",
            ":new:": "🆕",
            ":x:": "❌",
            ":white_check_mark:": "✅",
            ":warning:": "⚠️",
            ":information_source:": "ℹ️"
        }
        for code, emoji in emoji_map.items():
            content = content.replace(code, emoji)

        content = re.sub(r'@(everyone|here)', '', content)
        content = re.sub(r'<@!?\d+>', '', content)
        content = re.sub(r'<@&\d+>', '', content)
        content = re.sub(r':\w+:', '', content)

        content = re.sub(
            r'^(#{1,4})\s+(.*)',
            handle_headers,
            content,
            flags=re.MULTILINE
        )

        content = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2">\1</a>',
            content
        )

        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'(\*|_)(.*?)(\*|_)', r'\2', content)
        content = re.sub(r'~~(.*?)~~', r'\1', content)
        content = re.sub(r'`(.*?)`', r'\1', content)
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

        content = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        
        prefix_href = "https://discord.com/channels/1030160796401016883"

        if message.channel.id == NOTIF_CHANNEL: 
            prefix = f"<a href=\"{prefix_href}/1030914308097445939\">Новостное оповещение</a>:\n\n" 
        else: 
            if message.author.webhook_id:
                server_changes  = message.author.name 
            else:
                server_changes = "Неизвестно"
            prefix = f"<a href=\"{prefix_href}/1186681361021554818\">Изменение сборки {server_changes}:</a>:\n\n"
        
        end_message = "\n\n#Новости\n\nЖдём тебя в <a href=\"https://t.me/deadspace14\">💬Чате станции</a>"
        message_to_telegram = prefix + content + end_message

        if not message_to_telegram.strip():
            return

        try:
            escaped_message = quote(message_to_telegram)
            curl_cmd = (
                f'curl -s -X POST '
                f'"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" '
                f'-d "chat_id={TELEGRAM_CHAT_ID}&text={escaped_message}&parse_mode=HTML&disable_web_page_preview=true"'
            )
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Ошибка curl: {result.stderr}")
            else:
                self.logger.info(f"Отправлено в Telegram: {message_to_telegram}")

        except Exception as e:
            self.logger.error(f"Ошибка отправки: {e}")