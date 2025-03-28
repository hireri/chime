import asyncio
import asyncpg
import logging
import os
from typing import Optional, Dict, Any, Union, List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection manager with connection pooling"""

    def __init__(self):
        """Initialize the database connection manager"""
        self._pool = None
        self.ready = False

    async def setup(self, bot=None):
        """Set up the database connection pool and initialize tables

        Args:
            bot (commands.Bot, optional): If provided, attaches the pool to bot.db_pool
        """
        if self._pool is not None:
            if bot and not hasattr(bot, "db_pool"):
                bot.db_pool = self._pool
            return

        load_dotenv()

        db_host = os.getenv("DB_HOST", "localhost")
        db_name = os.getenv("DB_NAME", "discord_bot")
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_port = os.getenv("DB_PORT", "5432")

        try:
            self._pool = await asyncpg.create_pool(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_pass,
                port=db_port,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )

            if bot:
                bot.db_pool = self._pool
                logger.info("Database pool attached to bot.db_pool")

            await self._initialize_tables()
            self.ready = True
            logger.info("Database connection established and tables initialized")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def _initialize_tables(self):
        """Initialize necessary database tables if they don't exist"""
        async with self._pool.acquire() as conn:
            with open("schema.sql", "r") as f:
                schema = f.read()
            await conn.execute(schema)

    async def close(self):
        """Close the database connection pool"""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self.ready = False
            logger.info("Database connection closed")

    async def execute(self, query: str, *args, **kwargs):
        """Execute a database query"""
        if not self.ready:
            await self.setup()

        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)

    async def fetch(self, query: str, *args, **kwargs):
        """Fetch multiple rows from the database"""
        if not self.ready:
            await self.setup()

        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args, **kwargs)

    async def fetchrow(self, query: str, *args, **kwargs):
        """Fetch a single row from the database"""
        if not self.ready:
            await self.setup()

        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def fetchval(self, query: str, *args, **kwargs):
        """Fetch a single value from the database"""
        if not self.ready:
            await self.setup()

        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)

    async def run_sql(self, query: str, *args, fetch_type="all"):
        """Run a SQL query with the specified fetch type

        Args:
            query (str): SQL query to execute
            *args: Query parameters
            fetch_type (str): One of 'all', 'row', 'val', or 'execute'

        Returns:
            Query results based on fetch_type
        """
        if not self.ready:
            await self.setup()

        async with self._pool.acquire() as conn:
            if fetch_type == "all":
                return await conn.fetch(query, *args)
            elif fetch_type == "row":
                return await conn.fetchrow(query, *args)
            elif fetch_type == "val":
                return await conn.fetchval(query, *args)
            elif fetch_type == "execute":
                return await conn.execute(query, *args)
            else:
                raise ValueError(f"Invalid fetch_type: {fetch_type}")

    @property
    def pool(self):
        """Get the raw connection pool

        Returns:
            The asyncpg connection pool
        """
        return self._pool

    async def get_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get a guild's information by ID"""
        query = "SELECT * FROM guilds WHERE id = $1"
        record = await self.fetchrow(query, guild_id)
        return dict(record) if record else None

    async def update_guild(self, guild_id: int, name: str) -> None:
        """Update a guild's information or create if not exists"""
        query = """
            INSERT INTO guilds (id, name, last_active)
            VALUES ($1, $2, NOW())
            ON CONFLICT (id) DO UPDATE
            SET name = $2, last_active = NOW()
        """
        await self.execute(query, guild_id, name)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user's information by ID"""
        query = "SELECT * FROM users WHERE id = $1"
        record = await self.fetchrow(query, user_id)
        return dict(record) if record else None

    async def update_user(
        self, user_id: int, username: str, discriminator: str
    ) -> None:
        """Update a user's information or create if not exists"""
        query = """
            INSERT INTO users (id, username, discriminator, last_active)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (id) DO UPDATE
            SET username = $2, discriminator = $3, last_active = NOW()
        """
        await self.execute(query, user_id, username, discriminator)

    async def get_prefix(self, entity_type: str, entity_id: int) -> Optional[str]:
        """Get the custom prefix for a guild or user"""
        query = """
            SELECT prefix FROM prefixes 
            WHERE entity_type = $1 AND entity_id = $2
        """
        return await self.fetchval(query, entity_type, entity_id)

    async def set_prefix(self, entity_type: str, entity_id: int, prefix: str) -> None:
        """Set the custom prefix for a guild or user"""
        query = """
            INSERT INTO prefixes (entity_type, entity_id, prefix)
            VALUES ($1, $2, $3)
            ON CONFLICT (entity_type, entity_id) DO UPDATE
            SET prefix = $3, created_at = NOW()
        """
        await self.execute(query, entity_type, entity_id, prefix)

    async def remove_prefix(self, entity_type: str, entity_id: int) -> bool:
        """Remove the custom prefix for a guild or user"""
        query = """
            DELETE FROM prefixes
            WHERE entity_type = $1 AND entity_id = $2
            RETURNING id
        """
        result = await self.fetchval(query, entity_type, entity_id)
        return result is not None

    async def get_tags(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all tags for a guild"""
        query = """
            SELECT * FROM tags WHERE guild_id = $1
        """
        return await self.fetch(query, guild_id)

    async def get_tag(self, tag_id: str = None, name: str = None, guild_id: int = None):
        """Get a tag by ID or name"""
        if tag_id:
            query = """
                SELECT * FROM tags WHERE id = $1
            """
            return await self.fetchrow(query, tag_id)
        elif name and guild_id:
            query = """
                SELECT * FROM tags WHERE name = $1 AND guild_id = $2
            """
            return await self.fetchrow(query, name, guild_id)
        else:
            return None

    async def create_tag(self, name, content, user_id, guild_id):
        """Create a new tag"""
        query = """
            INSERT INTO tags (name, content, user_id, guild_id, uses)
            VALUES ($1, $2, $3, $4, 0)
            RETURNING id
        """
        return await self.fetchval(query, name, content, user_id, guild_id)

    async def use_tag(self, tag_id: str) -> None:
        """Increment the uses of a tag"""
        query = """
            UPDATE tags
            SET uses = uses + 1
            WHERE id = $1
            RETURNING id
        """
        return await self.execute(query, tag_id)

    async def update_tag(self, tag, name=None, content=None) -> None:
        """Update an existing tag"""
        query = """
            UPDATE tags
            SET name = $1, content = $2
            WHERE id = $3
            RETURNING id
        """
        name = name or tag.name
        content = content or tag.content
        return await self.execute(query, name, content, tag.id)

    async def delete_tag(self, tag_id: str) -> None:
        """Delete a tag by ID"""
        query = """
            DELETE FROM tags
            WHERE id = $1
            RETURNING id
        """
        return await self.execute(query, tag_id)

    async def reset_tags(self, guild_id: int) -> None:
        """Delete all tags for a guild"""
        query = """
            DELETE FROM tags
            WHERE guild_id = $1
            RETURNING id
        """
        return await self.execute(query, guild_id)


db = Database()
