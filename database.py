import aiosqlite


class Database:
    def __init__(self, path: str):
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_context ON messages(user_id, channel_id, id)")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT NOT NULL DEFAULT 'fr'
                )
            """)
            await db.commit()

    async def add_message(self, user_id: int, channel_id: int, role: str, content: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO messages(user_id, channel_id, role, content) VALUES (?, ?, ?, ?)",
                (user_id, channel_id, role, content),
            )
            await db.commit()

    async def get_context(self, user_id: int, channel_id: int, limit: int = 12) -> list[dict[str, str]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT role, content FROM messages WHERE user_id = ? AND channel_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, channel_id, limit),
            )
            rows = await cursor.fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    async def clear_context(self, user_id: int, channel_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM messages WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
            await db.commit()

    async def get_language(self, user_id: int) -> str:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT language FROM user_preferences WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
        return row[0] if row else "fr"

    async def set_language(self, user_id: int, language: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO user_preferences(user_id, language) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET language = excluded.language",
                (user_id, language),
            )
            await db.commit()
