import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime

# Bot Setup mit Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# IDs
TICKET_CATEGORY_IDS = {
    "Bewerbungen": 1410111339359113318,
    "Beschwerden": 1410111382237483088,
    "Leitungs Anliegen": 1410111463783268382
}

TICKET_LOG_CHANNEL_ID = 1397304957518221312
BEFUGTE_RANG_IDS = [1410124850265198602]  # Leitung/Admin Rolle

LOGO_URL = "attachment://BLCP-Logo2.png"

# Speicher für Tickets
user_tickets = {}


# Dropdown-Menü
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bewerbungen", description="Bewerbung erstellen", emoji="📝"),
            discord.SelectOption(label="Beschwerden", description="Eine Beschwerde einreichen", emoji="⚠️"),
            discord.SelectOption(label="Leitungs Anliegen", description="Kontakt mit der Leitung", emoji="📌"),
        ]
        super().__init__(placeholder="Wähle eine Ticket-Art...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        art = self.values[0]
        category_id = TICKET_CATEGORY_IDS[art]
        category = discord.utils.get(interaction.guild.categories, id=category_id)

        # Ticket Channel erstellen
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            topic=f"Ticket von {interaction.user} ({interaction.user.id})"
        )

        # Fragen definieren
        fragen = []
        if art == "Bewerbungen":
            fragen = ["Wie heißt du?", "Warum möchtest du dich bewerben?", "Welche Erfahrungen hast du?"]
        elif art == "Beschwerden":
            fragen = ["Gegen wen richtet sich die Beschwerde?", "Was ist passiert?", "Hast du Beweise?"]
        elif art == "Leitungs Anliegen":
            fragen = ["Worum geht es bei deinem Anliegen?", "Warum sollte es die Leitung klären?"]

        antworten = []
        def check(m): return m.author == interaction.user and m.channel == channel

        await channel.send(f"👋 Willkommen {interaction.user.mention}, bitte beantworte die folgenden Fragen:")

        for frage in fragen:
            await channel.send(f"❓ {frage}")
            msg = await bot.wait_for("message", check=check)
            antworten.append(msg.content)

        # Übersicht Embed
        embed = discord.Embed(
            title=f"📂 Ticket Übersicht – {art}",
            description=f"Ticket von {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        for i, (frage, antwort) in enumerate(zip(fragen, antworten), 1):
            embed.add_field(name=f"Frage {i}: {frage}", value=antwort, inline=False)

        embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text="BloodLife Police Department | Made by Vxle")

        file = discord.File("BLCP-Logo2.png", filename="BLCP-Logo2.png")
        await channel.send(embed=embed, file=file, view=TicketCloseView())

        # Ticket speichern
        user_tickets[interaction.user.id] = {
            "channel_id": channel.id,
            "art": art,
            "antworten": antworten,
            "created_at": datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M")
        }

        await interaction.response.send_message(f"✅ Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)


# View für Dropdown
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# Button fürs Schließen
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket schließen", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Rechte prüfen
        if not any(role.id in BEFUGTE_RANG_IDS for role in interaction.user.roles):
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

        if not ticket_data:
            await interaction.response.send_message("❌ Ticketdaten nicht gefunden.", ephemeral=True)
            return

        # Transkript ins Log senden
        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title=f"📑 Ticket-Log: {ticket_data['art']}",
                description=f"Von: <@{ticket_owner_id}> | Geschlossen von {interaction.user.mention}",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            antworten_text = "\n".join([f"**{i+1}.** {a}" for i, a in enumerate(ticket_data['antworten'])])
            embed.add_field(name="Antworten", value=antworten_text or "_Keine Antworten_", inline=False)
            embed.set_thumbnail(url=LOGO_URL)
            embed.set_footer(text="BloodLife Police Department | Made by Vxle")

            file = discord.File("BLCP-Logo2.png", filename="BLCP-Logo2.png")
            await log_channel.send(embed=embed, file=file)

        # Ticket löschen
        del user_tickets[ticket_owner_id]
        await interaction.response.send_message("✅ Ticket wird geschlossen und gelöscht.", ephemeral=True)
        await channel.delete()


# Setup
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Eingeloggt als {bot.user}")


# Command zum Setup des Ticket-Systems
@tree.command(name="ticketsetup", description="Erstellt das Ticket-Panel mit Dropdown.")
async def ticketsetup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Ticket-System",
        description="Wähle unten die Kategorie aus, um ein Ticket zu erstellen.",
        color=discord.Color.blue()
    )
    file = discord.File("BLCP-Logo2.png", filename="BLCP-Logo2.png")
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="BloodLife Police Department | Made by Vxle")
    await interaction.channel.send(embed=embed, file=file, view=TicketView())
    await interaction.response.send_message("✅ Ticket-Panel erstellt.", ephemeral=True)


# Bot starten
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
