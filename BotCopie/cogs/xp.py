import json
import os
import time
import discord
from discord.ext import commands, tasks

XP_FILE = os.path.join(os.path.dirname(__file__), "level.json")

def load_xp_data():
    if not os.path.exists(XP_FILE):
        with open(XP_FILE, "w") as f:
            json.dump({"guilds": {}}, f)
    with open(XP_FILE, "r") as f:
        return json.load(f)

def save_xp_data(data):
    with open(XP_FILE, "w") as f:
        json.dump(data, f, indent=4)

def clean_old_level_fields():
    data = load_xp_data()
    for guild in data.get("guilds", {}).values():
        for user_data in guild.get("users", {}).values():
            user_data.pop("level", None)
    save_xp_data(data)
    print("✅ Champs 'level' supprimés du fichier level.json")

def xp_needed_for_level(level):
    return int(100 * (1.5 ** level))

def calculate_level_from_xp(xp):
    level = 0
    while xp >= xp_needed_for_level(level):
        xp -= xp_needed_for_level(level)
        level += 1
    return level

def add_xp(guild_id: str, user_id: str, message_length: int, xp_gain: int = 0):
    data = load_xp_data()

    if "guilds" not in data:
        data["guilds"] = {}

    if guild_id not in data["guilds"]:
        data["guilds"][guild_id] = {}

    if "users" not in data["guilds"][guild_id]:
        data["guilds"][guild_id]["users"] = {}

    if user_id not in data["guilds"][guild_id]["users"]:
        data["guilds"][guild_id]["users"][user_id] = {"xp": 0}

    # ➕ Gagner de l'XP selon la taille du message
    if message_length <= 1000:
        xp_gain_message = 10
    elif 1000 < message_length <= 1799:
        xp_gain_message = 13
    elif 1800 <= message_length <= 2000:
        xp_gain_message = 18
    else:
        xp_gain_message = 0

    user_data = data["guilds"][guild_id]["users"][user_id]
    total_gain = xp_gain_message + xp_gain
    user_data["xp"] += total_gain

    total_xp = user_data["xp"]
    new_level = calculate_level_from_xp(total_xp)

    save_xp_data(data)

    print(f"[XP] {user_id} : +{total_gain} XP, total = {user_data['xp']} → niveau {new_level}")

def add_voice_xp(guild_id: str, user_id: str, time_spent: int):
    xp_gain = int(time_spent / 60 / 7) * 5  # 5 XP toutes les 7 minutes
    if xp_gain > 0:
        print(f"[VOICE XP] {user_id} gagne {xp_gain} XP pour {int(time_spent)} secondes passées en vocal.")
    add_xp(guild_id, user_id, 0, xp_gain)

class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_times = {}  # {guild_id: {user_id: timestamp}}
        clean_old_level_fields()
        self.xp_gain_task.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        add_xp(str(message.guild.id), str(message.author.id), len(message.content))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        if after.channel and not before.channel:
            if guild_id not in self.voice_times:
                self.voice_times[guild_id] = {}
            self.voice_times[guild_id][user_id] = time.time()

        elif not after.channel and before.channel:
            if guild_id in self.voice_times and user_id in self.voice_times[guild_id]:
                time_spent = time.time() - self.voice_times[guild_id][user_id]
                add_voice_xp(guild_id, user_id, time_spent)
                del self.voice_times[guild_id][user_id]

    @tasks.loop(seconds=60)
    async def xp_gain_task(self):
        now = time.time()
        for guild_id, users in self.voice_times.items():
            for user_id, join_time in users.items():
                time_spent = now - join_time
                add_voice_xp(guild_id, user_id, time_spent)
                self.voice_times[guild_id][user_id] = now  # Reset timer après gain d'XP

async def setup(bot):
    await bot.add_cog(XP(bot))