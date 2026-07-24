import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.database import init_db

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

INITIAL_EXTENSIONS = [
    "cogs.character",
    "cogs.combat",
    "cogs.campaign",
    "cogs.cards",
]


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")


async def main():
    await init_db()
    async with bot:
        for ext in INITIAL_EXTENSIONS:
            await bot.load_extension(ext)
        if not TOKEN:
            raise RuntimeError(
                "DISCORD_TOKEN이 설정되지 않았어요. .env 파일에 DISCORD_TOKEN=본인토큰 을 추가하세요."
            )
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
