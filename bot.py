import discord
from discord.ext import commands
from discord import app_commands

# ==== SETTINGS ====
TOKEN = "DEIN_BOT_TOKEN_HIER"
GUILD_ID = 000000000000000000   # Server-ID
LOG_CHANNEL_ID = 1397304957518221312  # Ticket-Logs

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ==== Fragen für Tickets ====
QUESTIONS = {
    "bewerbung": [
        "Wie heißt du Ingame?",
        "Wie alt bist du?",
        "Warum möchtest du Teil unseres Teams werden?",
        "Welche Erfahrungen bringst du mit?",
    ],
    "beschwerde": [
        "Wen möchtest du melden?",
        "Was ist passiert?",
        "Hast du Beweise (z. B. Screenshots, Videos)?",
    ],
    "leitung": [
        "Worum geht es in deinem Anliegen?",
        "Welche Personen sind beteiligt?",
        "Beschreibe bitte alles so detailliert wie möglich.",
    ],
}


# ==== Ticket Dropdown ====
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📩 Bewerbungen", value="bewerbung", description="Erstelle ein Bewerbungs-Ticket"),
            discord.SelectOption(label="⚠️ Beschwerden", value="beschwerde", description="Erstelle ein Beschwerde-Ticket"),
            discord.SelectOption(label="👮 Leitungs Anliegen", value="leitung", description="Erstelle ein Ticket für die Leitung"),
        ]
        super().__init__(placeholder="Bitte wähle einen Grund", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category_id = {
            "bewerbung": 1410111339359113318,
            "beschwerde": 1410111382237483088,
            "leitung": 1410111463783268382,
        }

        category = guild.get_channel(category_id[self.values[0]])
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Ticket-Channel erstellen
        ticket_channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        # Embed Begrüßung
        embed = discord.Embed(
            title="🎫 Dein Ticket wurde erstellt!",
            description=f"Hallo {interaction.user.mention}, willkommen in deinem **{self.values[0]}**-Ticket.\nBitte beantworte die folgenden Fragen:",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=embed)

        # Fragen senden
        for question in QUESTIONS[self.values[0]]:
            await ticket_channel.send(f"👉 **{question}**")

        await interaction.response.send_message(f"✅ Dein Ticket wurde erstellt: {ticket_channel.mention}", ephemeral=True)

        # Logs
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📂 Neues Ticket von {interaction.user.mention}: {ticket_channel.mention}")


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# ==== /tickets Command ====
@tree.command(name="tickets", description="Ticket System Setup")
async def tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Ticket-System",
        description="Willkommen im Ticketsystem!\n\nBitte wähle unten einen Grund aus, um ein Ticket zu erstellen.\n\n**Wichtig:** Beschreibe dein Anliegen so genau wie möglich.",
        color=discord.Color.blue()
    )
    file = discord.File("BLCP-Logo2.png", filename="BLCP-Logo2.png")
    embed.set_image(url="attachment://BLCP-Logo2.png")
    embed.set_footer(text="Made by Vxle")

    await interaction.response.send_message(embed=embed, file=file, view=TicketView())


# ==== /ticketclose Command ====
@tree.command(name="ticketclose", description="Schließt das aktuelle Ticket")
async def ticketclose(interaction: discord.Interaction):
    if interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("✅ Dieses Ticket wird geschlossen...", ephemeral=True)

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🗑️ Ticket {interaction.channel.name} wurde von {interaction.user.mention} geschlossen.")

        await interaction.channel.delete()
    else:
        await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)


# ==== Bot Ready Event ====
@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Bot ist online als {bot.user}")


bot.run(TOKEN)
