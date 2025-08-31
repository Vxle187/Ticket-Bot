import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime

# Bot-Setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Dein Logo (Pfad oder Upload-Link)
LOGO_URL = "https://cdn.discordapp.com/attachments/xxxxxx/BLCP-Logo2.png"  # hier dein Logo hochladen und URL einfügen

# Ticket Kategorien
TICKET_CATEGORY_IDS = {
    "bewerbungen": 1410111339359113318,
    "beschwerden": 1410111382237483088,
    "leitungs-anliegen": 1410111463783268382,
}

# Rollen mit Schließen-Rechten
BEFUGTE_RANG_IDS = [1410124850265198602]  # Leitung/Admins

# Speicher für Tickets
user_tickets = {}


# --------------------------
# Dropdown-Menü
# --------------------------
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bewerbungen", description="Erstelle ein Bewerbungsticket", value="bewerbungen"),
            discord.SelectOption(label="Beschwerden", description="Erstelle ein Beschwerdeticket", value="beschwerden"),
            discord.SelectOption(label="Leitungs Anliegen", description="Erstelle ein Ticket für die Leitung", value="leitungs-anliegen"),
        ]
        super().__init__(placeholder="Bitte wähle einen Grund", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        art = self.values[0]
        guild = interaction.guild
        category_id = TICKET_CATEGORY_IDS.get(art)
        category = discord.utils.get(guild.categories, id=category_id)

        # Check ob User schon ein Ticket hat
        if interaction.user.id in user_tickets:
            await interaction.response.send_message("❌ Du hast bereits ein offenes Ticket.", ephemeral=True)
            return

        # Ticket Channel erstellen
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)

        # Fragen je nach Kategorie
        fragen = []
        if art == "bewerbungen":
            fragen = ["Wie heißt du Ingame?", "Wie alt bist du?", "Warum möchtest du Teil des Teams werden?"]
        elif art == "beschwerden":
            fragen = ["Gegen wen richtet sich deine Beschwerde?", "Was ist genau passiert?", "Hast du Beweise? (Screenshots, Clips)"]
        elif art == "leitungs-anliegen":
            fragen = ["Welches Anliegen hast du an die Leitung?", "Bitte beschreibe dein Anliegen so genau wie möglich."]

        # Ticket speichern
        user_tickets[interaction.user.id] = {
            "channel_id": channel.id,
            "art": art,
            "fragen": fragen,
            "antworten": [],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        await channel.send(f"👋 Hallo {interaction.user.mention}, bitte beantworte die folgenden Fragen.")
        await channel.send(f"❓ {fragen[0]}")

        await interaction.response.send_message(f"✅ Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# --------------------------
# Command zum Setup des Systems
# --------------------------
@tree.command(name="setup_tickets", description="Ticket-System Nachricht senden (Admin)")
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Ticket-System",
        description="Willkommen im Ticketsystem! Bitte wähle einen Grund aus, um dein Ticket zu erstellen.\n\n**Wichtig:**\nBitte beschreibe dein Anliegen so genau wie möglich.",
        color=discord.Color.red()
    )
    embed.set_image(url=LOGO_URL)
    embed.set_footer(text="Made by BloodLife")
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket-System wurde eingerichtet.", ephemeral=True)


# --------------------------
# Antworten speichern & Übersicht senden
# --------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    for uid, data in user_tickets.items():
        if data["channel_id"] == message.channel.id and message.author.id == uid:
            data["antworten"].append(message.content)

            if len(data["antworten"]) < len(data["fragen"]):
                next_question = data["fragen"][len(data["antworten"])]
                await message.channel.send(f"❓ {next_question}")
            else:
                # Übersicht erstellen
                embed = discord.Embed(
                    title="📋 Deine Ticket-Übersicht",
                    description="Hier sind deine Antworten im Überblick:",
                    color=discord.Color.red()
                )
                for frage, antwort in zip(data["fragen"], data["antworten"]):
                    embed.add_field(name=f"❓ {frage}", value=f"💬 {antwort}", inline=False)

                embed.set_image(url=LOGO_URL)
                embed.set_footer(text="BloodLife Police Department")
                await message.channel.send(embed=embed)

                await message.channel.send("✅ Vielen Dank! Alle Fragen wurden beantwortet. Ein Teammitglied wird sich melden.")
            break

    await bot.process_commands(message)


# --------------------------
# Ticket schließen
# --------------------------
@tree.command(name="ticketclose", description="Schließt das aktuelle Ticket (nur Leitung/Admins).")
async def ticketclose(interaction: discord.Interaction):
    if not any((role.id == 1410124850265198602) or (role.id in BEFUGTE_RANG_IDS) for role in interaction.user.roles):
        await interaction.response.send_message("❌ Du hast keine Berechtigung, Tickets zu schließen.", ephemeral=True)
        return

    channel = interaction.channel
    ticket_owner_id = None
    ticket_data = None
    for uid, data in user_tickets.items():
        if data.get("channel_id") == channel.id:
            ticket_owner_id = uid
            ticket_data = data
            break

    if channel and channel.name.startswith("ticket-"):
        if ticket_data:
            antworten_text = "\n".join(
                [f"**{frage}:** {antwort}" for frage, antwort in zip(ticket_data["fragen"], ticket_data["antworten"])]
            ) or "_Keine Antworten_"

            embed = discord.Embed(
                title=f"🗂 Ticket-Transkript: {ticket_data['art'].capitalize()}",
                description=f"Von: <@{ticket_owner_id}> (geschlossen von {interaction.user.mention})",
                color=discord.Color.orange()
            )
            embed.add_field(name="Antworten", value=antworten_text, inline=False)
            embed.set_thumbnail(url=LOGO_URL)
            embed.set_footer(text=f"Erstellt: {ticket_data.get('created_at')}")

            ziel_channel = discord.utils.get(interaction.guild.text_channels, id=TICKET_CATEGORY_IDS[ticket_data["art"]])
            if ziel_channel:
                await ziel_channel.send(embed=embed)

            try:
                del user_tickets[ticket_owner_id]
            except KeyError:
                pass

        await interaction.response.send_message("✅ Ticket wird geschlossen und gelöscht.", ephemeral=True)
        await channel.delete()
    else:
        await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)


# --------------------------
# Bot starten
# --------------------------
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot ist online als {bot.user}")


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
