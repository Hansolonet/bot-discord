import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
import os

GUILD_ID = 1195718691254444175  # Remplace par ton ID de serveur
WARNS_FILE = "warns.json"

# Fonctions pour gérer les warns
def load_warns():
    if not os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "w") as f:
            json.dump({}, f)
    with open(WARNS_FILE, "r") as f:
        return json.load(f)

def save_warns(warns):
    with open(WARNS_FILE, "w") as f:
        json.dump(warns, f, indent=4)

# View & Select pour gérer la suppression d'avertissements
class WarnSelect(discord.ui.Select):
    def __init__(self, warns_list):
        options = [
            discord.SelectOption(
                label=f"Sanction n°{i+1} - {warn['date']}",
                description=warn["reason"][:100],
                value=str(i)
            )
            for i, warn in enumerate(warns_list)
        ]
        options.append(discord.SelectOption(label="🗑️ Supprimer TOUT", value="all"))

        super().__init__(
            placeholder="Choisis une sanction à supprimer...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view.process_selection(interaction, self.values[0])

class WarnView(discord.ui.View):
    def __init__(self, member: discord.Member, warns, author: discord.Member):
        super().__init__(timeout=60)
        self.member = member
        self.warns = warns
        self.author = author
        self.add_item(WarnSelect(warns[str(member.id)]))

    async def process_selection(self, interaction: discord.Interaction, selected_value: str):
        if interaction.user != self.author:
            await interaction.followup.send("🚫 Tu ne peux pas utiliser cette interaction.", ephemeral=True)
            return

        user_id = str(self.member.id)
        removed = []

        if selected_value == "all":
            removed = self.warns[user_id]
            del self.warns[user_id]
        else:
            idx = int(selected_value)
            removed.append(self.warns[user_id].pop(idx))
            if not self.warns[user_id]:
                del self.warns[user_id]

        save_warns(self.warns)

        embed = discord.Embed(
            title="✅ Sanction(s) supprimée(s)",
            description=f"{len(removed)} avertissement(s) supprimé(s) pour {self.member.mention}.",
            color=discord.Color.green()
        )
        for warn in removed:
            embed.add_field(name=warn["date"], value=warn["reason"], inline=False)

        await interaction.followup.send(embed=embed)

        # DM à l'utilisateur
        dm_embed = discord.Embed(
            title="📬 Tu as été dé-warn",
            description=f"Sur **{interaction.guild.name}**, les sanctions suivantes ont été retirées :",
            color=discord.Color.blue()
        )
        for warn in removed:
            dm_embed.add_field(name=warn["date"], value=f"🗑️ {warn['reason']}", inline=False)

        try:
            await self.member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- MUTE ---
    @app_commands.command(name="mute", description="Mute un utilisateur")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="Utilisateur à mute", reason="Raison du mute")
    async def mute(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Aucune raison donnée"):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("🚫 Tu n'as pas la permission.", ephemeral=True)
            return

        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if muted_role is None:
            await interaction.response.send_message("Le rôle Muted n'existe pas.", ephemeral=True)
            return

        if muted_role in user.roles:
            await interaction.response.send_message(f"{user.mention} est déjà mute.", ephemeral=True)
            return

        try:
            await user.add_roles(muted_role, reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Je n'ai pas la permission d'ajouter ce rôle.", ephemeral=True)
            return

        # Envoi DM à l'utilisateur
        dm_embed = discord.Embed(
            title="🔇 Vous avez été mute",
            description=f"Vous avez été mute pour la raison : {reason}",
            color=discord.Color.dark_grey()
        )
        try:
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title="🔇 Utilisateur mute",
            description=f"{user.mention} a été mute.\nRaison : {reason}",
            color=discord.Color.dark_grey()
        )
        await interaction.response.send_message(embed=embed)

    # --- UNMUTE ---
    @app_commands.command(name="unmute", description="Unmute un utilisateur")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="Utilisateur à unmute")
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("🚫 Tu n'as pas la permission.", ephemeral=True)
            return

        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if muted_role is None:
            await interaction.response.send_message("Le rôle Muted n'existe pas.", ephemeral=True)
            return

        if muted_role not in user.roles:
            await interaction.response.send_message(f"{user.mention} n'est pas mute.", ephemeral=True)
            return

        try:
            await user.remove_roles(muted_role, reason="Unmute demandé")
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Je n'ai pas la permission d'enlever ce rôle.", ephemeral=True)
            return

        # Envoi du DM pour informer
        dm_embed = discord.Embed(
            title="🔊 Vous avez été démute",
            description=f"Vous avez été démute du serveur **{interaction.guild.name}**.",
            color=discord.Color.green()
        )
        try:
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # Silencieux si impossible d'envoyer le DM

        await interaction.response.send_message(embed=discord.Embed(
            title="🔊 Unmute appliqué",
            description=f"{user.mention} a été unmute.",
            color=discord.Color.green()
        ))

    # --- BAN ---
    @app_commands.command(name="ban", description="Bannit un utilisateur (même externe au serveur)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user_id="ID de l'utilisateur à bannir", reason="Raison du bannissement")
    async def ban(self, interaction: discord.Interaction, user_id: str, reason: str = "Aucune raison donnée"):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("Tu n'as pas la permission de bannir.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.ban(user, reason=reason)

            embed = discord.Embed(
                title=f"🔨 Bannissement - {interaction.guild.name}",
                description=(
                    f"**{user.name}#{user.discriminator}** a été banni.\n\n"
                    f"**Raison :** {reason}"
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text="Fallait réfléchir, au revoir :))")
            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message("❌ Utilisateur introuvable.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Je n'ai pas la permission de bannir cet utilisateur.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID invalide.", ephemeral=True)

    # --- UNBAN ---
    @app_commands.command(name="unban", description="Débannit un utilisateur du serveur")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user_id="ID de l'utilisateur à débannir", reason="Raison du débannissement")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Aucune raison donnée"):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("Tu n'as pas la permission de débannir.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)

            # Essayer de lui envoyer un DM
            try:
                embed_dm = discord.Embed(
                    title="🔓 Tu as été débanni",
                    description=f"Tu as été débanni du serveur **{interaction.guild.name}**.\nRaison : {reason}",
                    color=discord.Color.green()
                )
                await user.send(embed=embed_dm)
            except discord.Forbidden:
                pass

            embed = discord.Embed(
                title=f"Débannissement - {interaction.guild.name}",
                description=f"**{user.mention} a été débanni.**\n\n**Raison :** {reason}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="Fallait réfléchir, au revoir :))")

            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message("Utilisateur non trouvé ou pas banni.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Je n'ai pas la permission de débannir cet utilisateur.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("ID invalide. Assure-toi d’entrer un identifiant numérique.", ephemeral=True)

    # --- WARN ---
    @app_commands.command(name="warn", description="Avertir un utilisateur avec une raison.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="L'utilisateur à avertir", reason="La raison de l'avertissement")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("🚫 Tu n'as pas la permission.", ephemeral=True)
            return

        warns = load_warns()
        user_id = str(user.id)

        warns.setdefault(user_id, []).append({
            "reason": reason,
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        })
        save_warns(warns)

        count = len(warns[user_id])
        footer = f"Avertissement n°{count}"

        embed_dm = discord.Embed(
            title="⚠️ Tu as reçu un avertissement",
            description=f"Serveur : **{interaction.guild.name}**\nRaison : {reason}",
            color=0xFFB34F
        )
        embed_dm.set_footer(text=footer)

        try:
            await user.send(embed=embed_dm)
            dm_status = f"✅ {user.mention} a été averti par DM."
        except discord.Forbidden:
            dm_status = f"❌ Impossible d’envoyer un DM à {user.mention}."

        embed = discord.Embed(description=dm_status, color=0xFFB34F)
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # --- UNWARN ---
    @app_commands.command(name="unwarn", description="Supprime un avertissement d’un utilisateur")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(member="Le membre à dé-warn")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("🚫 Tu n’as pas la permission.", ephemeral=True)
            return

        warns = load_warns()
        user_id = str(member.id)

        if user_id not in warns or not warns[user_id]:
            await interaction.response.send_message("❌ Ce membre n’a aucun avertissement.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🧹 Gestion des avertissements",
            description="Choisis un avertissement spécifique à supprimer ou supprime tout.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Expire dans 1 minute")

        view = WarnView(member, warns, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))