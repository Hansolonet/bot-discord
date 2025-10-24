import discord
from discord.ext import commands
from discord import app_commands, File
import json
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
import os

GUILD_ID = 1195718691254444175
XP_FILE = os.path.join(os.path.dirname(__file__), "level.json")

def xp_needed_for_level(level):
    return int(100 * (1.5 ** level))

def calculate_level_from_xp(xp):
    level = 0
    while xp >= xp_needed_for_level(level):
        xp -= xp_needed_for_level(level)
        level += 1
    return level

async def get_avatar_bytes(user):
    avatar_url = user.display_avatar.replace(size=64).url
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            return await response.read()

async def create_leaderboard_page(entries, guild, page_num, per_page=10):
    width, row_height = 600, 70
    height = 50 + row_height * len(entries)
    img = Image.new("RGB", (width, height), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 22)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((20, 10), f"\U0001F3C6 Classement XP — Page {page_num + 1}", font=font, fill="white")

    for i, (user_id, xp, level) in enumerate(entries):
        y = 50 + i * row_height
        user = guild.get_member(user_id)
        name = user.display_name if user else f"ID: {user_id}"

        avatar_bytes = await get_avatar_bytes(user) if user else None
        if avatar_bytes:
            avatar = Image.open(io.BytesIO(avatar_bytes)).resize((50, 50)).convert("RGB")
            img.paste(avatar, (20, y))

        draw.text((80, y), f"#{page_num * per_page + i + 1} {name}", font=font, fill="white")
        draw.text((350, y), f"Niveau {level} - {xp} XP", font=font_small, fill="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

class LeaderboardView(discord.ui.View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=60)
        self.pages = pages
        self.index = 0
        self.author_id = author_id
        self.message = None

        self.prev_btn = discord.ui.Button(label="⏮️ Précédent", style=discord.ButtonStyle.secondary)
        self.next_btn = discord.ui.Button(label="⏭️ Suivant", style=discord.ButtonStyle.secondary)
        self.prev_btn.callback = self.prev_page
        self.next_btn.callback = self.next_page
        self.add_item(self.prev_btn)
        self.add_item(self.next_btn)

    async def prev_page(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            return
        self.index = (self.index - 1) % len(self.pages)
        await self.update(interaction)

    async def next_page(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            return
        self.index = (self.index + 1) % len(self.pages)
        await self.update(interaction)

    async def update(self, interaction):
        buffer = self.pages[self.index]
        file = File(fp=buffer, filename="leaderboard.png")
        await interaction.response.edit_message(attachments=[file], view=self)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Classement des membres par XP")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            with open(XP_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            await interaction.followup.send("❌ Erreur de lecture de level.json.")
            return

        users_data = data.get("guilds", {}).get(str(interaction.guild.id), {}).get("users", {})

        if not users_data:
            await interaction.followup.send("Aucun utilisateur avec de l'XP.")
            return

        leaderboard = []
        for uid, info in users_data.items():
            xp = info.get("xp", 0)
            level = calculate_level_from_xp(xp)
            leaderboard.append((int(uid), xp, level))

        leaderboard.sort(key=lambda x: x[1], reverse=True)
        per_page = 10
        pages_data = [leaderboard[i:i + per_page] for i in range(0, len(leaderboard), per_page)]

        pages = []
        for i, page in enumerate(pages_data):
            img_buffer = await create_leaderboard_page(page, interaction.guild, i, per_page)
            pages.append(img_buffer)

        view = LeaderboardView(pages, interaction.user.id)
        file = File(fp=pages[0], filename="leaderboard.png")
        view.message = await interaction.followup.send(file=file, view=view)

async def setup(bot):
    print("✅ Chargé : leaderboard.py")
    await bot.add_cog(Leaderboard(bot))