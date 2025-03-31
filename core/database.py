import logging
import os
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, cache_ttl=300):
        self._pool = None
        self.ready = False
        self.cache_ttl = cache_ttl
        self.cache = {}
        self.table_query_mappings = {
            "guilds": ["id", "name"],
            "users": ["id", "username", "discriminator"],
            "prefixes": ["entity_type", "entity_id", "prefix"],
            "tags": ["id", "name", "content", "user_id", "guild_id", "uses"],
        }

    def _get_cache_key(self, query: str, args: Tuple) -> str:
        """Generate a cache key for the query and args"""
        args_str = str(args) if args else ""
        query_type = self._get_query_type(query)
        table_name = self._get_table_name(query)

        # Create a base key
        base_key = f"{query_type}:{table_name}:{hashlib.md5(f'{query}:{args_str}'.encode()).hexdigest()}"

        return base_key

    def _extract_entity_id(self, query: str, args: Tuple) -> Optional[str]:
        """Try to extract entity ID from query and args for cache mapping"""
        query_lower = query.strip().lower()

        # Handle different query types
        if "where id = $1" in query_lower and args:
            return str(args[0])
        elif "where name = $1 and guild_id = $2" in query_lower and len(args) >= 2:
            # For tag lookups by name, include the guild_id
            return f"name:{args[0]}:guild:{args[1]}"

        return None

    def _get_query_type(self, query: str) -> str:
        query = query.strip().lower()
        if query.startswith("select"):
            return "select"
        elif query.startswith("insert"):
            return "insert"
        elif query.startswith("update"):
            return "update"
        elif query.startswith("delete"):
            return "delete"
        else:
            return "other"

    def _get_table_name(self, query: str) -> str:
        query = query.strip().lower()
        for table in self.table_query_mappings.keys():
            if (
                f" {table} " in query
                or f" {table}\n" in query
                or f"from {table}" in query
            ):
                return table
        return "unknown"

    def _get_from_cache(self, query: str, args: Tuple) -> Tuple[bool, Any]:
        if self._get_query_type(query) in ("insert", "update", "delete"):
            return False, None

        cache_key = self._get_cache_key(query, args)
        if cache_key in self.cache:
            result, expiry_time = self.cache[cache_key]
            if time.time() < expiry_time:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return True, result
            else:
                del self.cache[cache_key]
                logger.debug(f"Cache expired for query: {query[:50]}...")
        return False, None

    def _store_in_cache(self, query: str, args: Tuple, result: Any) -> None:
        if (
            self._get_query_type(query) in ("insert", "update", "delete")
            or result is None
        ):
            return

        cache_key = self._get_cache_key(query, args)
        expiry_time = time.time() + self.cache_ttl
        self.cache[cache_key] = (result, expiry_time)

        # Keep a mapping of entity IDs to cache keys
        if not hasattr(self, "_id_to_cache_keys"):
            self._id_to_cache_keys = {}

        # For single record results
        if isinstance(result, asyncpg.Record) and "id" in result:
            entity_id = str(result["id"])
            if entity_id not in self._id_to_cache_keys:
                self._id_to_cache_keys[entity_id] = set()
            self._id_to_cache_keys[entity_id].add(cache_key)

        # For list of records
        elif (
            isinstance(result, list)
            and result
            and isinstance(result[0], asyncpg.Record)
        ):
            for record in result:
                if "id" in record:
                    entity_id = str(record["id"])
                    if entity_id not in self._id_to_cache_keys:
                        self._id_to_cache_keys[entity_id] = set()
                    self._id_to_cache_keys[entity_id].add(cache_key)

        print(f"Cached result for query: {query[:50]}...")
        logger.debug(f"Cached result for query: {query[:50]}...")

    def invalidate_cache(self, table_name=None, entity_id=None):
        """More intelligent cache invalidation using ID mappings"""
        if not table_name:
            cache_size = len(self.cache)
            self.cache.clear()
            if hasattr(self, "_id_to_cache_keys"):
                self._id_to_cache_keys.clear()
            return cache_size

        keys_to_delete = set()

        print(f"invalidating for id {entity_id} in table {table_name}")

        # If we have the entity ID and it's in our mapping, directly invalidate those cache entries
        if (
            entity_id is not None
            and hasattr(self, "_id_to_cache_keys")
            and entity_id in self._id_to_cache_keys
        ):
            keys_to_delete.update(self._id_to_cache_keys[entity_id])
            # Remove this ID from our mapping
            del self._id_to_cache_keys[entity_id]
        else:
            # Fallback: invalidate by table name prefix
            prefix_pattern = f"{self._get_query_type('select')}:{table_name}:"
            for cache_key in list(self.cache.keys()):
                if cache_key.startswith(prefix_pattern):
                    keys_to_delete.add(cache_key)

        # Delete all the identified keys
        for key in keys_to_delete:
            if key in self.cache:
                del self.cache[key]
                print(f"Deleted {key}")

        print(f"Cache cleared for {len(keys_to_delete)} keys")
        return len(keys_to_delete)

    async def setup(self, bot=None):
        if self._pool is not None:
            if bot and not hasattr(bot, "db_pool"):
                bot.db_pool = self._pool
            return

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
        try:
            async with self._pool.acquire() as conn:
                with open("schema.sql", "r") as f:
                    schema = f.read()
                await conn.execute(schema)
        except FileNotFoundError:
            logger.error("schema.sql file not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")
            raise

    async def close(self):
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self.ready = False
            logger.info("Database connection closed")

    async def execute(self, query: str, *args, **kwargs) -> str:
        if not self.ready:
            await self.setup()

        query_type = self._get_query_type(query)
        table_name = self._get_table_name(query)

        if query_type in ("insert", "update", "delete") and table_name != "unknown":
            self.invalidate_cache(table_name)

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *args, **kwargs)
                return result
        except Exception as e:
            logger.error(f"Database execute error: {e}, Query: {query}")
            raise

    async def fetch(self, query: str, *args, **kwargs) -> List[asyncpg.Record]:
        if not self.ready:
            await self.setup()

        try:
            cache_hit, cached_result = self._get_from_cache(query, args)
            if cache_hit:
                print(f"Cache hit for query: {query[:50]}...")
                return cached_result

            async with self._pool.acquire() as conn:
                result = await conn.fetch(query, *args, **kwargs)
                self._store_in_cache(query, args, result)
                return result
        except Exception as e:
            logger.error(f"Database fetch error: {e}, Query: {query}")
            raise

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[asyncpg.Record]:
        if not self.ready:
            await self.setup()

        try:
            cache_hit, cached_result = self._get_from_cache(query, args)
            if cache_hit:
                print(f"Cache hit for query: {query[:50]}...")
                return cached_result

            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(query, *args, **kwargs)
                self._store_in_cache(query, args, result)
                return result
        except Exception as e:
            logger.error(f"Database fetchrow error: {e}, Query: {query}")
            raise

    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        if not self.ready:
            await self.setup()

        try:
            cache_hit, cached_result = self._get_from_cache(query, args)
            if cache_hit:
                print(f"Cache hit for query: {query[:50]}...")
                return cached_result

            async with self._pool.acquire() as conn:
                result = await conn.fetchval(query, *args, **kwargs)
                self._store_in_cache(query, args, result)
                return result
        except Exception as e:
            logger.error(f"Database fetchval error: {e}, Query: {query}")
            raise

    async def transaction(self):
        if not self.ready:
            await self.setup()
        conn = await self._pool.acquire()
        tx = conn.transaction()
        await tx.start()
        try:
            return conn, tx
        except:
            await tx.rollback()
            await self._pool.release(conn)
            raise

    async def commit_transaction(self, conn, tx):
        try:
            await tx.commit()
        finally:
            await self._pool.release(conn)

    async def rollback_transaction(self, conn, tx):
        try:
            await tx.rollback()
        finally:
            await self._pool.release(conn)

    async def run_sql(self, query: str, *args, fetch_type="all") -> Any:
        if not self.ready:
            await self.setup()

        try:
            if fetch_type == "all":
                return await self.fetch(query, *args)
            elif fetch_type == "row":
                return await self.fetchrow(query, *args)
            elif fetch_type == "val":
                return await self.fetchval(query, *args)
            elif fetch_type == "execute":
                return await self.execute(query, *args)
            else:
                raise ValueError(f"Invalid fetch_type: {fetch_type}")
        except Exception as e:
            logger.error(f"Database run_sql error: {e}, Query: {query}")
            raise

    @property
    def pool(self):
        return self._pool

    async def get_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM guilds WHERE id = $1"
        record = await self.fetchrow(query, guild_id)
        return dict(record) if record else None

    async def update_guild(self, guild_id: int, name: str) -> str:
        query = """
            INSERT INTO guilds (id, name, last_active)
            VALUES ($1, $2, NOW())
            ON CONFLICT (id) DO UPDATE
            SET name = $2, last_active = NOW()
        """
        result = await self.execute(query, guild_id, name)
        self.invalidate_cache("guilds", guild_id)
        return result

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM users WHERE id = $1"
        record = await self.fetchrow(query, user_id)
        return dict(record) if record else None

    async def update_user(self, user_id: int, username: str, discriminator: str) -> str:
        query = """
            INSERT INTO users (id, username, discriminator, last_active)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (id) DO UPDATE
            SET username = $2, discriminator = $3, last_active = NOW()
        """
        result = await self.execute(query, user_id, username, discriminator)
        self.invalidate_cache("users", user_id)
        return result

    async def get_prefix(self, entity_type: str, entity_id: int) -> Optional[str]:
        query = """
            SELECT prefix FROM prefixes 
            WHERE entity_type = $1 AND entity_id = $2
        """
        return await self.fetchval(query, entity_type, entity_id)

    async def set_prefix(self, entity_type: str, entity_id: int, prefix: str) -> str:
        query = """
            INSERT INTO prefixes (entity_type, entity_id, prefix)
            VALUES ($1, $2, $3)
            ON CONFLICT (entity_type, entity_id) DO UPDATE
            SET prefix = $3, created_at = NOW()
        """
        result = await self.execute(query, entity_type, entity_id, prefix)
        self.invalidate_cache("prefixes", entity_id)
        return result

    async def remove_prefix(self, entity_type: str, entity_id: int) -> bool:
        query = """
            DELETE FROM prefixes
            WHERE entity_type = $1 AND entity_id = $2
            RETURNING id
        """
        result = await self.fetchval(query, entity_type, entity_id)
        self.invalidate_cache("prefixes", entity_id)
        return result is not None

    async def get_tags(self, guild_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM tags WHERE guild_id = $1
        """
        records = await self.fetch(query, guild_id)
        return [dict(record) for record in records]

    async def get_tag(
        self, tag_id: str = None, name: str = None, guild_id: int = None
    ) -> Optional[Dict[str, Any]]:
        if tag_id:
            query = """
                SELECT * FROM tags WHERE id = $1
            """
            record = await self.fetchrow(query, tag_id)
            return dict(record) if record else None
        elif name and guild_id:
            query = """
                SELECT * FROM tags WHERE name = $1 AND guild_id = $2
            """
            record = await self.fetchrow(query, name, guild_id)
            return dict(record) if record else None
        else:
            return None

    async def create_tag(self, name, content, user_id, guild_id) -> str:
        query = """
            INSERT INTO tags (name, content, user_id, guild_id, uses)
            VALUES ($1, $2, $3, $4, 0)
            RETURNING id
        """
        tag_id = await self.fetchval(query, name, content, user_id, guild_id)
        self.invalidate_cache("tags", guild_id)
        return tag_id

    async def use_tag(self, tag_id: str) -> Optional[int]:
        query = """
            UPDATE tags
            SET uses = uses + 1
            WHERE id = $1
            RETURNING guild_id
        """
        guild_id = await self.fetchval(query, tag_id)
        if guild_id:
            self.invalidate_cache("tags", tag_id)
            self.invalidate_cache("tags", guild_id)
        return guild_id

    async def update_tag(self, tag_id, name=None, content=None) -> Optional[str]:
        if isinstance(tag_id, dict) and "id" in tag_id:
            tag_id = str(tag_id["id"])
        elif hasattr(tag_id, "id"):
            tag_id = str(tag_id.id)

        current_tag = await self.get_tag(tag_id=tag_id)
        if not current_tag:
            return None

        try:
            conn, tx = await self.transaction()

            query = """
                UPDATE tags
                SET name = $1, content = $2
                WHERE id = $3
                RETURNING id
            """
            name = name or current_tag["name"]
            content = content or current_tag["content"]
            tag_id_result = await conn.fetchval(query, name, content, tag_id)

            await self.commit_transaction(conn, tx)

            self.invalidate_cache("tags", tag_id)
            self.invalidate_cache("tags", current_tag["guild_id"])
            return tag_id_result
        except Exception as e:
            if "conn" in locals() and "tx" in locals():
                await self.rollback_transaction(conn, tx)
            logger.error(f"Failed to update tag: {e}")
            raise

    async def delete_tag(self, tag_id: str) -> Optional[str]:
        current_tag = await self.get_tag(tag_id=tag_id)
        if not current_tag:
            return None

        try:
            conn, tx = await self.transaction()

            query = """
                DELETE FROM tags
                WHERE id = $1
                RETURNING id
            """
            tag_id_result = await conn.fetchval(query, tag_id)

            await self.commit_transaction(conn, tx)

            self.invalidate_cache("tags", tag_id)
            self.invalidate_cache("tags", current_tag["guild_id"])
            return tag_id_result
        except Exception as e:
            if "conn" in locals() and "tx" in locals():
                await self.rollback_transaction(conn, tx)
            logger.error(f"Failed to delete tag: {e}")
            raise

    async def reset_tags(self, guild_id: int) -> int:
        query = """
            DELETE FROM tags
            WHERE guild_id = $1
            RETURNING id
        """
        records = await self.fetch(query, guild_id)
        self.invalidate_cache("tags", guild_id)
        return len(records)


db = Database()
