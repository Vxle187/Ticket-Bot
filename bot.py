import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================
# KONFIGURATION
# ============================
TICKET_CHANNEL_ID = 1396969114442006539  # Channel, wo die Dropdown-Nachricht gesendet wird
LOGO_URL = "attachment://BLCP-Logo2.png"  # dein Logo aus dem Upload

# Rollen mit Schließ-Berechtigung
BEFUGTE_RANG_IDS = [1410124850265198602]  # Leitung/Admins

# Ticket-Kategorien
TICKET_CATEGORIES = {
    "📩 Bewerbungen": {
        "id": 1410111339359113318,
        "questions": [
            "Wie lautet dein Name?",
            "Wie alt bist du?",
            "Warum möchtest du dich bewerben?",
        ]
    },
    "⚠️ Beschwerden": {
        "id": 1410111382237483088,
        "questions": [
            "Gegen wen richtet sich die Beschwerde?",
            "Was ist genau passiert?",
            "Hast du Beweise (Screenshots etc.)?"
        ]
    },
    "🏛️ Leitungs Anliegen": {
        "id": 1410111463783268382,
        "questions": [
            "Worum geht es bei deinem Anliegen?",
            "Welche Vorschläge oder Probleme möchtest du ansprechen?",
        ]
    }
}

# Speicherung aller aktiven Tickets
user_tickets = {}


# ============================
# Dropdown Menü
# ============================
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
        category_data = TICKET_CATEGORIES[self.values[0]]
        category = guild.get_channel(category_data["id"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Ticket-Channel erstellen
        ticket_channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            category=category
        )

        # Ticket im Speicher speichern
        user_tickets[interaction.user.id] = {
            "channel_id": ticket_channel.id,
            "art": self.values[0],
            "antworten": [],
            "fragen": category_data["questions"].copy(),
            "created_at": discord.utils.utcnow().strftime("%d.%m.%Y %H:%M")
        }

        await ticket_channel.send(
            f"🎟️ Hallo {interaction.user.mention}, willkommen im **{self.values[0]}**-Ticket!\n"
            f"Bitte beantworte die folgenden Fragen nacheinander:"
        )

        # Erste Frage stellen
        first_question = category_data["questions"][0]
        await ticket_channel.send(f"❓ {first_question}")

        await interaction.response.send_message(
            f"✅ Dein Ticket wurde in {ticket_channel.mention} eröffnet.", ephemeral=True
        )


class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# ============================
# Nachrichten-Listener (Antworten speichern)
# ============================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Prüfen, ob Channel ein Ticket ist
    for uid, data in user_tickets.items():
        if data["channel_id"] == message.channel.id and message.author.id == uid:
            # Antwort speichern
            data["antworten"].append(message.content)

            # Nächste Frage stellen
            if len(data["antworten"]) < len(data["fragen"]):
                next_question = data["fragen"][len(data["antworten"])]
                await message.channel.send(f"❓ {next_question}")
            else:
                await message.channel.send("✅ Vielen Dank! Alle Fragen wurden beantwortet.")
            break

    await bot.process_commands(message)


# ============================
# Slash Command: Ticket schließen
# ============================
@bot.tree.command(name="ticketclose", description="Schließt das aktuelle Ticket (nur Leitung/Admins).")
async def ticketclose(interaction: discord.Interaction):
    # Rechteprüfung
    if not any((role.id in BEFUGTE_RANG_IDS) for role in interaction.user.roles):
        await interaction.response.send_message("❌ Du hast keine Berechtigung, Tickets zu schließen.", ephemeral=True)
        return

    channel = interaction.channel

    # Ticket-Eintrag finden
    ticket_owner_id = None
    ticket_data = None
    for uid, data in user_tickets.items():
        if data.get("channel_id") == channel.id:
            ticket_owner_id = uid
            ticket_data = data
            break

    if ticket_data:
        antworten_text_list = [f"**Antwort {i+1}:** {a}" for i, a in enumerate(ticket_data.get('antworten', []))]
        antworten_text = "\n".join(antworten_text_list) if antworten_text_list else "_Keine Antworten_"

        # Embed erstellen
        embed = discord.Embed(
            title=f"🗂 Ticket-Transkript: {ticket_data['art']}",
            description=f"Von: <@{ticket_owner_id}> (geschlossen von {interaction.user.mention})",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=LOGO_URL)
        embed.add_field(name="Antworten", value=antworten_text, inline=False)
        embed.set_footer(text=f"Erstellt: {ticket_data.get('created_at')}")

        # Transkript in Kategorie-Kanal posten
        category_id = TICKET_CATEGORIES[ticket_data["art"]]["id"]
        ziel_channel = interaction.guild.get_channel(category_id)
        if ziel_channel:
            await ziel_channel.send(embed=embed, file=discord.File("/mnt/data/BLCP-Logo2.png"))

        # Ticket aus Speicher löschen
        try:
            del user_tickets[ticket_owner_id]
        except KeyError:
            pass

        await interaction.response.send_message("✅ Ticket wird geschlossen...", ephemeral=True)
        await channel.delete()
    else:
        await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)


# ============================
# Bot Ready
# ============================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Eingeloggt als {bot.user}")
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        await channel.send("🎟️ Wähle unten eine Kategorie, um ein Ticket zu erstellen:", view=TicketView())


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
