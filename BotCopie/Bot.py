import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1195718691254444175  # Remplace par l'ID de ton serveur

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True  # ← Optionnel mais utile si tu veux gérer les messages
intents.members = True

# Création du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Événement appelé quand le bot est prêt
@bot.event
async def on_ready():
    print(f"🤖 {bot.user} est connecté et prêt.")

    try:
        # Synchroniser les commandes pour un serveur spécifique (développement local plus rapide)
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} commande(s) slash synchronisée(s) pour le serveur {GUILD_ID}.")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes slash : {e}")

# Charger dynamiquement les extensions (cogs)
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Chargé : {filename}")
            except Exception as e:
                print(f"❌ Erreur de chargement {filename}: {e}")

# Fonction principale
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# Exécution du bot avec gestion propre de l'arrêt
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("🛑 Bot arrêté manuellement.")