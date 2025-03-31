import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Cache:
    """A simple, efficient cache for database queries with smart invalidation capabilities."""

    def __init__(self, ttl=300):
        self.ttl = ttl
        self.data = {}
        self.table_keys = {}
        self.entity_keys = {}

    def get(self, key: str) -> Tuple[bool, Any]:
        """Get an item from cache if it exists and hasn't expired."""
        if key in self.data:
            result, expiry_time = self.data[key]
            if time.time() < expiry_time:
                logger.debug(f"Cache hit: {key[:50]}...")
                return True, result
            else:
                self._remove(key)
                logger.debug(f"Cache expired: {key[:50]}...")
        return False, None

    def set(
        self,
        key: str,
        result: Any,
        table_name: str,
        entity_ids: Optional[List[str]] = None,
    ) -> None:
        """Store an item in cache with metadata for smart invalidation."""
        if result is None:
            return

        expiry_time = time.time() + self.ttl
        self.data[key] = (result, expiry_time)

        if table_name not in self.table_keys:
            self.table_keys[table_name] = set()
        self.table_keys[table_name].add(key)

        if entity_ids:
            for entity_id in entity_ids:
                if entity_id:
                    if entity_id not in self.entity_keys:
                        self.entity_keys[entity_id] = set()
                    self.entity_keys[entity_id].add(key)

        logger.debug(f"Cached result: {key[:50]}...")

    def _remove(self, key: str) -> None:
        """Remove a specific key from the cache and all tracking structures."""
        if key in self.data:
            del self.data[key]

            # Remove from table tracking
            for table_keys in self.table_keys.values():
                if key in table_keys:
                    table_keys.remove(key)

            # Remove from entity tracking
            for entity_keys in self.entity_keys.values():
                if key in entity_keys:
                    entity_keys.remove(key)

    def invalidate(
        self, table_name: Optional[str] = None, entity_id: Optional[str] = None
    ) -> int:
        """Intelligently invalidate cache entries by table name or entity ID."""
        keys_to_remove = set()

        # Case 1: Full cache invalidation
        if table_name is None and entity_id is None:
            count = len(self.data)
            self.data.clear()
            self.table_keys.clear()
            self.entity_keys.clear()
            return count

        # Case 2: Table-level invalidation
        if table_name and entity_id is None:
            if table_name in self.table_keys:
                keys_to_remove.update(self.table_keys[table_name])
                self.table_keys[table_name].clear()

        # Case 3: Entity-level invalidation
        if entity_id:
            if entity_id in self.entity_keys:
                keys_to_remove.update(self.entity_keys[entity_id])
                self.entity_keys[entity_id].clear()

        # Case 4: Combined table and entity invalidation
        if table_name and entity_id:
            if table_name in self.table_keys and entity_id in self.entity_keys:
                # Find intersection of keys for this table and entity
                table_set = self.table_keys[table_name]
                entity_set = self.entity_keys[entity_id]
                keys_to_remove.update(table_set.intersection(entity_set))

        # Remove all identified keys
        for key in keys_to_remove:
            if key in self.data:
                del self.data[key]

        # Clean up empty sets
        if table_name in self.table_keys and not self.table_keys[table_name]:
            del self.table_keys[table_name]
        if entity_id in self.entity_keys and not self.entity_keys[entity_id]:
            del self.entity_keys[entity_id]

        return len(keys_to_remove)


