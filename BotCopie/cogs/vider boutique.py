import discord
from discord.ext import commands
from discord import app_commands
import json, os

GUILD_ID = 1195718691254444175
DOSSIER_BASE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_BOUTIQUE = os.path.join(DOSSIER_BASE, "shop.json")
articles_boutique = []  # variable globale

# ---------------------- utilitaires JSON ---------------------- #
def sauvegarder_json(chemin, donnees):
    tmp_chemin = chemin + ".tmp"
    with open(tmp_chemin, "w") as f:
        json.dump(donnees, f, indent=4)
    os.replace(tmp_chemin, chemin)

def charger_json(chemin):
    if os.path.exists(chemin):
        try:
            data = json.load(open(chemin, "r"))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []

# Charger la boutique au démarrage
articles_boutique = charger_json(CHEMIN_BOUTIQUE)

# ---------------------- Cog ---------------------- #
class ViderBoutique(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="vider_boutique",
        description="Supprime des objets dans le shop.json."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def vider_boutique(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Tu n'as pas la permission d'administrer le serveur.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        global articles_boutique
        # Recharger la boutique à chaque utilisation
        articles_boutique = charger_json(CHEMIN_BOUTIQUE)

        if not articles_boutique:
            embed = discord.Embed(
                title="❌ La boutique est déjà vide",
                description="Aucun objet à supprimer.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # Création du dropdown
        options = [discord.SelectOption(label=obj.get("nom", "Nom inconnu")) for obj in articles_boutique]
        options.insert(0, discord.SelectOption(label="Tout supprimer", description="Supprime tous les objets", value="__ALL__"))

        # ----- Définir la vue et le select ----- #
        vue_supprimer = discord.ui.View(timeout=None)

        class SelectSupprimer(discord.ui.Select):
            def __init__(self):
                super().__init__(
                    placeholder="Choisis les objets à supprimer...",
                    min_values=1,
                    max_values=len(options),
                    options=options
                )

            async def callback(self, inter: discord.Interaction):
                global articles_boutique
                articles_boutique = charger_json(CHEMIN_BOUTIQUE)

                if "__ALL__" in self.values:
                    articles_boutique = []
                    sauvegarder_json(CHEMIN_BOUTIQUE, articles_boutique)
                    embed = discord.Embed(
                        title="✅ Tous les objets ont été supprimés",
                        description="La boutique est maintenant vide.",
                        color=discord.Color.green()
                    )
                    await inter.response.edit_message(embed=embed, view=vue_supprimer)
                    return

                # Normaliser pour éviter problèmes de casse / espaces
                selected = [v.strip().lower() for v in self.values]
                supprimés = [obj["nom"] for obj in articles_boutique if obj.get("nom", "").strip().lower() in selected]

                articles_boutique = [obj for obj in articles_boutique if obj.get("nom", "").strip().lower() not in selected]
                sauvegarder_json(CHEMIN_BOUTIQUE, articles_boutique)

                # Envoyer embed final
                embed = discord.Embed(
                    title="✅ Objets supprimés",
                    description="\n".join(f"• {nom}" for nom in supprimés),
                    color=discord.Color.green()
                )
                await inter.response.edit_message(embed=embed, view=vue_supprimer)

        vue_supprimer.add_item(SelectSupprimer())

        await interaction.followup.send("Sélectionne les objets à supprimer :", view=vue_supprimer)

async def setup(bot):
    print("Cog ViderBoutique chargé.")
    await bot.add_cog(ViderBoutique(bot))