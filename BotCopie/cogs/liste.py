import discord
from discord.ext import commands
from discord import app_commands
import json
import os

WARNS_FILE = "warns.json"
GUILD_ID = 1195718691254444175  # Ton ID de serveur ici

def load_warns():
    if not os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "w") as f:
            json.dump({}, f)
    with open(WARNS_FILE, "r") as f:
        return json.load(f)

class ListSanctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Cog ListeSanctions initialisé.")  # Cette ligne sera imprimée si le cog est bien chargé

    @app_commands.guilds(discord.Object(id=GUILD_ID))  # 👈 Enregistre la commande pour ton serveur
    @app_commands.command(name="liste", description="Affiche les sanctions d’un utilisateur.")
    @app_commands.describe(member="Le membre concerné")
    async def list_sanctions(self, interaction: discord.Interaction, member: discord.Member):
        print("Commande /liste a été appelée.")  # Vérifie si cette ligne s'affiche

        warns = load_warns()
        user_id = str(member.id)
        
        sanctions = warns.get(user_id, [])
        print(f"Sanctions trouvées pour {user_id}: {sanctions}")  # Vérifie si les sanctions sont chargées correctement

        embed = discord.Embed(
            title=f"Sanctions de {member.display_name}",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if not sanctions:
            embed.description = "✅ Aucun avertissement trouvé."
        else:
            for idx, warn in enumerate(sanctions, 1):
                embed.add_field(
                    name=f"Avertissement {idx}",
                    value=f"📅 {warn['date']} — ✏️ {warn['reason']}",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    print("Chargement du cog ListeSanctions.")  # Vérifie si le cog est bien chargé
    await bot.add_cog(ListSanctions(bot))