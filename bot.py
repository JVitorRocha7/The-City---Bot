import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="-", intents=intents)

COGS = [
    "cogs.fichas",
    "cogs.dados",
    "cogs.mod",
    "cogs.info",
    "cogs.utils",
    "cogs.iniciativa",
    "cogs.music"
]

async def main():
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
            print(f"Cog carregada: {cog}")
        await bot.start(os.getenv("DISCORD_TOKEN"))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online: {bot.user} | Servidores: {len(bot.guilds)}")

asyncio.run(main())