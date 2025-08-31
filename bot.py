import os
import discord
from discord.ext import commands

# Intents aktivieren
intents = discord.Intents.default()
intents.message_content = True  # Wichtig, sonst liest der Bot keine Nachrichten

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

# Token aus Environment Variable laden
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
