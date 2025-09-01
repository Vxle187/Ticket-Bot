import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import os

# ---------- CONFIG ----------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")  # Render-Umgebungsvariable
GUILD_ID = 1396969113955602562  # <- DEINE SERVER ID hier!
LOG_CHANNEL_ID = 1397304957518221312
TICKET_CHANNEL_ID = 1396969114442006539  # <- Channel ID, wo die Setup Nachricht automatisch rein soll
LOGO_URL = "https://i.ibb.co/DHMjTcWC/BLCP-Logo2-3.png"

# Kategorien
TICKET_CATEGORY_IDS = {
    "bewerbungen": 1410111339359113318,
    "beschwerden": 1410111382237483088,
    "leitungs-anliegen": 1410111463783268382,
}

# Rollen mit Schließen-Recht
BEFUGTE_RANG_IDS = [1410124850265198602]

# Fragen je Ticket-Art
TICKET_FRAGEN = {
    "bewerbungen": [
        "Wie lautet dein vollständiger Name?",
        "Wie alt bist du?",
        "Warum möchtest du Teil des Teams werden?",
    ],
    "beschwerden": [
        "Gegen wen oder was richtet sich deine Beschwerde?",
        "Bitte beschreibe den Vorfall ausführlich.",
        "Hast du Beweise (z.B. Screenshots, Clips)?",
    ],
    "leitungs-anliegen": [
        "Bitte beschreibe dein Anliegen an die Leitung.",
        "Welche Lösung wünschst du dir?",
    ],
}

# Speicher im RAM (nicht persistent!)
user_tickets = {}

# ---------- BOT ----------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# Ticket Dropdown Menü
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bewerbungen", value="bewerbungen", emoji="📝"),
            discord.SelectOption(label="Beschwerden", value="beschwerden", emoji="⚠️"),
            discord.SelectOption(label="Leitungs Anliegen", value="leitungs-anliegen", emoji="📢"),
        ]
        super().__init__(placeholder="Wähle eine Ticket-Art...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        art = self.values[0]
        category_id = TICKET_CATEGORY_IDS.get(art)

        if not category_id:
            await interaction.response.send_message("❌ Kategorie nicht gefunden.", ephemeral=True)
            return

        guild = interaction.guild
        category = guild.get_channel(category_id)

        # Ticket erstellen
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            },
        )

        await interaction.response.send_message(f"✅ Ticket erstellt: {ticket_channel.mention}", ephemeral=True)

        # Begrüßung senden
        await ticket_channel.send(
            f"👋 Willkommen {interaction.user.mention}!\n"
            f"Bitte beantworte die folgenden Fragen, damit wir dir schnell helfen können."
        )

        # Fragen stellen
        antworten = []
        for frage in TICKET_FRAGEN.get(art, []):
            await ticket_channel.send(f"**{frage}**")

            def check(m): 
                return m.author == interaction.user and m.channel == ticket_channel
            try:
                msg = await bot.wait_for("message", check=check, timeout=300)
                antworten.append(msg.content)
            except asyncio.TimeoutError:
                antworten.append("_Keine Antwort_")

        # Speichern (optional, wird nicht fürs Schließen gebraucht)
        user_tickets[interaction.user.id] = {
            "art": art,
            "channel_id": ticket_channel.id,
            "antworten": antworten,
            "created_at": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        }

        # Übersicht schicken
        embed = discord.Embed(
            title=f"📂 Ticket: {art.capitalize()}",
            description=f"Von {interaction.user.mention}",
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=LOGO_URL)

        for i, ant in enumerate(antworten, start=1):
            embed.add_field(name=f"Frage {i}", value=ant, inline=False)

        embed.set_footer(text="BloodLife Police Department | Made by Vxle", icon_url=LOGO_URL)
        await ticket_channel.send(embed=embed)


class TicketDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# ==== /angenommen Command ====
@tree.command(name="angenommen", description="Markiert den User im Ticket als angenommen")
async def angenommen(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ Dieser Befehl funktioniert nur in einem Ticket.", ephemeral=True)
        return

    # Den Ticket-Ersteller finden (aus Overwrites)
    ticket_user = None
    for overwrite in interaction.channel.overwrites:
        if isinstance(overwrite, discord.Member):
            ticket_user = overwrite
            break

    if ticket_user is None:
        await interaction.response.send_message("⚠️ Konnte den Ticket-Ersteller nicht finden.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎉 Glückwunsch!",
        description=f"{ticket_user.mention}, **du hast es geschafft!** 🎊\n\nWillkommen im Team!",
        color=discord.Color.green()
    )
    embed.set_footer(text="BloodLife Police Department")

    await interaction.response.send_message(embed=embed)


# ==== /ticketsetup Command ====
@tree.command(name="ticketsetup", description="Setup für Ticketsystem")
async def ticketsetup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📩 BloodLife | Ticketsystem",
        description="Bitte wähle im Dropdown-Menü aus, für welchen Bereich du ein Ticket erstellen möchtest.",
        color=discord.Color.red(),
    )
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_image(url=LOGO_URL)
    embed.set_footer(text="BloodLife Police Department | Made by Vxle", icon_url=LOGO_URL)

    await interaction.response.send_message(embed=embed, view=TicketDropdownView())


# ==== /ticketclose Command ====
@tree.command(name="ticketclose", description="Schließt das aktuelle Ticket")
async def ticketclose(interaction: discord.Interaction):
    if not any((role.id in BEFUGTE_RANG_IDS) for role in interaction.user.roles):
        await interaction.response.send_message("❌ Du darfst keine Tickets schließen.", ephemeral=True)
        return

    channel = interaction.channel
    if not channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
        return

    # Versuche den User aus dem Channel zu finden
    ticket_user = None
    for member in channel.members:
        if member.bot is False:  # wir nehmen an: der Nicht-Bot ist der Ersteller
            ticket_user = member
            break

    # Log-Channel
    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

    embed = discord.Embed(
        title="🗂 Ticket geschlossen",
        description=f"Channel: {channel.name}\nGeschlossen von: {interaction.user.mention}",
        color=discord.Color.orange(),
    )
    embed.set_footer(text="BloodLife Police Department | Made by Vxle")

    if ticket_user:
        embed.add_field(name="Ersteller", value=ticket_user.mention, inline=False)

    await log_channel.send(embed=embed)

    await interaction.response.send_message("✅ Ticket geschlossen.", ephemeral=True)
    await channel.delete()


# ---------- START ----------
@bot.event
async def on_ready():
    try:
        # Erst Guild-Commands syncen
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Commands für Guild {GUILD_ID} synchronisiert")
    except Exception as e:
        print(f"⚠️ Guild-Sync fehlgeschlagen: {e}")
        await tree.sync()
        print("🌍 Commands global synchronisiert")

    print(f"🤖 Bot online als {bot.user}")

    # Automatisch Ticket-System-Embed in den festen Channel schicken
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📩 BloodLife | Ticketsystem",
            description="Bitte wähle im Dropdown-Menü aus, für welchen Bereich du ein Ticket erstellen möchtest.",
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=LOGO_URL)
        embed.set_image(url=LOGO_URL)
        embed.set_footer(text="BloodLife Police Department | Made by Vxle", icon_url=LOGO_URL)

        await channel.send(embed=embed, view=TicketDropdownView())


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("❌ DISCORD_TOKEN nicht gefunden! Bitte in Render als Environment Variable setzen.")
    bot.run(DISCORD_TOKEN)
