import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta

GUILD_ID = 1195718691254444175
MONEY_FILE = os.path.join(os.path.dirname(__file__), "money.json")

def load_money():
    if os.path.exists(MONEY_FILE):
        with open(MONEY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_money(data):
    with open(MONEY_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Salaire(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="salaire", description="Réclame ton salaire quotidien de 50 coins.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def salaire(self, interaction: discord.Interaction):
        await interaction.response.defer()

        user_id = str(interaction.user.id)
        data = load_money()
        user_data = data.get(user_id, {"coins": 0, "last_claim": None})

        now = datetime.utcnow()
        last_claim = datetime.fromisoformat(user_data["last_claim"]) if user_data["last_claim"] else None

        if last_claim and now - last_claim < timedelta(days=1):
            next_time = last_claim + timedelta(days=1)
            remaining = next_time - now
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes = remainder // 60

            embed_wait = discord.Embed(
                title="⏳ Salaire déjà réclamé",
                description=f"Tu as déjà reçu ton salaire aujourd'hui.\nReviens dans **{hours}h {minutes}m**.",
                color=discord.Color.orange()
            )
            embed_wait.set_footer(text="Reviens demain pour de nouveaux coins !")
            await interaction.followup.send(embed=embed_wait)
            return

        user_data["coins"] += 50
        user_data["last_claim"] = now.isoformat()
        data[user_id] = user_data
        save_money(data)

        embed = discord.Embed(
            title="💸 Salaire reçu",
            description=f"Tu viens de recevoir **50 coins** !\nTu as maintenant **{user_data['coins']} coins**.",
         color=discord.Color.from_rgb(144, 238, 144)  # vert pastel
        )
        embed.set_footer(text="Reviens demain pour un autre salaire 🕒")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Salaire(bot))