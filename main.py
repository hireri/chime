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

# Database environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "discord_bot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

# Verify required environment variables
if not TOKEN:
    logger.error("Missing TOKEN environment variable. Please set it in .env file.")
    exit(1)

# Log database configuration
logger.info(f"Using database: {DB_NAME} at {DB_HOST}:{DB_PORT}")

if __name__ == "__main__":
    bot = Core()
    bot.run(TOKEN)
