import os
import discord
from discord.ext import commands

# Intents aktivieren
intents = discord.Intents.default()
intents.message_content = True  # Wichtig für Commands

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

# Token aus Render-Env laden
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
