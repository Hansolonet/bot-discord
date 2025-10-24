import discord
from discord import app_commands
from discord.ext import commands
import json, os, time

ID_SERVEUR = 1195718691254444175
DOSSIER_BASE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_BOUTIQUE = os.path.join(DOSSIER_BASE, "shop.json")
CHEMIN_INVENTAIRE = os.path.join(DOSSIER_BASE, "inventaire.json")
CHEMIN_ARGENT = os.path.join(DOSSIER_BASE, "money.json")

# ---------------------- utilitaires JSON ---------------------- #
def charger_json(chemin, default=None):
    if default is None:
        default = []
    if os.path.exists(chemin):
        try:
            with open(chemin, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default
    return default

def sauvegarder_json(chemin, donnees):
    with open(chemin, "w") as f:
        json.dump(donnees, f, indent=4)

# ---------------------- utilitaire boutique ---------------------- #
def objet_expiré(objet):
    return (
        objet.get("timestamp") is not None
        and objet.get("duration") is not None
        and time.time() > objet["timestamp"] + objet["duration"] * 60
    )

# ---------------------- variable globale ---------------------- #
articles_boutique: list[dict] = charger_json(CHEMIN_BOUTIQUE)

# ============================================================== #
#                      COG BOUTIQUE                              #
# ============================================================== #
class Boutique(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ajout_objet", description="Ajoute un objet à la boutique")
    @app_commands.guilds(discord.Object(id=ID_SERVEUR))
    async def ajouter_objet(
        self,
        interaction: discord.Interaction,
        nom: str,
        prix: int,
        description: str,
        limitation: int | None = None,
        duree_minutes: int | None = None,
        echangeable: bool = True,  # Ajout du paramètre échangeable
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Permission refusée", ephemeral=True)
            return

        objet = {
            "nom": nom,
            "prix": prix,
            "description": description,
            "limitation": limitation,
            "timestamp": time.time() if duree_minutes else None,
            "duration": duree_minutes,
            "echangeable": echangeable,  # Enregistrement de la propriété échangeable
        }
        articles_boutique.append(objet)
        sauvegarder_json(CHEMIN_BOUTIQUE, articles_boutique)

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Objet ajouté",
                description=f"{nom} — {prix}💰",
                color=discord.Color.green(),
            )
        )

    @app_commands.command(name="boutique", description="Affiche la boutique")
    @app_commands.guilds(discord.Object(id=ID_SERVEUR))
    async def afficher_boutique(self, interaction: discord.Interaction):
        global articles_boutique
        articles_boutique = charger_json(CHEMIN_BOUTIQUE)

        articles_valides = [art for art in articles_boutique if not objet_expiré(art)]
        if not articles_valides:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ La boutique est vide pour le moment.",
                    color=discord.Color.red(),
                )
            )
            return

        embed = discord.Embed(
            title="🛍️ Boutique",
            description="Voici les objets disponibles :",
            color=discord.Color.from_rgb(216, 191, 216),
        )
        vue = discord.ui.View(timeout=None)

        def creer_callback_achat(index: int):
            async def callback(inter: discord.Interaction):
                try:
                    utilisateur = str(inter.user.id)
                    argent = charger_json(CHEMIN_ARGENT)
                    inventaire = charger_json(CHEMIN_INVENTAIRE)
                    prix = articles_valides[index]["prix"]
                    nom_item = articles_valides[index]["nom"]

                    if utilisateur not in argent or not isinstance(argent[utilisateur], dict):
                        argent[utilisateur] = {"coins": 0, "last_claim": None}

                    if argent[utilisateur]["coins"] < prix:
                        await inter.response.send_message(
                            embed=discord.Embed(
                                title="❌ Achat refusé",
                                description="Tu n'as pas assez d'argent !",
                                color=discord.Color.red(),
                            )
                        )
                        return

                    argent[utilisateur]["coins"] -= prix
                    sauvegarder_json(CHEMIN_ARGENT, argent)

                    inventaire.setdefault(utilisateur, []).append(nom_item)
                    sauvegarder_json(CHEMIN_INVENTAIRE, inventaire)

                    await inter.response.send_message(
                        embed=discord.Embed(
                            title="✅ Achat réussi",
                            description=f"Tu as acheté **{nom_item}** pour {prix}💰 !",
                            color=discord.Color.green(),
                        )
                    )
                except Exception as e:
                    print("ERREUR BOUTON :", e)
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            "⚠️ Une erreur est survenue, consulte la console.", ephemeral=True
                        )

            return callback

        for index, article in enumerate(articles_valides):
            limite = f" (Limité à {article['limitation']})" if article["limitation"] else ""
            echange_text = "\n*`Il n'est pas échangeable`*" if not article.get("echangeable", True) else ""

            embed.add_field(
                name=f"{index + 1}. {article['nom']} - {article['prix']}💰",
                value=f"{article['description']}{limite}{echange_text}",
                inline=False,
            )
            bouton = discord.ui.Button(
                label=f"Acheter {article['nom']}", style=discord.ButtonStyle.secondary
            )
            bouton.callback = creer_callback_achat(index)
            vue.add_item(bouton)

        await interaction.response.send_message(embed=embed, view=vue)

    # ---------------------- commandes publiques ---------------------- #

    @app_commands.command(name="inventaire", description="Voir l'inventaire d'un utilisateur")
    @app_commands.guilds(discord.Object(id=ID_SERVEUR))
    async def voir_inventaire(self, interaction: discord.Interaction, utilisateur: discord.Member):
        inv = charger_json(CHEMIN_INVENTAIRE).get(str(utilisateur.id), [])
        desc = ""
        for obj in inv:
            details = next((art for art in articles_boutique if art["nom"] == obj), None)
            non_echange = "\n  *`Il n'est pas échangeable`*" if details and not details.get("echangeable", True) else ""
            desc += f"• {obj}{non_echange}\n"
        desc = desc or "Aucun objet."
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"📁 Inventaire de {utilisateur.display_name}",
                description=desc,
                color=discord.Color.blue()
            )
        )

    # ---------------------- commandes admin ---------------------- #

    @app_commands.command(name="retirer_objet", description="(Admin) Retirer un objet d'un utilisateur")
    @app_commands.guilds(discord.Object(id=ID_SERVEUR))
    async def retirer_objet(self, interaction: discord.Interaction,
                            utilisateur: discord.Member, objet: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Permission refusée", ephemeral=True)
            return
        inv = charger_json(CHEMIN_INVENTAIRE)
        lst = inv.get(str(utilisateur.id), [])
        if objet not in lst:
            await interaction.response.send_message("❌ Cet utilisateur ne possède pas cet objet.")
            return
        lst.remove(objet)
        inv[str(utilisateur.id)] = lst
        sauvegarder_json(CHEMIN_INVENTAIRE, inv)
        await interaction.response.send_message(f"🗑️ **{objet}** retiré de son inventaire.")

    @app_commands.command(name="ajout_argent", description="(Admin) Ajouter de l'argent à un utilisateur")
    @app_commands.guilds(discord.Object(id=ID_SERVEUR))
    async def ajouter_argent(self, interaction: discord.Interaction,
                             utilisateur: discord.Member, montant: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Permission refusée", ephemeral=True)
            return
        user_id = str(utilisateur.id)
        argent = charger_json(CHEMIN_ARGENT)
        if user_id not in argent:
            argent[user_id] = {"coins": 0, "last_claim": None}
        argent[user_id]["coins"] += montant
        sauvegarder_json(CHEMIN_ARGENT, argent)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Argent ajouté",
                description=f"{montant}💰 ont été ajoutés à {utilisateur.display_name}.",
                color=discord.Color.green(),
            )
        )

    # ---------------------- commandes echange ---------------------- #

    @app_commands.command(name="echange", description="Proposer un échange d'objet avec un autre utilisateur")
    @app_commands.guilds(discord.Object(id=ID_SERVEUR))
    async def echange(self, interaction: discord.Interaction, utilisateur: discord.Member,
                      ton_objet: str, son_objet: str):
        inventaire = charger_json(CHEMIN_INVENTAIRE)
        user_id = str(interaction.user.id)
        target_id = str(utilisateur.id)

        if ton_objet not in inventaire.get(user_id, []):
            await interaction.response.send_message("❌ Tu ne possèdes pas cet objet.", ephemeral=True)
            return

        if son_objet not in inventaire.get(target_id, []):
            await interaction.response.send_message("❌ Cette personne ne possède pas cet objet.", ephemeral=True)
            return

        # Vérification échangeable
        objets_data = charger_json(CHEMIN_BOUTIQUE)
        donnee_ton_objet = next((x for x in objets_data if x["nom"] == ton_objet), {})
        donnee_son_objet = next((x for x in objets_data if x["nom"] == son_objet), {})

        if not donnee_ton_objet.get("echangeable", True) or not donnee_son_objet.get("echangeable", True):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Échange refusé",
                    description="Les permissions de l'objet vous empêchent de le mettre à l'échange.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return

        class BoutonAccepter(discord.ui.Button):
            def __init__(self):
                super().__init__(label="✅ Accepter", style=discord.ButtonStyle.success)

            async def callback(self, inter: discord.Interaction):
                if inter.user.id != utilisateur.id:
                    await inter.response.send_message("❌ Tu n'es pas concerné par cet échange.", ephemeral=True)
                    return

                inventaire_actualise = charger_json(CHEMIN_INVENTAIRE)
                if (ton_objet not in inventaire_actualise.get(user_id, []) or
                        son_objet not in inventaire_actualise.get(target_id, [])):
                    await inter.response.edit_message(
                        content="⚠️ Échange annulé : un des objets n'est plus dans l'inventaire.",
                        embed=None,
                        view=None
                    )
                    return

                # Échange des objets
                inventaire_actualise[user_id].remove(ton_objet)
                inventaire_actualise[target_id].append(ton_objet)

                inventaire_actualise[target_id].remove(son_objet)
                inventaire_actualise[user_id].append(son_objet)

                sauvegarder_json(CHEMIN_INVENTAIRE, inventaire_actualise)

                await inter.response.edit_message(
                    content="🔁 Échange complété avec succès !",
                    embed=None,
                    view=None
                )

        class BoutonRefus(discord.ui.Button):
            def __init__(self):
                super().__init__(label="❌ Refuser", style=discord.ButtonStyle.danger)

            async def callback(self, inter: discord.Interaction):
                if inter.user.id != utilisateur.id:
                    await inter.response.send_message("❌ Tu n'es pas concerné par cet échange.", ephemeral=True)
                    return

                inventaire_actualise = charger_json(CHEMIN_INVENTAIRE)
                if (ton_objet not in inventaire_actualise.get(user_id, []) or
                        son_objet not in inventaire_actualise.get(target_id, [])):
                    await inter.response.edit_message(
                        content="⚠️ Échange annulé : un des objets n'est plus dans l'inventaire.",
                        embed=None,
                        view=None
                    )
                    return

                await inter.response.edit_message(
                    content="❌ Échange refusé.",
                    embed=None,
                    view=None
                )

        class VueEchange(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                self.add_item(BoutonAccepter())
                self.add_item(BoutonRefus())

        embed = discord.Embed(
            title="🔁 Demande d'échange",
            description=f"{interaction.user.mention} te propose un échange !",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Proposition",
            value=f"**{interaction.user.display_name}** te propose :\n"
                  f"🎁 {ton_objet}  ➡️  {son_objet} 🎁",
            inline=False
        )

        await interaction.response.send_message(
            content=f"{utilisateur.mention}, tu as reçu une demande d'échange !",
            embed=embed,
            view=VueEchange()
        )


async def setup(bot):
    await bot.add_cog(Boutique(bot))