class Database:
    def __init__(self, cache_ttl=300):
        self._pool = None
        self.ready = False
        self.cache = Cache(ttl=cache_ttl)

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

    def _make_cache_key(self, query: str, args: Tuple) -> str:
        """Generate a unique cache key for a query and its arguments."""
        args_str = str(args) if args else ""
        return hashlib.md5(f"{query}:{args_str}".encode()).hexdigest()

    def _get_table_name(self, query: str) -> str:
        """Extract the table name from a SQL query."""
        query = query.strip().lower()

        # Common tables to check for
        tables = ["guilds", "users", "prefixes", "tags", "afk_users"]

        for table in tables:
            if (
                f" {table} " in query
                or f"from {table}" in query
                or f"into {table}" in query
            ):
                return table

        return "unknown"

    def _get_query_type(self, query: str) -> str:
        """Get the type of SQL query (select, insert, update, delete)."""
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

    def _extract_entity_ids(
        self, query: str, args: Tuple, result: Any = None
    ) -> List[str]:
        """Extract entity IDs from query arguments and results for cache mapping."""
        entity_ids = []
        table = self._get_table_name(query)

        # Extract IDs from arguments for common patterns
        if "where id = $" in query.lower() and args:
            entity_ids.append(str(args[0]))

        # For composite keys like user_id and guild_id
        if table == "afk_users" and len(args) >= 2:
            if "user_id = $1 and guild_id = $2" in query.lower():
                entity_ids.append(f"{args[0]}:{args[1]}")  # Composite key

        # For tags lookups
        if table == "tags" and len(args) >= 2:
            if "name = $1 and guild_id = $2" in query.lower():
                entity_ids.append(f"tag:{args[0]}:{args[1]}")  # Tag name + guild

        # Extract IDs from results
        if result:
            if isinstance(result, asyncpg.Record) and "id" in result:
                entity_ids.append(str(result["id"]))
            elif (
                isinstance(result, list)
                and result
                and isinstance(result[0], asyncpg.Record)
            ):
                for record in result:
                    if "id" in record:
                        entity_ids.append(str(record["id"]))

        return entity_ids

    async def execute(self, query: str, *args, **kwargs) -> str:
        if not self.ready:
            await self.setup()

        query_type = self._get_query_type(query)
        table_name = self._get_table_name(query)

        if query_type in ("insert", "update", "delete") and table_name != "unknown":
            # Automatically invalidate cache for write operations
            self.cache.invalidate(table_name=table_name)

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

        cache_key = self._make_cache_key(query, args)
        hit, result = self.cache.get(cache_key)
        if hit:
            return result

        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetch(query, *args, **kwargs)

                # Store in cache with metadata for smart invalidation
                table = self._get_table_name(query)
                entity_ids = self._extract_entity_ids(query, args, result)
                self.cache.set(cache_key, result, table, entity_ids)

                return result
        except Exception as e:
            logger.error(f"Database fetch error: {e}, Query: {query}")
            raise

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[asyncpg.Record]:
        if not self.ready:
            await self.setup()

        cache_key = self._make_cache_key(query, args)
        hit, result = self.cache.get(cache_key)
        if hit:
            return result

        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(query, *args, **kwargs)

                # Store in cache with metadata for smart invalidation
                table = self._get_table_name(query)
                entity_ids = self._extract_entity_ids(query, args, result)
                self.cache.set(cache_key, result, table, entity_ids)

                return result
        except Exception as e:
            logger.error(f"Database fetchrow error: {e}, Query: {query}")
            raise

    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        if not self.ready:
            await self.setup()

        cache_key = self._make_cache_key(query, args)
        hit, result = self.cache.get(cache_key)
        if hit:
            return result

        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval(query, *args, **kwargs)

                # Only cache non-None results
                if result is not None:
                    table = self._get_table_name(query)
                    entity_ids = self._extract_entity_ids(query, args)
                    self.cache.set(cache_key, result, table, entity_ids)

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
        self.cache.invalidate(table_name="guilds", entity_id=str(guild_id))
        return result

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM users WHERE id = $1"
        record = await self.fetchrow(query, user_id)
        return dict(record) if record else None

    async def update_user(self, user_id: int, username: str) -> str:
        query = """
            INSERT INTO users (id, username, last_active)
            VALUES ($1, $2, NOW())
            ON CONFLICT (id) DO UPDATE
            SET username = $2, last_active = NOW()
        """
        result = await self.execute(query, user_id, username)
        self.cache.invalidate(table_name="users", entity_id=str(user_id))
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
        self.cache.invalidate(table_name="prefixes", entity_id=str(entity_id))
        return result

    async def remove_prefix(self, entity_type: str, entity_id: int) -> bool:
        query = """
            DELETE FROM prefixes
            WHERE entity_type = $1 AND entity_id = $2
            RETURNING id
        """
        result = await self.fetchval(query, entity_type, entity_id)
        self.cache.invalidate(table_name="prefixes", entity_id=str(entity_id))
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
        self.cache.invalidate(table_name="tags", entity_id=str(guild_id))
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
            self.cache.invalidate(table_name="tags", entity_id=str(tag_id))
            self.cache.invalidate(table_name="tags", entity_id=str(guild_id))
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

            self.cache.invalidate(table_name="tags", entity_id=str(tag_id))
            self.cache.invalidate(
                table_name="tags", entity_id=str(current_tag["guild_id"])
            )
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

            self.cache.invalidate(table_name="tags", entity_id=str(tag_id))
            self.cache.invalidate(
                table_name="tags", entity_id=str(current_tag["guild_id"])
            )
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
        self.cache.invalidate(table_name="tags", entity_id=str(guild_id))
        return len(records)

    async def set_afk(self, user_id: int, guild_id: int, message: str) -> str:
        query = """
            INSERT INTO afk_users (user_id, guild_id, message)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id) DO UPDATE
            SET message = $3
        """
        result = await self.execute(query, user_id, guild_id, message)
        composite_key = f"{user_id}:{guild_id}"
        self.cache.invalidate(table_name="afk_users", entity_id=composite_key)
        return result

    async def get_afk(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT * FROM afk_users WHERE user_id = $1 AND guild_id = $2
        """
        record = await self.fetchrow(query, user_id, guild_id)
        return dict(record) if record else None

    async def remove_afk(self, user_id: int, guild_id: int) -> bool:
        query = """
            DELETE FROM afk_users
            WHERE user_id = $1 AND guild_id = $2
            RETURNING id
        """
        result = await self.fetchval(query, user_id, guild_id)

        composite_key = f"{user_id}:{guild_id}"
        self.cache.invalidate(table_name="afk_users", entity_id=composite_key)

        return result is not None

    async def get_guild_afk(self, guild_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT * FROM afk_users WHERE guild_id = $1
        """
        records = await self.fetch(query, guild_id)
        return records


db = Database()
