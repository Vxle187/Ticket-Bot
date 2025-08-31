import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Kategorien
categories = {
    "bewerbungen": 1410111339359113318,
    "beschwerden": 1410111382237483088,
    "leitungsAnliegen": 1410111463783268382
}

# ID vom Channel, wo die Ticket-Nachricht rein soll
TICKET_CHANNEL_ID = 1396969114442006539  # <- HIER deine Channel-ID eintragen


class TicketView(discord.ui.View):
    @discord.ui.select(
        placeholder="Bitte wähle einen Grund",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Bewerbungen", description="Erstelle ein Ticket für Bewerbungen", value="bewerbungen"),
            discord.SelectOption(label="Beschwerden", description="Erstelle ein Ticket für Beschwerden", value="beschwerden"),
            discord.SelectOption(label="Leitungs Anliegen", description="Erstelle ein Ticket für Anliegen an die Leitung", value="leitungsAnliegen"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        reason = select.values[0]
        category_id = categories[reason]
        guild = interaction.guild
        category = guild.get_channel(category_id)

        # Channel erstellen
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(f"{interaction.user.mention}, dein Ticket wurde erstellt! 🎫")
        await interaction.response.send_message(f"✅ Ticket erstellt: {channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Ticket-System",
            description="Willkommen im Ticketsystem! Bitte wähle einen Grund aus, um dein Ticket zu erstellen.\n\n**Wichtig:** Bitte beschreibe dein Anliegen so genau wie möglich.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed, view=TicketView())
    else:
        print("❌ Ticket-Channel nicht gefunden. Bitte überprüfe die Channel-ID.")


bot.run("DEIN_BOT_TOKEN")
