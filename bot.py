import os
from discord.ext import commands

bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
