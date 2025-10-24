import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
import io
from PIL import Image, ImageDraw, ImageFont

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

def get_user_data(guild_id, user_id):
    if not os.path.exists(XP_FILE):
        return {"xp": 0}

    with open(XP_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("❌ level.json mal formé.")
            return {"xp": 0}

    return data.get("guilds", {}).get(str(guild_id), {}).get("users", {}).get(str(user_id), {"xp": 0})

async def get_avatar_bytes(user):
    avatar_url = user.display_avatar.replace(size=128).url
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            return await response.read()

def xp_into_current_level(total_xp, level):
    xp_in_level = total_xp
    for i in range(level):
        xp_in_level -= xp_needed_for_level(i)
    return max(0, xp_in_level)

def create_rank_image(user, avatar_bytes, xp, level):
    current_xp = xp_into_current_level(xp, level)
    xp_required = xp_needed_for_level(level)
    progress = min(current_xp / xp_required, 1.0)
    bar_width = int(330 * progress)

    width, height = 481, 150
    try:
        background_image = Image.open("rank.png").resize((width, height))
        img = background_image.convert("RGB")
    except Exception as e:
        raise FileNotFoundError(f"Erreur image de fond : {e}")

    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([130, 80, 460, 110], fill="#FFFFE0", radius=10)
    draw.rounded_rectangle([130, 80, 130 + bar_width, 110], fill=(255, 140, 0), radius=10)

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()

    xp_text = f"{current_xp} / {xp_required} XP"
    draw.text((460 - draw.textlength(xp_text, font=font), 60), xp_text, fill="white", font=font)
    draw.text((130, 40), f"Niveau {level}", fill="white", font=font)

    avatar = Image.open(io.BytesIO(avatar_bytes)).resize((100, 100)).convert("RGB")
    img.paste(avatar, (15, 25))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def create_levelup_image(user, avatar_bytes, new_level):
    width, height = 481, 150
    try:
        background_image = Image.open("rank.png").resize((width, height))
        img = background_image.convert("RGB")
    except Exception as e:
        raise FileNotFoundError(f"Erreur image de fond : {e}")

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    message = f"Bravo {user.name}, tu es niveau {new_level} !"
    text_width = draw.textlength(message, font=font)
    draw.text(((width - text_width) // 2, 20), message, fill="white", font=font)

    avatar = Image.open(io.BytesIO(avatar_bytes)).resize((100, 100)).convert("RGB")
    img.paste(avatar, (15, 25))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rank", description="Affiche ton niveau.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user = interaction.user
        data = get_user_data(interaction.guild.id, interaction.user.id)
        xp = data.get("xp", 0)
        level = calculate_level_from_xp(xp)

        try:
            avatar_bytes = await get_avatar_bytes(user)
            img_buffer = create_rank_image(user, avatar_bytes, xp, level)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur image : {e}")
            return

        await interaction.followup.send(file=discord.File(fp=img_buffer, filename="rank.png"))

    @app_commands.command(name="enlève_xp", description="Retirer de l'XP à un utilisateur.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def remove_xp(self, interaction: discord.Interaction, user: discord.User, xp_to_remove: int):
        await interaction.response.defer()

        data = get_user_data(interaction.guild.id, user.id)
        current_xp = data.get("xp", 0)
        current_level = calculate_level_from_xp(current_xp)

        if xp_to_remove >= current_xp:
            xp_to_remove = current_xp

        new_xp = current_xp - xp_to_remove
        new_level = calculate_level_from_xp(new_xp)
        data["xp"] = new_xp

        # Sauvegarde
        if not os.path.exists(XP_FILE):
            file_data = {"guilds": {}}
        else:
            with open(XP_FILE, "r") as f:
                try:
                    file_data = json.load(f)
                except json.JSONDecodeError:
                    file_data = {"guilds": {}}

        guild_data = file_data.get("guilds", {}).get(str(interaction.guild.id), {"users": {}})
        guild_data["users"][str(user.id)] = data
        file_data["guilds"][str(interaction.guild.id)] = guild_data

        with open(XP_FILE, "w") as f:
            json.dump(file_data, f, indent=4)

        levels_lost = current_level - new_level
        embed = discord.Embed(
            title="XP Retiré",
            description=f"Tu as retiré **{xp_to_remove} XP** à {user.mention}.",
            color=discord.Color.from_rgb(255, 165, 0)
        )
        embed.add_field(name="Niveaux enlevés", value=str(levels_lost), inline=False)
        embed.add_field(name="XP restant", value=f"{new_xp} ({new_level} niveau{'s' if new_level > 1 else ''})", inline=False)
        embed.add_field(name="Pseudo", value=user.name, inline=False)
        embed.add_field(name="ID de l'utilisateur", value=user.id, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ajout_xp", description="Ajouter de l'XP à un utilisateur.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def add_xp(self, interaction: discord.Interaction, user: discord.User, xp_to_add: int):
        await interaction.response.defer()

        data = get_user_data(interaction.guild.id, user.id)
        current_xp = data.get("xp", 0)
        current_level = calculate_level_from_xp(current_xp)

        new_xp = current_xp + xp_to_add
        new_level = calculate_level_from_xp(new_xp)
        levels_gained = new_level - current_level
        data["xp"] = new_xp

        # Sauvegarde
        if not os.path.exists(XP_FILE):
            file_data = {"guilds": {}}
        else:
            with open(XP_FILE, "r") as f:
                try:
                    file_data = json.load(f)
                except json.JSONDecodeError:
                    file_data = {"guilds": {}}

        guild_data = file_data.get("guilds", {}).get(str(interaction.guild.id), {"users": {}})
        guild_data["users"][str(user.id)] = data
        file_data["guilds"][str(interaction.guild.id)] = guild_data

        with open(XP_FILE, "w") as f:
            json.dump(file_data, f, indent=4)

        embed = discord.Embed(
            title="XP Ajouté",
            description=f"Tu as ajouté **{xp_to_add} XP** à {user.mention}.",
            color=discord.Color.from_rgb(255, 165, 0)
        )
        embed.add_field(name="Niveaux gagnés", value=str(levels_gained), inline=False)
        embed.add_field(name="XP total", value=f"{new_xp} ({new_level} niveau{'s' if new_level > 1 else ''})", inline=False)
        embed.add_field(name="Pseudo", value=user.name, inline=False)
        embed.add_field(name="ID de l'utilisateur", value=user.id, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)

        await interaction.followup.send(embed=embed)

        # 🎉 Génère une image si le joueur a monté de niveau
        if levels_gained > 0:
            try:
                avatar_bytes = await get_avatar_bytes(user)
                levelup_img = create_levelup_image(user, avatar_bytes, new_level)
                await interaction.followup.send(file=discord.File(fp=levelup_img, filename="levelup.png"))
            except Exception as e:
                await interaction.followup.send(f"❌ Erreur image de level up : {e}")

async def setup(bot):
    print("✅ Chargé : rank.py")
    await bot.add_cog(Rank(bot))