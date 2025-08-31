import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import os

# ---------- CONFIG ----------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")  # Token aus Render-Env
GUILD_ID = 123456789012345678  # <- deine Server-ID HIER einsetzen!
LOG_CHANNEL_ID = 1397304957518221312
LOGO_URL = "https://cdn.discordapp.com/attachments/1396969116195360941/1411723745546211409/BLCP-Logo2_3.png"

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

# Speicher
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

        # Fragen stellen
        antworten = []
        for frage in TICKET_FRAGEN.get(art, []):
            await ticket_channel.send(f"**{frage}**")

            def check(m): return m.author == interaction.user and m.channel == ticket_channel
            try:
                msg = await bot.wait_for("message", check=check, timeout=300)
                antworten.append(msg.content)
            except asyncio.TimeoutError:
                antworten.append("_Keine Antwort_")

        # Speichern
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


# Ticket Setup Command
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


# Ticket Close Command
@tree.command(name="ticketclose", description="Schließt das aktuelle Ticket")
async def ticketclose(interaction: discord.Interaction):
    if not any((role.id in BEFUGTE_RANG_IDS) for role in interaction.user.roles):
        await interaction.response.send_message("❌ Du darfst keine Tickets schließen.", ephemeral=True)
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
        await interaction.response.send_message("❌ Kein Ticket gefunden.", ephemeral=True)
        return

    # Übersicht für Logs
    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
    embed = discord.Embed(
        title=f"🗂 Ticket-Transkript: {ticket_data['art'].capitalize()}",
        description=f"Von: <@{ticket_owner_id}> (geschlossen von {interaction.user.mention})",
        color=discord.Color.orange(),
    )
    embed.set_thumbnail(url=LOGO_URL)

    for i, ant in enumerate(ticket_data.get("antworten", []), start=1):
        embed.add_field(name=f"Frage {i}", value=ant, inline=False)

    embed.set_footer(text=f"Erstellt: {ticket_data['created_at']} | BloodLife PD")
    await log_channel.send(embed=embed)

    del user_tickets[ticket_owner_id]
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
        # Fallback → global sync
        await tree.sync()
        print("🌍 Commands global synchronisiert")

    print(f"🤖 Bot online als {bot.user}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("❌ DISCORD_TOKEN nicht gefunden! Bitte in Render als Environment Variable setzen.")
    bot.run(DISCORD_TOKEN)
