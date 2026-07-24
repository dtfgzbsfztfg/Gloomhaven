"""
캐릭터 데이터를 SQLite에 저장/조회하는 얇은 레이어.
전투 중 상태(이니셔티브 등)는 DB에 넣지 않고 combat 코그의 메모리에서만 관리한다
(봇이 재시작되면 진행 중이던 전투는 초기화됨 - v2에서 필요하면 영속화 추가 예정).
"""
import os
import aiosqlite

# Railway 등에 배포할 때는 DB_PATH 환경변수로 볼륨 마운트 경로를 지정하세요.
# 예: 볼륨을 /app/data 에 마운트했다면 DB_PATH=/app/data/gloomhaven.db
DB_PATH = os.getenv("DB_PATH", "gloomhaven.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    class_key TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    max_hp INTEGER NOT NULL,
    current_hp INTEGER NOT NULL,
    exp INTEGER NOT NULL DEFAULT 0,
    gold INTEGER NOT NULL DEFAULT 15,
    perk_points INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS campaign_state (
    guild_id INTEGER PRIMARY KEY,
    current_scenario_num INTEGER,
    current_scenario_name TEXT,
    prosperity INTEGER NOT NULL DEFAULT 0,
    reputation INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS completed_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    scenario_num INTEGER,
    scenario_name TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


async def init_db():
    dirname = os.path.dirname(DB_PATH)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def create_character(c) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO characters
               (owner_id, guild_id, name, class_key, level, max_hp, current_hp, exp, gold, perk_points, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c.owner_id, c.guild_id, c.name, c.class_key, c.level,
             c.max_hp, c.current_hp, c.exp, c.gold, c.perk_points, c.notes),
        )
        await db.commit()
        return cur.lastrowid


async def get_character_by_owner(owner_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM characters WHERE owner_id=? AND guild_id=? ORDER BY id DESC LIMIT 1",
            (owner_id, guild_id),
        )
        return await cur.fetchone()


async def get_party(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM characters WHERE guild_id=? ORDER BY name", (guild_id,)
        )
        return await cur.fetchall()


async def update_hp(char_id: int, current_hp: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE characters SET current_hp=? WHERE id=?", (current_hp, char_id))
        await db.commit()


async def update_level(char_id: int, level: int, max_hp: int, current_hp: int, perk_points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE characters SET level=?, max_hp=?, current_hp=?, perk_points=? WHERE id=?",
            (level, max_hp, current_hp, perk_points, char_id),
        )
        await db.commit()


async def update_gold(char_id: int, gold: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE characters SET gold=? WHERE id=?", (gold, char_id))
        await db.commit()


async def get_campaign_state(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM campaign_state WHERE guild_id=?", (guild_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO campaign_state (guild_id, prosperity, reputation, notes) VALUES (?, 0, 0, '')",
                (guild_id,),
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM campaign_state WHERE guild_id=?", (guild_id,))
            row = await cur.fetchone()
        return row


async def set_current_scenario(guild_id: int, num: int | None, name: str | None):
    await get_campaign_state(guild_id)  # ensure row exists
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE campaign_state SET current_scenario_num=?, current_scenario_name=? WHERE guild_id=?",
            (num, name, guild_id),
        )
        await db.commit()


async def adjust_prosperity(guild_id: int, delta: int) -> int:
    await get_campaign_state(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE campaign_state SET prosperity = MAX(0, prosperity + ?) WHERE guild_id=?",
            (delta, guild_id),
        )
        await db.commit()
        cur = await db.execute("SELECT prosperity FROM campaign_state WHERE guild_id=?", (guild_id,))
        return (await cur.fetchone())[0]


async def adjust_reputation(guild_id: int, delta: int) -> int:
    await get_campaign_state(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE campaign_state SET reputation = MAX(-20, MIN(20, reputation + ?)) WHERE guild_id=?",
            (delta, guild_id),
        )
        await db.commit()
        cur = await db.execute("SELECT reputation FROM campaign_state WHERE guild_id=?", (guild_id,))
        return (await cur.fetchone())[0]


async def complete_scenario(guild_id: int, num: int | None, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO completed_scenarios (guild_id, scenario_num, scenario_name) VALUES (?, ?, ?)",
            (guild_id, num, name),
        )
        await db.commit()


async def get_completed_scenarios(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM completed_scenarios WHERE guild_id=? ORDER BY completed_at", (guild_id,)
        )
        return await cur.fetchall()


async def add_achievement(guild_id: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO achievements (guild_id, text) VALUES (?, ?)", (guild_id, text))
        await db.commit()


async def get_achievements(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM achievements WHERE guild_id=? ORDER BY created_at", (guild_id,)
        )
        return await cur.fetchall()


async def delete_character(char_id: int, owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM characters WHERE id=? AND owner_id=?", (char_id, owner_id)
        )
        await db.commit()
        return cur.rowcount > 0
