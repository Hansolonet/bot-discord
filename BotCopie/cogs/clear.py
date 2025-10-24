import discord
from discord.ext import commands
from discord import app_commands

GUILD_ID = 1195718691254444175

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Supprimer des messages.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        member="Utilisateur dont les messages seront supprimés (optionnel)",
        number="Nombre de messages à supprimer (optionnel)",
        channel="Salon où les messages seront supprimés (optionnel)"
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None,
        number: int = 20,
        channel: discord.TextChannel = None
    ):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "Tu n'as pas la permission de gérer les messages.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)  # ✅ Empêche Discord de considérer l'app comme plantée

        if number > 100:
            number = 100

        channel = channel or interaction.channel

        # ✅ Remplacement de flatten()
        messages = [msg async for msg in channel.history(limit=number)]

        if member:
            messages = [msg for msg in messages if msg.author == member]

        deleted_count = 0
        for msg in messages:
            try:
                await msg.delete()
                deleted_count += 1
            except discord.Forbidden:
                continue

        if deleted_count == 0:
            await interaction.followup.send("Aucun message trouvé à supprimer.")
        else:
            await interaction.followup.send(f"{deleted_count} message(s) supprimé(s).")

async def setup(bot):
    print("Cog Clear chargé.")
    await bot.add_cog(Clear(bot))