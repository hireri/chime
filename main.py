import discord_ios
import os
import logging
from dotenv import load_dotenv

from core.bot import Core

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("discord.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")

if __name__ == "__main__":
    bot = Core()
    bot.run(TOKEN)
