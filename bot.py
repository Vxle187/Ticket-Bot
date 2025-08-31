import os
import discord
from discord.ext import commands
from discord.ui import View, Select

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Channel, wo die Ticket-Nachricht automatisch gepostet wird
TICKET_CHANNEL_ID = 123456789012345678  # <-- DEINE Channel-ID hier

# Kategorien für Tickets
TICKET_CATEGORIES = {
    "📩 Bewerbungen": 1410111339359113318,
    "⚠️ Beschwerden": 1410111382237483088,
    "🏛️ Leitungs Anliegen": 1410111463783268382
}


class TicketDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📩 Bewerbungen", description="Ticket für Bewerbungen"),
            discord.SelectOption(label="⚠️ Beschwerden", description="Ticket für Beschwerden"),
            discord.SelectOption(label="🏛️ Leitungs Anliegen", description="Ticket für die Leitung")
        ]
        super().__init__(placeholder="Wähle eine Kategorie...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category_id = TICKET_CATEGORIES[self.values[0]]
        category = guild.get_channel(category_id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Ticket-Channel erstellen
        ticket_channel = await guild.create_text_channel(
            f"{self.values[0]}-{interaction.user.name}",
            overwrites=overwrites,
            category=category
        )

        await ticket_channel.send(
            f"🎟️ Hallo {interaction.user.mention}, willkommen im **{self.values[0]}**-Ticket!\n"
            "Bitte beschreibe dein Anliegen hier."
        )

        await interaction.response.send_message(
            f"✅ Dein Ticket wurde in {ticket_channel.mention} eröffnet.", ephemeral=True
        )


class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


@bot.event
async def on_ready():
    print(f"✅ Eingeloggt als {bot.user}")
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        await channel.send("🎟️ Wähle unten eine Kategorie, um ein Ticket zu erstellen:", view=TicketView())


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
