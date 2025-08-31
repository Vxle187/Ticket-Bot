import os
import discord
from discord.ext import commands

# Intents aktivieren
intents = discord.Intents.default()
intents.message_content = True  # wichtig für Befehle per Nachrichten

# Bot erstellen
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: Bot ist online
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

# Testbefehl: !ping
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Der Bot läuft!")

# Bot starten mit Token aus Environment Variable
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
