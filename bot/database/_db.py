from collections.abc import Generator

import pandas as pd
from aiosqlite import Error, IntegrityError, connect

import bot.database.model as model
from bot.discord_cmd.helpers.logger import logger


class BaseDatabase:
    @classmethod
    async def _select(cls, query: str, parameters: tuple = ()) -> tuple | None:
        try:
            async with connect(cls._DB_PATH) as db:
                async with db.execute(query, parameters) as cursor:
                    await db.commit()
                    return await cursor.fetchall()
        except Error as e:
            logger.warning(e)
            return None

    @classmethod
    async def _insert(cls, query: str, parameters: tuple = ()) -> int:
        try:
            async with connect(cls._DB_PATH) as db:
                async with db.execute(query, parameters) as cursor:
                    await db.commit()
                    return cursor.lastrowid

        except Exception as e:
            if "UNIQUE" not in str(e):
                logger.warning(e)
            raise IntegrityError()

    @classmethod
    async def _insert_many(cls, query: str, parameters: tuple = ()) -> None:
        try:
            async with connect(cls._DB_PATH) as db:
                await db.executemany(query, parameters)
                await db.commit()
        except Exception as e:
            if "UNIQUE" not in str(e):
                logger.warning(e)
            raise IntegrityError()


class TrialDatabase(BaseDatabase):
    _DB_PATH = "./data/TrialDatabase.db"

    @staticmethod
    async def create_table() -> None:
        sql_stataments = (
            """CREATE TABLE IF NOT EXISTS trial (
                server_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL,
                log_channel_id INTEGER,
                entry_channel_id INTEGER,
                notify_channel_id INTEGER,
                guild_id INTEGER NOT NULL UNIQUE,
                name TEXT
            );""",
            """CREATE TABLE IF NOT EXISTS trial_entry (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                trial_id INTEGER NOT NULL,
                FOREIGN KEY (trial_id) REFERENCES trial (server_id)
                ON DELETE CASCADE
            );""",
            """CREATE TABLE IF NOT EXISTS trial_category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                allow_parallel INTEGER NOT NULL,
                FOREIGN KEY (trial_id) REFERENCES trial (server_id)
                ON DELETE CASCADE
            );""",
            """CREATE TABLE IF NOT EXISTS trial_task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cooldown INTEGER NOT NULL,
                reward TEXT NOT NULL,
                points INTEGER NOT NULL,
                bonus_time INTEGER,
                bonus TEXT,
                FOREIGN KEY (trial_category_id) REFERENCES trial_category (id)
                ON DELETE CASCADE
            );""",
            """CREATE TABLE IF NOT EXISTS trial_task_requisite (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_task_id INTEGER NOT NULL,
                formula TEXT NOT NULL,
                goal INTEGER NOT NULL,
                FOREIGN KEY (trial_task_id) REFERENCES trial_task (id)
                ON DELETE CASCADE
            );""",
            """CREATE TABLE IF NOT EXISTS trial_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_task_id INTEGER NOT NULL,
                smmo_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status INTEGER NOT NULL,
                cancelled INTEGER NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER,
                update_time INTEGER NOT NULL,
                start_npc INTEGER NOT NULL,
                start_steps INTEGER NOT NULL,
                start_pvp INTEGER NOT NULL,
                start_levels INTEGER NOT NULL,
                current_npc INTEGER NOT NULL,
                current_steps INTEGER NOT NULL,
                current_pvp INTEGER NOT NULL,
                current_levels INTEGER NOT NULL,
                FOREIGN KEY (trial_task_id) REFERENCES trial_task (id)
                ON DELETE CASCADE
            );""",
            """CREATE TABLE IF NOT EXISTS trial_user (
                trial_id INTEGER,
                smmo_id INTEGER,
                points INTEGER,
                PRIMARY KEY (trial_id,smmo_id),
                FOREIGN KEY (trial_id) REFERENCES trial (server_id)
                ON DELETE CASCADE
            );""",
        )

        for statement in sql_stataments:
            await Database._insert(statement)

    ## trial entry
    @staticmethod
    async def select_trial_entry(trial_id: int) -> model.TrialEntry | None:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_entry WHERE trial_id=?", (trial_id,)
        )
        if data is not None and len(data) != 0:
            return model.TrialEntry(*data[0])
        return None

    @staticmethod
    async def insert_trial_entry(
        trial_id: int, message_id: int, channel_id: int
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "INSERT INTO trial_entry VALUES (?,?,?)",
                (
                    message_id,
                    channel_id,
                    trial_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial_entry(
        trial_id: int, message_id: int, channel_id: int
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial_entry SET message_id=?,channel_id=? WHERE trial_id=?",
                (
                    message_id,
                    channel_id,
                    trial_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_trial_entry(trial_id: int) -> None:
        await TrialDatabase._insert(
            "DELETE FROM trial_entry WHERE trial_id=?", (trial_id,)
        )

    ## trial
    @staticmethod
    async def select_all_trial_enabled_ids() -> Generator[int]:
        data = await TrialDatabase._select(
            "SELECT server_id FROM trial WHERE enabled=TRUE"
        )
        if data is not None and len(data) != 0:
            return (int(v[0]) for v in data)
        return None

    @staticmethod
    async def select_trial_log_channel(server_id: int) -> int:
        data = await TrialDatabase._select(
            "SELECT log_channel_id FROM trial WHERE server_id=?", (server_id,)
        )
        if data is not None and len(data) != 0 and data[0][0] is not None:
            return int(data[0][0])
        return None

    @staticmethod
    async def select_trial_x_settings() -> dict:
        data = await TrialDatabase._select("SELECT server_id,name FROM trial")
        if data is not None and len(data) != 0:
            res = {}
            for v in data:
                res.setdefault(v[1], []).append(v[0])
            return res
        return None

    @staticmethod
    async def select_trial_by_server_id(server_id: int) -> model.Trial | None:
        data = await TrialDatabase._select(
            "SELECT * FROM trial WHERE server_id=?", (server_id,)
        )
        if data is not None and len(data) != 0:
            return model.Trial(*data[0])
        return None

    @staticmethod
    async def select_trial_by_guild_id(guild_id: int) -> model.Trial | None:
        data = await TrialDatabase._select(
            "SELECT * FROM trial WHERE guild_id=?", (guild_id,)
        )
        if data is not None and len(data) != 0:
            return model.Trial(*data[0])
        return None

    @staticmethod
    async def insert_trial(
        server_id: int,
        log_channel_id: int,
        notify_channel_id: int,
        entry_channel_id: int,
        guild_id: int,
        name: str,
        enabled: bool = True,
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "INSERT INTO trial VALUES (?,?,?,?,?,?,?)",
                (
                    server_id,
                    enabled,
                    log_channel_id,
                    notify_channel_id,
                    entry_channel_id,
                    guild_id,
                    name,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial(
        server_id: int,
        log_channel_id: int,
        notify_channel_id: int,
        entry_channel_id: int,
        name: str,
        enabled: bool,
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial SET name=?,enabled=?,log_channel_id=?,notify_channel_id=?,entry_channel_id=? WHERE server_id=?",
                (
                    name,
                    enabled,
                    log_channel_id,
                    notify_channel_id,
                    entry_channel_id,
                    server_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_trial(server_id: int) -> None:
        await TrialDatabase._insert("DELETE FROM trial WHERE server_id=?", (server_id,))

    ## trial category
    @staticmethod
    async def select_trial_category(id: int) -> model.TrialCategory | None:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_category WHERE id=?", (id,)
        )
        if data is not None and len(data) != 0:
            return model.TrialCategory(*data[0])
        return None

    @staticmethod
    async def select_trial_category_active(
        trial_id: int,
    ) -> Generator[model.TrialCategory]:
        data = await TrialDatabase._select(
            """SELECT tc.*
                                                FROM trial_category tc
                                                JOIN trial t ON tc.trial_id = t.server_id
                                                WHERE tc.trial_id=? AND t.enabled=TRUE""",
            (trial_id,),
        )
        if data is not None and len(data) != 0:
            return (model.TrialCategory(*v) for v in data)
        return ()

    @staticmethod
    async def insert_trial_category(trial_id: int, name: str, allow_parallel: bool) -> bool|int:
        try:
            return await TrialDatabase._insert(
                "INSERT INTO trial_category (trial_id,name,allow_parallel) VALUES (?,?,?)",
                (
                    trial_id,
                    name,
                    allow_parallel,
                ),
            )
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial_category(trial_category_id: int, name: str) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial_category SET name=? WHERE id=?",
                (
                    name,
                    trial_category_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_trial_category(id: int) -> None:
        await TrialDatabase._insert("DELETE FROM trial_category WHERE id=?", (id,))

    ## trial task
    @staticmethod
    async def select_trial_task(trial_category_id: int) -> Generator[model.TrialTask]:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_task WHERE trial_category_id=?", (trial_category_id,)
        )
        if data is not None and len(data) != 0:
            return (model.TrialTask(*v) for v in data)
        return ()

    @staticmethod
    async def select_trial_task_by_id(id: int) -> model.TrialTask | None:
        data = await TrialDatabase._select("SELECT * FROM trial_task WHERE id=?", (id,))
        if data is not None and len(data) != 0:
            return model.TrialTask(*data[0])
        return None

    @staticmethod
    async def insert_trial_task(
        trial_category_id: int,
        name: str,
        cooldown: int,
        reward: str,
        points: int,
        bonus_time: int,
        bonus: str,
    ) -> bool:
        try:
            return await TrialDatabase._insert(
                "INSERT INTO trial_task (trial_category_id,name,cooldown,reward,points,bonus_time,bonus) VALUES (?,?,?,?,?,?,?)",
                (
                    trial_category_id,
                    name,
                    cooldown,
                    reward,
                    points,
                    bonus_time,
                    bonus,
                ),
            )
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial_task(
        id: int,
        name: str,
        cooldown: int,
        reward: int,
        points: int,
        bonus_time: int,
        bonus: str,
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial_task SET name=?,cooldown=?,reward=?,points=?,bonus_time=?,bonus=? WHERE id=?",
                (
                    name,
                    cooldown,
                    reward,
                    points,
                    id,
                    bonus_time,
                    bonus,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_trial_task(id: int) -> None:
        await TrialDatabase._insert("DELETE FROM trial_task WHERE id=?", (id,))

    ## trial task requisite
    @staticmethod
    async def select_trial_task_requisite(
        trial_task_id: int,
    ) -> Generator[model.TrialTaskRequisite]:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_task_requisite WHERE trial_task_id=?", (trial_task_id,)
        )
        if data is not None and len(data) != 0:
            return (model.TrialTaskRequisite(*v) for v in data)
        return ()

    @staticmethod
    async def insert_trial_task_requisite(
        trial_task_id: int, formula: str, goal: int
    ) -> bool:
        try:
            return await TrialDatabase._insert(
                "INSERT INTO trial_task_requisite (trial_task_id,formula,goal) VALUES (?,?,?)",
                (
                    trial_task_id,
                    formula,
                    goal,
                ),
            )
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial_task_requisite(id: int, formula: str, goal: int) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial_task_requisite SET formula=?,goal=? WHERE id=?",
                (
                    formula,
                    goal,
                    id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_trial_task_requisite(id: int) -> None:
        await TrialDatabase._insert(
            "DELETE FROM trial_task_requisite WHERE id=?", (id,)
        )

    ## trial record
    @staticmethod
    async def select_all_trial_active_record_by_guild_id(
        guild_id: int,
    ) -> Generator[model.TrialRecord]:
        data = await TrialDatabase._select(
            """SELECT tr.*
                                                FROM trial_record tr
                                                JOIN trial_task tt ON tr.trial_task_id = tt.id
                                                JOIN trial_category tc ON tt.trial_category_id = tc.id
                                                JOIN trial t ON tc.trial_id = t.server_id
                                                WHERE t.guild_id=? AND tr.status=FALSE AND tr.cancelled=FALSE""",
            (guild_id,),
        )
        if data is not None and len(data) != 0:
            res = {}
            for v in data:
                if v[2] in res:
                    res[v[2]].append(model.TrialRecord(*v))
                else:
                    res[v[2]] = [model.TrialRecord(*v)]
            return res
        return ()

    @staticmethod
    async def select_all_trial_record_by_guild_id(
        guild_is: int,
    ) -> Generator[model.TrialRecord]:
        data = await TrialDatabase._select(
            """SELECT tr.*
                                                FROM trial_record tr
                                                JOIN trial_task tt ON tr.trial_task_id = tt.id
                                                JOIN trial_category tc ON tt.trial_category_id = tc.id
                                                JOIN trial t ON tc.trial_id = t.id
                                                WHERE t.guild_id=?""",
            (guild_is,),
        )
        if data is not None and len(data) != 0:
            return (model.TrialRecord(*v) for v in data)
        return ()

    @staticmethod
    async def select_all_trial_record(server_id: int) -> Generator[model.TrialRecord]:
        data = await TrialDatabase._select(
            """SELECT tr.*
                                                FROM trial_record tr
                                                JOIN trial_task tt ON tr.trial_task_id = tt.id
                                                JOIN trial_category tc ON tt.trial_category_id = tc.id
                                                WHERE tc.trial_id=?""",
            (server_id,),
        )
        if data is not None and len(data) != 0:
            return (model.TrialRecord(*v) for v in data)
        return ()

    @staticmethod
    async def select_trial_active_record(smmo_id: int) -> Generator[model.TrialRecord]:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_record WHERE smmo_id=? AND status=FALSE AND cancelled=FALSE",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return (model.TrialRecord(*v) for v in data)
        return ()

    @staticmethod
    async def select_trial_last_records(smmo_id: int) -> Generator[model.TrialRecord]:
        data = await TrialDatabase._select(
            """WITH RankedRecords AS (
                    SELECT
                        tr.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY tc.id
                            ORDER BY tr.end_time DESC
                        ) as rn
                    FROM trial_record tr
                    JOIN trial_task tt ON tr.trial_task_id = tt.id
                    JOIN trial_category tc ON tt.trial_category_id = tc.id
                    WHERE tr.smmo_id = ?
            )
            SELECT *
            FROM RankedRecords
            WHERE rn = 1;""",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            # it return the extra row rn (1)
            return (
                model.TrialRecord(*v)
                for i, v in enumerate(data, start=1)
                if i != len(data)
            )
        return ()

    @staticmethod
    async def select_trial_last_record_by_category(
        smmo_id: int, category_id: int
    ) -> model.TrialRecord | None:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_record tr JOIN trial_task tt ON tr.trial_task_id=tt.id WHERE smmo_id=? AND tt.trial_category_id=? AND end_time IS NOT NULL ORDER BY end_time DESC LIMIT 1",
            (
                smmo_id,
                category_id,
            ),
        )
        if data is not None and len(data) != 0:
            return model.TrialRecord(*data[0])
        return None

    @staticmethod
    async def select_trial_record(trial_task_id: int) -> Generator[model.TrialRecord]:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_record WHERE trial_task_id=?", (trial_task_id,)
        )
        if data is not None and len(data) != 0:
            return (model.TrialRecord(*v) for v in data)
        return ()

    @staticmethod
    async def insert_trial_record(
        trial_task_id: int,
        smmo_id: int,
        user_id: int,
        start_time: int,
        end_time: int,
        update_time: int,
        start_npc: int,
        start_steps: int,
        start_pvp: int,
        start_levels: int,
        end_npc: int,
        end_steps: int,
        end_pvp: int,
        end_levels: int,
        status: bool = False,
        cancelled: bool = False,
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "INSERT INTO trial_record (trial_task_id,smmo_id,user_id,status,cancelled,start_time,end_time,update_time,start_npc,start_steps,start_pvp,start_levels,current_npc,current_steps,current_pvp,current_levels) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    trial_task_id,
                    smmo_id,
                    user_id,
                    status,
                    cancelled,
                    start_time,
                    end_time,
                    update_time,
                    start_npc,
                    start_steps,
                    start_pvp,
                    start_levels,
                    end_npc,
                    end_steps,
                    end_pvp,
                    end_levels,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial_record(
        current_npc: int,
        current_steps: int,
        current_pvp: int,
        current_levels: int,
        upd_timestamp: int,
        end_timestamp: int,
        cancelled: bool,
        status: bool,
        id: int,
    ) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial_record SET current_npc=?,current_steps=?,current_pvp=?,current_levels=?,update_time=?,end_time=?,cancelled=?,status=? WHERE id=?",
                (
                    current_npc,
                    current_steps,
                    current_pvp,
                    current_levels,
                    upd_timestamp,
                    end_timestamp,
                    cancelled,
                    status,
                    id,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## trial user
    @staticmethod
    async def select_all_trial_user(server_id: int) -> Generator[model.TrialUser]:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_user WHERE trial_id=?",
            (
                smmo_id,
                server_id,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.TrialUser(*v) for v in data)
        return ()

    @staticmethod
    async def select_trial_user(
        smmo_id: int, server_id: int
    ) -> Generator[model.TrialUser]:
        data = await TrialDatabase._select(
            "SELECT * FROM trial_user WHERE smmo_id=?,trial_id=?",
            (
                smmo_id,
                server_id,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.TrialUser(*v) for v in data)
        return ()

    @staticmethod
    async def insert_trial_user(server_id: int, smmo_id: int) -> bool:
        try:
            await TrialDatabase._insert(
                "INSERT INTO trial_user VALUES (?,?,0)",
                (
                    server_id,
                    smmo_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_trial_user(trial_id: int, smmo_id: int, points: int) -> bool:
        try:
            await TrialDatabase._insert(
                "UPDATE trial_user SET points=? WHERE smmo_id=? AND trial_id=?",
                (
                    points,
                    smmo_id,
                    trial_id,
                ),
            )
            return True
        except IntegrityError:
            return False


class Database(BaseDatabase):
    _DB_PATH = "./data/Database.db"

    @staticmethod
    async def create_table() -> None:
        sql_stataments = (
            """CREATE TABLE IF NOT EXISTS user_stats (
                        smmo_id INTEGER NOT NULL,
                        year INTEGER NOT NULL,
                        month INTEGER NOT NULL,
                        day INTEGER NOT NULL,
                        time INTEGER NOT NULL,
                        level INTEGER NOT NULL,
                        steps INTEGER NOT NULL,
                        npc_kills INTEGER NOT NULL,
                        user_kills INTEGER NOT NULL,
                        quest_performed INTEGER NOT NULL,
                        bounties_completed INTEGER NOT NULL,
                        reputation INTEGER NOT NULL,
                        chests_opened INTEGER NOT NULL,
                        PRIMARY KEY (smmo_id,year,month,day)
                );""",
            """CREATE TABLE IF NOT EXISTS user(
                    discord_id INTEGER NOT NULL,
                    smmo_id INTEGER UNIQUE,
                    verification TEXT,
                    PRIMARY KEY (discord_id)
                );""",
            """CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_year INTEGER NOT NULL,
                    start_month INTEGER NOT NULL,
                    start_day INTEGER NOT NULL,
                    start_time INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    end_year INTEGER NOT NULL,
                    end_month INTEGER NOT NULL,
                    end_day INTEGER NOT NULL,
                    end_time INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    event_type TEXT,
                    guildies_only INTEGER,
                    message_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    team_size INTEGER NOT NULL,
                    global_evt INTEGER
                );""",
            """CREATE TABLE IF NOT EXISTS event_team(
                    team INTEGER,
                    smmo_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    PRIMARY KEY (team,smmo_id,event_id),
                    FOREIGN KEY (event_id) REFERENCES events (id)
                    on DELETE CASCADE
                );""",
            """CREATE TABLE IF NOT EXISTS events_stats(
                    event_id INTEGER NOT NULL,
                    smmo_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    time INTEGER NOT NULL,
                    stats INTEGER NOT NULL,
                    PRIMARY KEY (smmo_id,year,month,day),
                    FOREIGN KEY (event_id) REFERENCES events (id)
                    ON DELETE CASCADE
                );""",
            """CREATE TABLE IF NOT EXISTS event_partecipant(
                    smmo_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    discord_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    team TEXT,
                    points INTEGER,
                    PRIMARY KEY (smmo_id, event_id),
                    FOREIGN KEY (event_id) REFERENCES events (id)
                    on DELETE CASCADE
                );""",
            """CREATE TABLE IF NOT EXISTS event_lb(
                    channel_id INTEGER not NULL,
                    message_id INTEGER not NULL,
                    event_id INTEGER not NULL,
                    PRIMARY KEY (channel_id, event_id),
                    FOREIGN KEY (event_id) REFERENCES events (id)
                    on DELETE CASCADE
                );""",
            """CREATE TABLE IF NOT EXISTS guild_stats(
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    time INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    experience INTEGER NOT NULL,
                    season INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, year, month, day, season)
                );""",
            """CREATE TABLE IF NOT EXISTS worldboss_notification(
                    channel_id INTEGER,
                    role_id INTEGER NOT NULL,
                    seconds_before INTEGER NOT NULL,
                    god INTEGER NOT NULL,
                    boss_id INTEGER NOT NULL,
                    PRIMARY KEY(channel_id, god, seconds_before)
                );""",
            """CREATE TABLE IF NOT EXISTS worldboss_message(
                    channel_id INTEGER PRIMARY KEY,
                    boss_id INTEGER NOT NULL
                );""",
            """CREATE TABLE IF NOT EXISTS leaderboard(
                    channel_id INTEGER PRIMARY KEY,
                    message_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    date TEXT
                );""",
            """CREATE TABLE IF NOT EXISTS api_key(
                    api_key TEXT PRIMARY KEY,
                    guild_id INTEGER,
                    smmo_id INTEGER UNIQUE
                );""",
            """CREATE TABLE IF NOT EXISTS staff(
                    guild_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY(guild_id,role_id)
                );""",
            """CREATE TABLE IF NOT EXISTS server(
                    guild_id INTEGER,
                    server_id INTEGER,
                    PRIMARY KEY (guild_id, server_id)
                );""",
            """CREATE TABLE IF NOT EXISTS orphanage(
                    channel_id INTEGER,
                    role_id INTEGER NOT NULL,
                    tier INTEGER,
                    active INTEGER,
                    message_id INTEGER,
                    PRIMARY KEY (channel_id, tier)
                );""",
            """CREATE TABLE IF NOT EXISTS requirements(
                    guild_id INTEGER PRIMARY KEY,
                    days INTEGER,
                    levels INTEGER,
                    npc INTEGER,
                    pvp INTEGER,
                    steps INTEGER
                );""",
            # TODO: fix this object in the model folder and queries
            """CREATE TABLE IF NOT EXISTS rewards(
                    guild_id INTEGER PRIMARY KEY,
                    type TEXT,
                    n_members INTEGER,
                    gold INTEGER,
                    x_days INTEGER,
                    year INTEGER,
                    month INTEGER,
                    day INTEGER
                );""",
            """CREATE TABLE IF NOT EXISTS monthly_reward(
                    role_id INTEGER NOT NULL,
                    channel_id INTEGER,
                    PRIMARY KEY (channel_id)
                );""",
            """CREATE TABLE IF NOT EXISTS diamonds(
                    role_id INTEGER NOT NULL,
                    channel_id INTEGER,
                    min_price INTEGER NOT NULL,
                    last_min_price TEXT,
                    PRIMARY KEY (channel_id, min_price)
                );""",
            """CREATE TABLE IF NOT EXISTS safe_user(
                    smmo_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    PRIMARY KEY (smmo_id, guild_id)
                );""",
            """CREATE TABLE IF NOT EXISTS worldboss(
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    avatar TEXT,
                    level INTEGER,
                    god INTEGER,
                    strength INTEGER,
                    defence INTEGER,
                    dexterity INTEGER,
                    current_hp INTEGER,
                    max_hp INTEGER,
                    enable_time INTEGER
                );""",
            """CREATE TABLE IF NOT EXISTS gains_leaderboard(
                    channel_id INTEGER PRIMARY KEY,
                    message_id INTEGER NOT NULL
                );""",
            """CREATE TABLE IF NOT EXISTS track(
                    smmo_id INTEGER PRIMARY KEY
                );""",
            """CREATE TABLE IF NOT EXISTS raid(
                    channel_id INTEGER PRIMARY KEY,
                    time INTEGER,
                    duration INTEGER,
                    role_id INTEGER
                );""",
            """CREATE TABLE IF NOT EXISTS valut(
                    code TEXT PRIMARY KEY,
                    year INTEGER,
                    month INTEGER,
                    day INTEGER,
                    note TEXT
                );""",
            """CREATE TABLE IF NOT EXISTS valutmsg(
                    channel_id INTEGER PRIMARY KEY,
                    role_id INTEGER,
                    status INTEGER,
                    message_id INTEGER KEY,
                    code TEXT
                );""",
            """CREATE TABLE IF NOT EXISTS banned(
                    smmo_id INTEGER PRIMARY KEY
                );""",
            """CREATE TABLE IF NOT EXISTS task(
                    channel_id INTEGER,
                    guild_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY (channel_id, guild_id)
                );""",
            """CREATE TABLE IF NOT EXISTS best(
                    smmo_id INTEGER,
                    name TEXT,
                    category TEXT,
                    date INTEGER,
                    levels INTEGER,
                    steps INTEGER,
                    npc INTEGER,
                    pvp INTEGER,
                    PRIMARY KEY (smmo_id,category)
                );""",
            """CREATE TABLE IF NOT EXISTS del_msg(
                message_id INTEGER,
                channel_id INTEGER,
                time INTEGER,
                PRIMARY KEY (message_id, channel_id)
            );""",
            """CREATE TABLE IF NOT EXISTS statistics(
                id TEXT PRIMARY KEY,
                time_used INTEGER,
                average_time REAL
                );""",
            """CREATE TABLE IF NOT EXISTS season(
                id INTEGER PRIMARY KEY,
                name TEXT,
                starts_at TEXT,
                ends_at TEXT
            );""",
            """CREATE TABLE IF NOT EXISTS join_conf(
                guild_id INTEGER PRIMARY KEY,
                msg TEXT,
                groles TEXT,
                vroles TEXT,
                channel INTEGER
            );""",
            """CREATE TABLE IF NOT EXISTS market(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                category INTEGER,
                price TEXT,
                author_id INTEGER,
                author_smmo_id INTEGER,
                author_name TEXT,
                time INTEGER
            );""",
            """CREATE TABLE IF NOT EXISTS market_notice(
                channel_id INTEGER PRIMARY KEY
            );""",
            """CREATE TABLE IF NOT EXISTS market_notice_item(
                item_id INTEGER PRIMARY KEY,
                message_id INTEGER,
                time INTEGER
            );""",
            """CREATE TABLE IF NOT EXISTS complete_lb(
                channel_id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                timestamp INTEGER,
                category TEXT,
                timeframe TEXT
            );""",
            """CREATE TABLE IF NOT EXISTS role_message(
                server_id INTEGER,
                role_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                text TEXT
            );""",
            """CREATE TABLE IF NOT EXISTS monitor_system(
                server_id INTEGER,
                channel_id INTEGER,
                guild_id INTEGER,
                message_id INTEGER,
                PRIMARY KEY (server_id,channel_id)
            );""",
        )

        for statement in sql_stataments:
            await Database._insert(statement)

    ## Monitor System
    @staticmethod
    async def select_all_monitors_config() -> Generator[model.MonitorSystem] | tuple:
        data = await Database._select("SELECT * FROM monitor_system")
        if data is not None and len(data) != 0:
            return (model.MonitorSystem(*v) for v in data)
        return ()

    @staticmethod
    async def select_monitors_config_by_server_id(server_id:int) -> Generator[model.MonitorSystem] | tuple:
        data = await Database._select("SELECT * FROM monitor_system WHERE server_id=?",(server_id,))
        if data is not None and len(data) != 0:
            return (model.MonitorSystem(*v) for v in data)
        return ()

    @staticmethod
    async def select_monitors_config_by_guild_id(guild_id:int) -> Generator[model.MonitorSystem] | tuple:
        data = await Database._select("SELECT * FROM monitor_system WHERE guild_id=?",(guild_id,))
        if data is not None and len(data) != 0:
            return (model.MonitorSystem(*v) for v in data)
        return ()

    @staticmethod
    async def insert_monitors_config(server_id:int,channel_id:int,guild_id:int,message_id:int) -> bool:
        try:
            await Database._insert("INSERT INTO monitor_system VALUES(?,?,?,?)",(server_id,channel_id,guild_id,message_id,))
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_monitor_config(channel_id:int) -> None:
        await Database._insert("DELETE FROM monitor_system WHERE channel_id=?",(channel_id,))

    ## Role Message
    @staticmethod
    async def select_all_role_message() -> Generator[model.RoleMessage]:
        data = await Database._select("SELECT * FROM role_message")
        if data is not None and len(data) != 0:
            return (model.RoleMessage(*v) for v in data)
        return ()

    @staticmethod
    async def select_role_message_bulk(role_ids: list[int]) -> dict:
        if not role_ids:
            return {}
        placeholders = ", ".join(["?"] * len(role_ids))
        data = await Database._select(
            f"SELECT * FROM role_message WHERE role_id IN ({placeholders})",
            (*role_ids,),
        )
        if data is not None and len(data) != 0:
            return {v[1]: model.RoleMessage(*v) for v in data}
        return {}

    @staticmethod
    async def select_role_message(role_id: int) -> model.RoleMessage | None:
        data = await Database._select(
            "SELECT * FROM role_message WHERE role_id=?", (role_id,)
        )
        if data is not None and len(data) != 0:
            return model.RoleMessage(*data[0])
        return None

    @staticmethod
    async def insert_role_message(
        server_id: int, role_id: int, channel_id: int, text: str
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO role_message VALUES(?,?,?,?)",
                (
                    server_id,
                    role_id,
                    channel_id,
                    text,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_role_message(role_id: int) -> None:
        await Database._insert("DELETE FROM role_message WHERE role_id=?", (role_id,))

    ## leaderboard
    @staticmethod
    async def select_all_cmp_lb() -> Generator[model.CompleteLb]:
        data = await Database._select("SELECT * FROM complete_lb")
        if data is not None and len(data) != 0:
            return (model.CompleteLb(*v) for v in data)
        return ()

    @staticmethod
    async def select_all_cmp_sid(server_id:int) -> Generator[model.CompleteLb]:
        data = await Database._select("SELECT * FROM complete_lb WHERE server_id=?",(server_id,))
        if data is not None and len(data) != 0:
            return (model.CompleteLb(*v) for v in data)
        return ()

    @staticmethod
    async def select_cmp_lb(channel_id: int) -> Generator[model.CompleteLb]:
        data = await Database._select(
            "SELECT * FROM complete_lb WHERE channel_id=?", (channel_id,)
        )
        if data is not None and len(data) != 0:
            return (model.CompleteLb(*v) for v in data)
        return ()

    @staticmethod
    async def insert_cmp_lb(
        channel_id: int,
        message_id: int,
        guild_id: int,
        timestamp: int,
        category: str,
        timeframe: str,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO complete_lb VALUES(?,?,?,?,?,?)",
                (
                    channel_id,
                    message_id,
                    guild_id,
                    timestamp,
                    category,
                    timeframe,
                ),
            )
            return True
        except IntegrityError:
            return False


    @staticmethod
    async def update_cmp_lb_sid(channel_id: int, server_id:int) -> bool:
        try:
            await Database._insert(
                "UPDATE complete_lb SET server_id=? WHERE channel_id=?",
                (
                    server_id,
                    channel_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_cmp_lb(
        channel_id: int, timestamp: int, old_message_id: int, message_id: int
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE complete_lb SET message_id=?,timestamp=? WHERE channel_id=? AND message_id=?",
                (
                    message_id,
                    timestamp,
                    channel_id,
                    old_message_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_cmp_lb(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM complete_lb WHERE channel_id=?", (channel_id,)
        )

    ## market notice item
    @staticmethod
    async def select_market_notice_item(item_id: int) -> model.MarketNoticeItem:
        data = await Database._select(
            "SELECT * FROM market_notice_item WHERE item_id=?", (item_id,)
        )
        if data is not None and len(data) != 0:
            return model.MarketNoticeItem(*data[0])
        return None

    @staticmethod
    async def insert_market_notice_item(
        item_id: int, message_id: int, time: int
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO market_notice_item VALUES (?,?,?)",
                (
                    item_id,
                    message_id,
                    time,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_market_notice_item(item_id: int, message_id: int) -> None:
        await Database._insert(
            "DELETE FROM market_notice_item WHERE item_id=? AND message_id=?",
            (
                item_id,
                message_id,
            ),
        )

    @staticmethod
    async def delete_old_market_notice_item() -> None:
        await Database._insert(
            "DELETE FROM market_notice_item WHERE time<=strftime('%s', 'now')"
        )

    ## market notice
    @staticmethod
    async def select_all_market_notice() -> Generator[model.MarketNotice]:
        data = await Database._select("SELECT * FROM market_notice")
        if data is not None and len(data) != 0:
            return (model.MarketNotice(*v) for v in data)
        return ()

    @staticmethod
    async def insert_market_notice(channel_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO market_notice (channel_id) VALUES (?)", (channel_id,)
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_market_notice(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM market_notice WHERE channel_id=?", (channel_id,)
        )

    ## market
    @staticmethod
    async def select_count_all_market() -> int:
        data = await Database._select("SELECT COUNT(*) FROM market")
        if data is not None and len(data) != 0:
            return int(data[0][0])
        return 0

    @staticmethod
    async def select_all_market() -> Generator[model.Market]:
        data = await Database._select("SELECT * FROM market")
        if data is not None and len(data) != 0:
            return (model.Market(*v) for v in data)
        return ()

    @staticmethod
    async def select_market_by_author_timestamp(
        author_id: int, time: int
    ) -> model.Market:
        data = await Database._select(
            "SELECT * FROM market WHERE author_id=? AND time=?",
            (
                author_id,
                time,
            ),
        )
        if data is not None and len(data) != 0:
            return model.Market(*data[0])
        return None

    @staticmethod
    async def select_market_by_cat(category_id: int) -> Generator[model.Market]:
        data = await Database._select(
            "SELECT * FROM market WHERE category=?", (category_id,)
        )
        if data is not None and len(data) != 0:
            return (model.Market(*v) for v in data)
        return ()

    @staticmethod
    async def select_market_by_user(author_id: int) -> Generator[model.Market]:
        data = await Database._select(
            "SELECT * FROM market WHERE author_id=?", (author_id,)
        )
        if data is not None and len(data) != 0:
            return (model.Market(*v) for v in data)
        return ()

    @staticmethod
    async def insert_market_item(
        title: str,
        description: str,
        category: str,
        price: str,
        author_id: int,
        author_smmo_id: int,
        author_name: int,
        time: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO market (title,description,category,price,author_id,author_smmo_id,author_name,time) VALUES (?,?,?,?,?,?,?,?)",
                (
                    title,
                    description,
                    category,
                    price,
                    author_id,
                    author_smmo_id,
                    author_name,
                    time,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_market_item(id: int) -> None:
        await Database._insert("DELETE from market WHERE id=?", (id,))

    @staticmethod
    async def delete_old_market_item() -> None:
        await Database._insert(
            "DELETE FROM market WHERE time<=CAST(strftime('%s', 'now') AS INTEGER)"
        )

    ## join
    @staticmethod
    async def select_join_roles(guild_id: int) -> model.JoinConf | None:
        data = await Database._select(
            "SELECT * FROM join_conf WHERE guild_id=?", (guild_id,)
        )
        if data is not None and len(data) != 0:
            return model.JoinConf(*data[0])
        return None

    @staticmethod
    async def insert_join_roles(
        guild_id: int,
        message: str,
        guildmates_roles: str,
        visitators_roles: str,
        channel: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO join_conf (guild_id,msg,groles,vroles,channel) VALUES (?,?,?,?,?)",
                (
                    guild_id,
                    message,
                    guildmates_roles,
                    visitators_roles,
                    channel,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_join_roles(guild_id: int) -> None:
        await Database._insert("DELETE from join_conf WHERE guild_id=?", (guild_id,))

    ## season
    @staticmethod
    async def select_seasons() -> Generator[model.Season]:
        data = await Database._select("SELECT * FROM season")
        if data is not None and len(data) != 0:
            return (model.Season(*v) for v in data)
        return ()

    @staticmethod
    async def select_last_season() -> model.Season | None:
        data = await Database._select("SELECT * FROM season ORDER BY id DESC LIMIT 1")
        if data is not None and len(data) != 0:
            return model.Season(*data[0])
        return None

    @staticmethod
    async def select_last_season_id() -> int:
        data = await Database._select("SELECT id FROM season ORDER BY id DESC LIMIT 1")
        if data is not None and len(data) != 0:
            return int(*data[0])
        return None

    @staticmethod
    async def insert_season(id: int, name: str, starts_at: str, ends_at: str) -> bool:
        try:
            await Database._insert(
                "INSERT INTO season (id,name,starts_at,ends_at) VALUES (?,?,?,?)",
                (
                    id,
                    name,
                    starts_at,
                    ends_at,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## statistics
    @staticmethod
    async def select_statistics() -> Generator[model.Statistics]:
        data = await Database._select("SELECT * FROM statistics")
        if data is not None and len(data) != 0:
            return (model.Statistics(*v) for v in data)
        return ()

    @staticmethod
    async def insert_statistics(id: str, time: int) -> bool:
        try:
            await Database._insert(
                """
                    INSERT INTO statistics (id, time_used, average_time)
                    VALUES (?, 1, ?)
                    ON CONFLICT(id)
                    DO UPDATE SET
                        time_used = time_used + 1,
                        average_time = (average_time + excluded.average_time) / 2;""",
                (
                    id,
                    time,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## del_msg
    @staticmethod
    async def select_delmsg(time: int) -> Generator[model.DeleteMessage]:
        data = await Database._select("SELECT * FROM del_msg WHERE time <= ?", (time,))
        if data is not None and len(data) != 0:
            return (model.DeleteMessage(*v) for v in data)
        return ()

    @staticmethod
    async def insert_delmsg(message_id: int, channel_id: int, time: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO del_msg VALUES(?,?,?)",
                (
                    message_id,
                    channel_id,
                    time,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_delmsg(message_id: int, time: int) -> bool:
        try:
            await Database._insert(
                "UPDATE del_msg SET time=? WHERE message_id=?",
                (
                    time,
                    message_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_delmsg(message_id: int, channel_id: int) -> None:
        await Database._insert(
            "DELETE from del_msg WHERE message_id=? AND channel_id=?",
            (
                message_id,
                channel_id,
            ),
        )

    ## best
    @staticmethod
    async def select_all_best(category: str, ids:tuple=()) -> Generator[model.BestStats]:
        if len(ids):
            placeholders = ','.join(['?'] * len(ids))

            data = await Database._select(
                f"""SELECT *
                FROM best
                WHERE category=? AND smmo_id IN ({placeholders})
                ORDER BY
                CASE
                    WHEN ?='NPC' THEN npc
                    WHEN ?='PVP' THEN pvp
                    WHEN ?='STEPS' THEN steps
                    WHEN ?='LEVEL' THEN levels
                END
                DESC""",
                (category,*ids,category, category, category, category),
            )
        else:
            data = await Database._select(
                """SELECT *
                FROM best
                WHERE category=?
                ORDER BY
                CASE
                    WHEN ?='NPC' THEN npc
                    WHEN ?='PVP' THEN pvp
                    WHEN ?='STEPS' THEN steps
                    WHEN ?='LEVEL' THEN levels
                END
                DESC""",
                (category, category, category, category, category),
            )
        if data is not None and len(data) != 0:
            return (model.BestStats(*v) for v in data)
        return ()

    @staticmethod
    async def select_best(smmo_id: int) -> Generator[model.BestStats]:
        data = await Database._select("SELECT * FROM best WHERE smmo_id=?", (smmo_id,))
        if data is not None and len(data) != 0:
            return (model.BestStats(*v) for v in data)
        return ()

    @staticmethod
    async def insert_best_bulk(data: list) -> bool:
        try:
            await Database._insert_many("INSERT OR IGNORE INTO best VALUES(?,?,?,?,?,?,?,?)", data)
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def insert_best(
        smmo_id: int,
        name: str,
        category: str,
        date: int,
        levels: int,
        steps: int,
        npc: int,
        pvp: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO best VALUES(?,?,?,?,?,?,?,?)",
                (smmo_id, name, category, date, levels, steps, npc, pvp),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_best(smmo_id: int, category: str) -> None:
        await Database._insert(
            "DELETE from best WHERE smmo_id=? AND category=?",
            (
                smmo_id,
                category,
            ),
        )

    @staticmethod
    async def delete_best_bulk(smmo_ids) -> None:
        placeholders = ", ".join(["?"] * len(smmo_ids))
        await Database._insert(
            f"DELETE FROM best WHERE smmo_id IN ({placeholders})", (*smmo_ids,)
        )

    ##task
    @staticmethod
    async def select_task() -> Generator[model.Task]:
        data = await Database._select("SELECT * FROM task")
        if data is not None and len(data) != 0:
            return (model.Task(*v) for v in data)
        return ()

    @staticmethod
    async def insert_task(channel_id: int, guild_id: int, role_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO task VALUES(?,?,?)",
                (
                    channel_id,
                    guild_id,
                    role_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_task(channel_id: int) -> None:
        await Database._insert("DELETE from task WHERE channel_id=?", (channel_id,))

    ## banned
    @staticmethod
    async def select_banned() -> Generator[int]:
        data = await Database._select("SELECT * FROM banned")
        if data is not None and len(data) != 0:
            return set(int(v[0]) for v in data)
        return ()

    ## banned
    @staticmethod
    async def insert_banned(smmo_id: int) -> bool:
        try:
            await Database._insert("INSERT INTO banned VALUES(?)", (smmo_id,))
            return True
        except IntegrityError:
            return False

    ## valut
    @staticmethod
    async def select_valut(year: int, month: int, day: int) -> model.Valut | None:
        data = await Database._select(
            "SELECT * FROM valut WHERE year=? AND month=? AND day=?",
            (
                year,
                month,
                day,
            ),
        )
        if data is not None and len(data) != 0:
            return model.Valut(*data[0])
        return None

    @staticmethod
    async def insert_valut(
        code: int, year: int, month: int, day: int, note: str
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO valut VALUES(?,?,?,?,?)",
                (
                    code,
                    year,
                    month,
                    day,
                    note,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_valut(year: int, month: int, day: int) -> None:
        await Database._insert(
            "DELETE from valut WHERE year=? AND month=? AND day=?",
            (
                year,
                month,
                day,
            ),
        )

    @staticmethod
    async def delete_all_valut() -> None:
        await Database._insert("DELETE from valut")

    ## valutmsg
    @staticmethod
    async def select_valutmsg() -> Generator[model.ValutMsg]:
        data = await Database._select("SELECT * FROM valutmsg")
        if data is not None and len(data) != 0:
            return (model.ValutMsg(*v) for v in data)
        return ()

    @staticmethod
    async def insert_valutmsg(channel_id: int, role_id: int, message_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO valutmsg VALUES(?,?,0,?,0)",
                (
                    channel_id,
                    role_id,
                    message_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_valutmsg(channel_id: int) -> None:
        await Database._insert("DELETE from valutmsg WHERE channel_id=?", (channel_id,))

    @staticmethod
    async def update_valutmsg(
        status: int, channel_id: int, code: str, message_id: int
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE valutmsg SET status=?, code=?, message_id=? WHERE channel_id=?",
                (
                    status,
                    code,
                    message_id,
                    channel_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## track
    @staticmethod
    async def select_track() -> Generator[model.Track]:
        data = await Database._select("SELECT * FROM track")
        if data is not None and len(data) != 0:
            return (model.Track(*v) for v in data)
        return ()

    @staticmethod
    async def insert_track(smmo_id: int) -> bool:
        try:
            await Database._insert("INSERT INTO track VALUES (?)", (smmo_id,))
            return True
        except IntegrityError:
            return False

    ## user_stats
    @staticmethod
    async def data_for_best(smmo_id: int):
        # data = await Database._select("SELECT user_stats.smmo_id,year,month,day,time,level,steps,npc_kills,user_kills,quest_performed,bounties_completed,reputation,chests_opened FROM user_stats INNER JOIN user ON user_stats.smmo_id=user.smmo_id")
        data = await Database._select(
            "SELECT user_stats.smmo_id,year,month,day,time,level,steps,npc_kills,user_kills,quest_performed,bounties_completed,reputation,chests_opened FROM user_stats WHERE user_stats.smmo_id=?",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            aa = pd.DataFrame(
                data,
                columns=(
                    "smmo_id",
                    "year",
                    "month",
                    "day",
                    "time",
                    "level",
                    "steps",
                    "npc_kills",
                    "user_kills",
                    "quest_performed",
                    "bounties_completed",
                    "reputation",
                    "chest_opened",
                ),
            ).astype(
                {
                    "smmo_id": "uint16",
                    "year": "uint16",
                    "month": "uint8",
                    "day": "uint8",
                    "time": "float32",
                    "level": "uint32",
                    "steps": "uint32",
                    "npc_kills": "uint32",
                    "user_kills": "uint32",
                    "quest_performed": "int32",
                    "bounties_completed": "int32",
                    "reputation": "int16",
                    "chest_opened": "int32",
                }
            )
            aa["date"] = pd.to_datetime(dict(year=aa.year, month=aa.month, day=aa.day))
            return aa
        return ()

    @staticmethod
    async def select_user_stat_data(
        year: int, month: int, day: int
    ) -> Generator[model.UserStat]:
        data = await Database._select(
            "SELECT * FROM user_stats WHERE year=? AND month=? AND day=?",
            (
                year,
                month,
                day,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.UserStat(*v) for v in data)
        return ()

    @staticmethod
    async def select_counter_user_stats(smmo_id: int) -> int:
        data = await Database._select(
            "SELECT count(*) FROM user_stats WHERE smmo_id=?", (smmo_id,)
        )
        if data is not None:
            return int(data[0][0])
        return 0

    @staticmethod
    async def select_user_stat_bulk(
        smmo_ids: list[int], year: int, month: int, day: int
    ) -> dict:
        if not smmo_ids:
            return {}
        placeholders = ", ".join(["?"] * len(smmo_ids))
        data = await Database._select(
            f"SELECT * FROM user_stats WHERE smmo_id IN ({placeholders}) AND year=? AND month=? AND day=?",
            (
                *smmo_ids,
                year,
                month,
                day,
            ),
        )
        if data is not None and len(data) != 0:
            return {v[0]: model.UserStat(*v) for v in data}
        return {}

    @staticmethod
    async def select_user_stat(
        smmo_id: int, year: int, month: int, day: int
    ) -> model.UserStat | None:
        data = await Database._select(
            "SELECT * FROM user_stats WHERE smmo_id=? AND year=? AND month=? AND day=?",
            (
                smmo_id,
                year,
                month,
                day,
            ),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def select_all_user_stats(smmo_id: int):
        data = await Database._select(
            "SELECT * FROM user_stats WHERE smmo_id = ?", (smmo_id,)
        )
        if data is not None and len(data) != 0:
            aa = (
                pd.DataFrame(
                    data,
                    columns=(
                        "smmo_id",
                        "year",
                        "month",
                        "day",
                        "time",
                        "level",
                        "steps",
                        "npc_kills",
                        "user_kills",
                        "quest_performed",
                        "bounties_completed",
                        "reputation",
                        "chest_opened",
                    ),
                )
                .astype(
                    {
                        "smmo_id": "uint16",
                        "year": "uint16",
                        "month": "uint8",
                        "day": "uint8",
                        "time": "float32",
                        "level": "uint32",
                        "steps": "uint32",
                        "npc_kills": "uint32",
                        "user_kills": "uint32",
                        "quest_performed": "int32",
                        "bounties_completed": "int32",
                        "reputation": "int16",
                        "chest_opened": "int32",
                    }
                )
                .set_index("smmo_id")
            )
            aa["date"] = pd.to_datetime(dict(year=aa.year, month=aa.month, day=aa.day))
            return aa
        return ()

    @staticmethod
    async def select_best_step_stats(smmo_id: int) -> model.UserStat | None:
        data = await Database._select(
            """
                                        SELECT
                                            s1.smmo_id,
                                            s1.year,
                                            s1.month,
                                            s1.day,
                                            s1.time,
                                            s1.level - (
                                            SELECT s2.level
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.steps - (
                                            SELECT s2.steps
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ) AS daily_gain,
                                            s1.npc_kills - (
                                            SELECT s2.npc_kills
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.user_kills - (
                                            SELECT s2.user_kills
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            quest_performed,
                                            bounties_completed,
                                            reputation,
                                            chests_opened
                                        FROM user_stats s1
                                        WHERE s1.smmo_id = ?
                                        AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) IS NOT NULL
                                        ORDER BY daily_gain DESC
                                        LIMIT 1;""",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def select_best_level_stats(smmo_id: int) -> model.UserStat | None:
        data = await Database._select(
            """
            SELECT
                s1.smmo_id,
                s1.year,
                s1.month,
                s1.day,
                s1.time,
                s1.level - (
                SELECT s2.level
                FROM user_stats s2
                WHERE s2.smmo_id = s1.smmo_id
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                        = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                LIMIT 1
                ) AS daily_gain,
                s1.steps - (
                SELECT s2.steps
                FROM user_stats s2
                WHERE s2.smmo_id = s1.smmo_id
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                        = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                LIMIT 1
                ),
                s1.npc_kills - (
                SELECT s2.npc_kills
                FROM user_stats s2
                WHERE s2.smmo_id = s1.smmo_id
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                        = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                LIMIT 1
                ),
                s1.user_kills - (
                SELECT s2.user_kills
                FROM user_stats s2
                WHERE s2.smmo_id = s1.smmo_id
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                        = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                    AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                LIMIT 1
                ),
                quest_performed,
                bounties_completed,
                reputation,
                chests_opened
            FROM user_stats s1
            WHERE s1.smmo_id = ?
            AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) IS NOT NULL
            ORDER BY daily_gain DESC
            LIMIT 1;""",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def select_best_npc_stats(smmo_id: int) -> model.UserStat | None:
        data = await Database._select(
            """
                                        SELECT
                                            s1.smmo_id,
                                            s1.year,
                                            s1.month,
                                            s1.day,
                                            s1.time,
                                            s1.level - (
                                            SELECT s2.level
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.steps - (
                                            SELECT s2.steps
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.npc_kills - (
                                            SELECT s2.npc_kills
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ) AS daily_gain,
                                            s1.user_kills - (
                                            SELECT s2.user_kills
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            quest_performed,
                                            bounties_completed,
                                            reputation,
                                            chests_opened
                                        FROM user_stats s1
                                        WHERE s1.smmo_id = ?
                                        AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) IS NOT NULL
                                        ORDER BY daily_gain DESC
                                        LIMIT 1;""",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def select_best_pvp_stats(smmo_id: int) -> model.UserStat | None:
        data = await Database._select(
            """
                                        SELECT
                                            s1.smmo_id,
                                            s1.year,
                                            s1.month,
                                            s1.day,
                                            s1.time,
                                            s1.level - (
                                            SELECT s2.level
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.steps - (
                                            SELECT s2.steps
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.npc_kills - (
                                            SELECT s2.npc_kills
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ),
                                            s1.user_kills - (
                                            SELECT s2.user_kills
                                            FROM user_stats s2
                                            WHERE s2.smmo_id = s1.smmo_id
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                            ) AS daily_gain,
                                            quest_performed,
                                            bounties_completed,
                                            reputation,
                                            chests_opened
                                        FROM user_stats s1
                                        WHERE s1.smmo_id = ?
                                        AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) IS NOT NULL
                                        ORDER BY daily_gain DESC
                                        LIMIT 1;""",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def select_avg_stats_week(smmo_id: int) -> model.UserStat | None:
        data = await Database._select(
            """
                SELECT smmo_id,year,month,day,time,AVG(daily_level),AVG(daily_steps),AVG(daily_npc),AVG(daily_pvp),quest_performed,bounties_completed,reputation,chests_opened
                FROM (SELECT
                    s1.smmo_id,
                    s1.year,
                    s1.month,
                    s1.day,
                    s1.time,
                    s1.level - (
                    SELECT s2.level
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_level,
                    s1.steps - (
                    SELECT s2.steps
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_steps,
                    s1.npc_kills - (
                    SELECT s2.npc_kills
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_npc,
                    s1.user_kills - (
                    SELECT s2.user_kills
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_pvp,
                    quest_performed,
                    bounties_completed,
                    reputation,
                    chests_opened
                FROM user_stats s1
                WHERE s1.smmo_id = ?
                AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) >= date('now', '-7 days'));
            """,
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def select_avg_stats(smmo_id: int) -> model.UserStat | None:
        data = await Database._select(
            """
                SELECT smmo_id,year,month,day,time,AVG(daily_level),AVG(daily_steps),AVG(daily_npc),AVG(daily_pvp),quest_performed,bounties_completed,reputation,chests_opened
                FROM (SELECT
                    s1.smmo_id,
                    s1.year,
                    s1.month,
                    s1.day,
                    s1.time,
                    s1.level - (
                    SELECT s2.level
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_level,
                    s1.steps - (
                    SELECT s2.steps
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_steps,
                    s1.npc_kills - (
                    SELECT s2.npc_kills
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_npc,
                    s1.user_kills - (
                    SELECT s2.user_kills
                    FROM user_stats s2
                    WHERE s2.smmo_id = s1.smmo_id
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                            = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                        AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                    LIMIT 1
                    ) AS daily_pvp,
                    quest_performed,
                    bounties_completed,
                    reputation,
                    chests_opened
                FROM user_stats s1
                WHERE s1.smmo_id = ?
                AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) IS NOT NULL);""",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return model.UserStat(*data[0])
        return None

    @staticmethod
    async def insert_user_stat_bulk(data: list) -> bool:
        try:
            await Database._insert_many(
                "INSERT OR IGNORE INTO user_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                data,
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def insert_user_stat(
        smmo_id: int,
        year: int,
        month: int,
        day: int,
        time: int,
        level: int,
        steps: int,
        npc_kills: int,
        user_kills: int,
        quest_performed: int,
        bounties_completed: int,
        reputation: int,
        chests_opened: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO user_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    smmo_id,
                    year,
                    month,
                    day,
                    time,
                    level,
                    steps,
                    npc_kills,
                    user_kills,
                    quest_performed,
                    bounties_completed,
                    reputation,
                    chests_opened,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_user_stat(
        smmo_id: int,
        year: int,
        month: int,
        day: int,
        quest_performed: int,
        bounties_completed: int,
        reputation: int,
        chests_opened: int,
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE user_stats SET quest_performed=?,bounties_completed=?,reputation=?,chests_opened=? WHERE smmo_id=? AND year=? AND month=? AND day=?",
                (
                    quest_performed,
                    bounties_completed,
                    reputation,
                    chests_opened,
                    smmo_id,
                    year,
                    month,
                    day,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## user
    @staticmethod
    async def select_all_user() -> Generator[model.User]:
        data = await Database._select("SELECT * FROM user")
        if data is not None and len(data) != 0:
            return (model.User(*v) for v in data)
        return ()

    @staticmethod
    async def select_counter_user_linked() -> int:
        data = await Database._select("SELECT COUNT(discord_id) FROM user")
        if data is not None and len(data) != 0:
            return int(data[0][0])
        return 0

    @staticmethod
    async def select_user_discord(discord_id: int) -> model.User | None:
        data = await Database._select(
            "SELECT * FROM user WHERE discord_id=?", (discord_id,)
        )
        if data is not None and len(data) != 0:
            return model.User(*data[0])
        return None

    @staticmethod
    async def select_user_smmoid(smmo_id: int) -> model.User | None:
        data = await Database._select("SELECT * FROM user WHERE smmo_id=?", (smmo_id,))
        if data is not None and len(data) != 0:
            return model.User(*data[0])
        return None

    @staticmethod
    async def insert_user(discord_id: int, verification: str) -> bool:
        try:
            await Database._insert(
                "INSERT INTO user VALUES (?,NULL,?)", (discord_id, verification)
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_user(discord_id: int, smmo_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE user SET smmo_id=?,verification=NULL WHERE discord_id=?",
                (
                    smmo_id,
                    discord_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_user(discord_id: int) -> None:
        await Database._insert("DELETE FROM user WHERE discord_id=?", (discord_id,))

    @staticmethod
    async def select_events_by_starting_day(
        year: int, month: int, day: int
    ) -> Generator[model.Event]:
        data = await Database._select(
            "SELECT * FROM events WHERE start_year=? AND start_month=? AND start_day=? ORDER BY start_time ASC",
            (
                year,
                month,
                day,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.Event(*v) for v in data)
        return ()

    @staticmethod
    async def select_all_global_events(timestamp: int = 0) -> Generator[model.Event]:
        data = await Database._select(
            "SELECT * FROM events WHERE end_time>=? AND global_evt=1 ORDER BY start_time ASC",
            (timestamp,),
        )
        if data is not None and len(data) != 0:
            return (model.Event(*v) for v in data)
        return ()

    @staticmethod
    async def select_all_events(timestamp: int = 0) -> Generator[model.Event]:
        data = await Database._select(
            "SELECT * FROM events WHERE end_time>=? ORDER BY start_time ASC",
            (timestamp,),
        )
        if data is not None and len(data) != 0:
            return (model.Event(*v) for v in data)
        return ()

    @staticmethod
    async def select_all_guild_events(guild_id: int) -> Generator[model.Event]:
        data = await Database._select(
            "SELECT * FROM events WHERE igguild_id=? ORDER BY start_time ASC",
            (guild_id,),
        )
        if data is not None and len(data) != 0:
            return (model.Event(*v) for v in data)
        return ()

    @staticmethod
    async def select_events(guild_id: int, timestamp: int) -> Generator[model.Event]:
        data = await Database._select(
            "SELECT * FROM events WHERE guild_id=? AND end_time>=? ORDER BY start_time ASC",
            (
                guild_id,
                timestamp,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.Event(*v) for v in data)
        return ()

    @staticmethod
    async def select_event(event_id: int) -> model.Event | None:
        data = await Database._select("SELECT * FROM events WHERE id=? ", (event_id,))
        if data is not None and len(data) != 0:
            return model.Event(*data[0])
        return None

    @staticmethod
    async def select_events_by_message(
        guild_id: int, message_id: int
    ) -> model.Event | None:
        data = await Database._select(
            "SELECT * FROM events WHERE guild_id=? AND message_id=?",
            (
                guild_id,
                message_id,
            ),
        )
        if data is not None and len(data) != 0:
            return model.Event(*data[0])
        return None

    @staticmethod
    async def insert_event(
        start_year: int,
        start_month: int,
        start_day: int,
        start_time: int,
        guild_id: int,
        end_year: int,
        end_month: int,
        end_day: int,
        end_time: int,
        name: str,
        description: str,
        event_type: str,
        guildies_only: int,
        message_id: int,
        channel_id: int,
        team_size: int,
        custom_image: str,
        custom_thumbnail: str,
        global_evt: bool,
        host: str,
        igguild_id: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO events(start_year,start_month,start_day,start_time,guild_id,end_year,end_month,end_day,end_time,name,description,event_type,guildies_only,message_id,channel_id,team_size,custom_image,custom_thumbnail,global_evt,host,igguild_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    start_year,
                    start_month,
                    start_day,
                    start_time,
                    guild_id,
                    end_year,
                    end_month,
                    end_day,
                    end_time,
                    name,
                    description,
                    event_type,
                    guildies_only,
                    message_id,
                    channel_id,
                    team_size,
                    custom_image,
                    custom_thumbnail,
                    global_evt,
                    host,
                    igguild_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_event(
        event_id: int,
        start_year: int,
        start_month: int,
        start_day: int,
        start_time: int,
        guild_id: int,
        end_year: int,
        end_month: int,
        end_day: int,
        end_time: int,
        name: str,
        description: str,
        event_type: str,
        guildies_only: int,
        team_size: int,
        message_id: int,
        channel_id: int,
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE events SET start_year=?,start_month=?,start_day=?,start_time=?,end_year=?,end_month=?,end_day=?,end_time=?,name=?,description=?,event_type=?,guildies_only=?,team_size=?,channel_id=?,message_id=? WHERE id=? AND guild_id=?",
                (
                    start_year,
                    start_month,
                    start_day,
                    start_time,
                    end_year,
                    end_month,
                    end_day,
                    end_time,
                    name,
                    description,
                    event_type,
                    guildies_only,
                    team_size,
                    channel_id,
                    message_id,
                    event_id,
                    guild_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_event(event_id: int, guild_id: int) -> None:
        await Database._insert(
            "DELETE FROM events WHERE event_id=? AND guild_id=?",
            (
                event_id,
                guild_id,
            ),
        )

    ## event stats
    @staticmethod
    async def select_event_stats(smmo_id: int) -> model.EventStats | None:
        data = await Database._select(
            "SELECT * FROM event_stats WHERE smmo_id=?", (smmo_id,)
        )
        if data is not None and len(data) != 0:
            return model.EventStats(*data[0])
        return None

    @staticmethod
    async def insert_event_stats(
        event_id: int,
        smmo_id: int,
        year: int,
        month: int,
        day: int,
        time: int,
        stats: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO events_stats VALUES(?,?,?,?,?,?,?)",
                (
                    event_id,
                    smmo_id,
                    year,
                    month,
                    day,
                    time,
                    stats,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## event team
    @staticmethod
    async def select_event_team_all(
        event_id: int,
    ) -> Generator[model.EventPartecipants]:
        data = await Database._select(
            "SELECT et.* FROM event_team et WHERE et.team=? AND et.event_id=?",
            (
                team_id,
                event_id,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.EventPartecipants(*v) for v in data)
        return ()

    @staticmethod
    async def select_event_team(
        team_id: str, event_id: int
    ) -> Generator[model.EventPartecipants]:
        data = await Database._select(
            "SELECT et.* FROM event_partecipant et WHERE et.team=? AND et.event_id=?",
            (
                team_id,
                event_id,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.EventPartecipants(*v) for v in data)
        return ()

    @staticmethod
    async def insert_event_team(
        team: int, smmo_id: int, event_id: int, guild_id: int
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO event_team VALUES(?,?,?,?)",
                (
                    team,
                    smmo_id,
                    event_id,
                    guild_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_event_team(smmo_id: int, team: int, event_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE event_team SET team=? WHERE smmo_id=? AND event_id=?",
                (
                    team,
                    smmo_id,
                    event_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_event_team(smmo_id: int, event_id: int) -> None:
        await Database._insert(
            "DELETE FROM event_team WHERE smmo_id=? AND event_id=?",
            (
                smmo_id,
                event_id,
            ),
        )

    ## event partecipant
    @staticmethod
    async def select_event_partecipants(
        event_id: int,
    ) -> Generator[model.EventPartecipants]:
        data = await Database._select(
            "SELECT * FROM event_partecipant WHERE event_id = ? ORDER BY team ASC",
            (event_id,),
        )
        if data is not None and len(data) != 0:
            return (model.EventPartecipants(*v) for v in data)
        return ()

    @staticmethod
    async def select_event_partecipant(
        event_id: int, smmo_id: int
    ) -> model.EventPartecipants | None:
        data = await Database._select(
            "SELECT * FROM event_partecipant WHERE event_id = ? AND smmo_id=?",
            (
                event_id,
                smmo_id,
            ),
        )
        if data is not None and len(data) != 0:
            return model.EventPartecipants(*data[0])
        return None

    @staticmethod
    async def select_event_user_partecipants(
        smmo_id: int,
    ) -> Generator[model.EventPartecipants]:
        data = await Database._select(
            "SELECT * FROM event_partecipant WHERE smmo_id = ? ORDER BY event_id DESC",
            (smmo_id,),
        )
        if data is not None and len(data) != 0:
            return (model.EventPartecipants(*v) for v in data)
        return ()

    @staticmethod
    async def select_event_user_partecipants_events(
        smmo_id: int, time: int
    ) -> Generator[model.EventPartecipants]:
        data = await Database._select(
            "SELECT ep.* FROM event_partecipant ep INNER JOIN events ON ep.event_id = events.id WHERE events.start_time<=? AND events.end_time>=?",
            (
                smmo_id,
                time,
                time,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.EventPartecipants(*v) for v in data)
        return ()

    @staticmethod
    async def select_counter_event_user_partecipants(event_id: int) -> int:
        data = await Database._select(
            "SELECT COUNT(smmo_id) FROM event_partecipant WHERE event_id = ?",
            (event_id,),
        )
        if data is not None and len(data) != 0:
            return int(data[0][0])
        return ()

    @staticmethod
    async def insert_event_partecipant(
        smmo_id: int, name: str, discord_id: int, event_id: int, team: str = ""
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO event_partecipant VALUES(?,?,?,?,?,0)",
                (
                    smmo_id,
                    name,
                    discord_id,
                    event_id,
                    team,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_event_partecipant(smmo_id: int, event_id: int, team: str) -> bool:
        try:
            await Database._insert(
                "UPDATE event_partecipant SET team=? WHERE smmo_id=? AND event_id=?",
                (
                    team,
                    smmo_id,
                    event_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_event_partecipant_points(
        smmo_id: int, event_id: int, points: str
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE event_partecipant SET points=? WHERE smmo_id=? AND event_id=?",
                (
                    points,
                    smmo_id,
                    event_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_event_partecipant(smmo_id: int, event_id: int) -> None:
        await Database._insert(
            "DELETE FROM event_partecipant WHERE smmo_id=? AND event_id=?",
            (
                smmo_id,
                event_id,
            ),
        )

    ## event lb
    @staticmethod
    async def select_all_event_lb() -> Generator[model.EventLeaderboard]:
        data = await Database._select("SELECT * FROM event_lb")
        if data is not None and len(data) != 0:
            return (model.EventLeaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def insert_event_lb(channel_id: int, message_id: int, event_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO event_lb VALUES(?,?,?)",
                (
                    channel_id,
                    message_id,
                    event_id,
                ),
            )
            return True
        except IntegrityError:
            logger.exception("Insert_event_lb")
            return False

    @staticmethod
    async def update_event_lb(channel_id: int, event_id: int, message_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE event_lb SET message_id=? WHERE channel_id=? AND event_id=?",
                (
                    message_id,
                    channel_id,
                    event_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_event_lb(channel_id: int, event_id: int) -> None:
        await Database._insert(
            "DELETE FROM event_lb WHERE channel_id=? AND event_id=?",
            (
                channel_id,
                event_id,
            ),
        )

    ## guild stats
    @staticmethod
    async def select_guild_stats_data(
        year: int, month: int, day: int, season: int
    ) -> Generator[model.GuildStats]:
        data = await Database._select(
            "SELECT * FROM guild_stats WHERE year=? AND month=? AND day=? AND season=?",
            (
                year,
                month,
                day,
                season,
            ),
        )
        if data is not None and len(data) != 0:
            return (model.GuildStats(*v) for v in data)
        return ()

    @staticmethod
    async def select_guild_stats(
        guild_id: int, year: int, month: int, day: int, season: int
    ) -> model.GuildStats | None:
        data = await Database._select(
            "SELECT * FROM guild_stats WHERE guild_id=? AND year=? AND month=? AND day=? AND season=?",
            (
                guild_id,
                year,
                month,
                day,
                season,
            ),
        )
        if data is not None and len(data) != 0:
            return model.GuildStats(*data[0])
        return None

    @staticmethod
    async def select_all_guild_stats(season: int):
        # data = await Database._select("SELECT * FROM guild_stats WHERE guild_id = ? AND season = ?",(guild_id,season,))
        data = await Database._select(
            "SELECT * FROM guild_stats WHERE season = ?", (season,)
        )
        if data is not None and len(data) != 0:
            aa = (
                pd.DataFrame(
                    data,
                    columns=[
                        "year",
                        "month",
                        "day",
                        "time",
                        "guild_id",
                        "position",
                        "experience",
                        "season",
                    ],
                )
                .astype(
                    {
                        "year": "uint16",
                        "month": "uint8",
                        "day": "uint8",
                        "time": "float32",
                        "guild_id": "uint16",
                        "position": "int8",
                        "experience": "uint32",
                        "season": "uint8",
                    }
                )
                .drop(columns="season")
            )
            aa["date"] = pd.to_datetime(dict(year=aa.year, month=aa.month, day=aa.day))
            return aa
        return ()

    @staticmethod
    async def select_all_guilds_stats(season: int):
        data = await Database._select(
            "SELECT * FROM guild_stats WHERE season = ?", (season,)
        )
        if data is not None and len(data) != 0:
            aa = (
                pd.DataFrame(
                    data,
                    columns=[
                        "year",
                        "month",
                        "day",
                        "time",
                        "guild_id",
                        "position",
                        "experience",
                        "season",
                    ],
                )
                .astype(
                    {
                        "year": "uint16",
                        "month": "uint8",
                        "day": "uint8",
                        "time": "float32",
                        "guild_id": "uint16",
                        "position": "int8",
                        "experience": "uint32",
                        "season": "uint8",
                    }
                )
                .set_index("guild_id")
            )
            aa["date"] = pd.to_datetime(dict(year=aa.year, month=aa.month, day=aa.day))
            return aa
        return ()

    @staticmethod
    async def select_best_experience_gain(guild_id: int) -> model.GuildStats | None:
        data = await Database._select(
            """
                                        SELECT s1.year,s1.month,s1.day,s1.time,s1.guild_id,0,
                                        s1.experience - (
                                            SELECT s2.experience
                                            FROM guild_stats s2
                                            WHERE s2.guild_id = s1.guild_id
                                                AND s2.season = s1.season
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day))
                                                    = date(date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)), '-1 day')
                                                AND date(s2.year || '-' || printf('%02d', s2.month) || '-' || printf('%02d', s2.day)) IS NOT NULL
                                            LIMIT 1
                                        ) AS daily_gain,
                                        s1.season
                                        FROM guild_stats s1
                                        WHERE s1.guild_id = ?
                                        AND date(s1.year || '-' || printf('%02d', s1.month) || '-' || printf('%02d', s1.day)) IS NOT NULL
                                        ORDER BY daily_gain DESC
                                        LIMIT 5;
                                    """,
            (guild_id,),
        )
        if data is not None and len(data) != 0:
            return (model.GuildStats(*v) for v in data)
        return None

    @staticmethod
    async def insert_guild_stats(
        year: int,
        month: int,
        day: int,
        time: int,
        guild_id: int,
        position: int,
        experience: int,
        season: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO guild_stats VALUES(?,?,?,?,?,?,?,?)",
                (
                    year,
                    month,
                    day,
                    time,
                    guild_id,
                    position,
                    experience,
                    season,
                ),
            )
            return True
        except IntegrityError:
            return False

    ## worldboss notification
    @staticmethod
    async def select_wb_notification() -> Generator[model.WorldbossNotification]:
        data = await Database._select(
            "SELECT * FROM worldboss_notification ORDER BY seconds_before ASC"
        )
        if data is not None and len(data) != 0:
            return (model.WorldbossNotification(*v) for v in data)
        return ()

    @staticmethod
    async def select_wb_notification_sid(server_id:int) -> Generator[model.WorldbossNotification]:
        data = await Database._select("SELECT * FROM worldboss_notification WHERE server_id=? ORDER BY seconds_before ASC",(server_id,))
        if data is not None and len(data) != 0:
            return (model.WorldbossNotification(*v) for v in data)
        return ()

    @staticmethod
    async def insert_wb_notification(channel_id: int, role_id: int, seconds_before: int, god: bool, server_id:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO worldboss_notification VALUES(?,?,?,?,0,?)",
                (
                    channel_id,
                    role_id,
                    seconds_before,
                    int(god),
                    server_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_wb_notification_sid(channel_id: int, server_id: int,seconds_before:int) -> bool:
        try:
            await Database._insert(
                "UPDATE worldboss_notification SET server_id=? WHERE channel_id=? AND seconds_before=?",
                (
                    server_id,
                    channel_id,
                    seconds_before,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_wb_notification(
        channel_id: int, boss_id: int, seconds_before: int
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE worldboss_notification SET boss_id=? WHERE channel_id=? AND seconds_before=?",
                (
                    boss_id,
                    channel_id,
                    seconds_before,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_wb_notification(channel_id: int, seconds_before: int) -> None:
        await Database._insert(
            "DELETE FROM worldboss_notification WHERE channel_id=? AND seconds_before=?",
            (
                channel_id,
                seconds_before,
            ),
        )

    ## worldboss message
    @staticmethod
    async def select_wb_message() -> Generator[model.WorldbossMessage]:
        data = await Database._select("SELECT * FROM worldboss_message")
        if data is not None and len(data) != 0:
            return (model.WorldbossMessage(*v) for v in data)
        return ()

    @staticmethod
    async def select_wb_message_sid(server_id:int) -> Generator[model.WorldbossMessage]:
        data = await Database._select("SELECT * FROM worldboss_message WHERE server_id=?",(server_id,))
        if data is not None and len(data) != 0:
            return (model.WorldbossMessage(*v) for v in data)
        return ()

    @staticmethod
    async def insert_wb_message(channel_id: int, server_id:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO worldboss_message VALUES(?,0,?)", (channel_id,server_id,)
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_wb_message_sid(channel_id: int, server_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE worldboss_message SET server_id=? WHERE channel_id=?",
                (
                    server_id,
                    channel_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_wb_message(channel_id: int, boss_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE worldboss_message SET boss_id=? WHERE channel_id=?",
                (
                    boss_id,
                    channel_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_wb_message(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM worldboss_message WHERE channel_id=?", (channel_id,)
        )

    ## leaderboard
    @staticmethod
    async def select_all_lb() -> Generator[model.Leaderboard]:
        data = await Database._select("SELECT * FROM leaderboard")
        if data is not None and len(data) != 0:
            return (model.Leaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def select_lb_sid(server_id: int) -> Generator[model.Leaderboard]:
        data = await Database._select("SELECT * FROM leaderboard WHERE server_id=?", (server_id,))
        if data is not None and len(data) != 0:
            return (model.Leaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def select_lb(channel_id: int) -> Generator[model.Leaderboard]:
        data = await Database._select(
            "SELECT * FROM leaderboard WHERE channel_id=?", (channel_id,)
        )
        if data is not None and len(data) != 0:
            return (model.Leaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def insert_lb(channel_id: int, message_id: int, guild_id: int, server_id:int, timeframe:str, timestamp:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO leaderboard VALUES(?,?,?,?,?,?)",
                (
                    channel_id,
                    message_id,
                    guild_id,
                    server_id,
                    timeframe,
                    timestamp,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_lb_sid(channel_id: int, server_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE leaderboard SET server_id=? WHERE channel_id=?",
                (
                    server_id,
                    channel_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_lb(channel_id: int, timestamp: int, message_id: int,old_message_id:int) -> bool:
        try:
            await Database._insert(
                "UPDATE leaderboard SET message_id=?,timestamp=? WHERE channel_id=? AND message_id=?",
                (
                    message_id,
                    timestamp,
                    channel_id,
                    old_message_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_lb(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM leaderboard WHERE channel_id=?", (channel_id,)
        )

    ## api_key
    @staticmethod
    async def select_api_keys() -> Generator[model.ApiKey]:
        data = await Database._select("SELECT * FROM api_key")
        if data is not None and len(data) != 0:
            return (model.ApiKey(*v) for v in data)
        return ()

    @staticmethod
    async def insert_api_key(api_key: str, guild_id: int | None, smmo_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO api_key VALUES(?,?,?)",
                (
                    api_key,
                    guild_id,
                    smmo_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_api_key(api_key: str, guild_id: int | None) -> bool:
        try:
            await Database._insert(
                "UPDATE api_key SET guild_id=? WHERE api_key=?",
                (
                    guild_id,
                    api_key,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_api_key(smmo_id: int) -> None:
        await Database._insert("DELETE FROM api_key WHERE smmo_id=?", (smmo_id))

    ## staff
    @staticmethod
    async def select_staff(guild_id: int) -> Generator[model.Staff]:
        data = await Database._select(
            "SELECT * FROM staff WHERE guild_id=?", (guild_id,)
        )
        if data is not None and len(data) != 0:
            return (model.Staff(*v) for v in data)
        return ()

    @staticmethod
    async def insert_staff(guild_id: int, role_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO staff VALUES(?,?)",
                (
                    guild_id,
                    role_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_staff(guild_id: int, role_id: int) -> None:
        await Database._insert(
            "DELETE FROM staff WHERE guild_id=? AND role_id=?",
            (
                guild_id,
                role_id,
            ),
        )

    ## server
    @staticmethod
    async def select_all_server_guild() -> Generator[int]:
        data = await Database._select("SELECT guild_id FROM server")
        if data is not None and len(data) != 0:
            return (int(v[0]) for v in data)
        return ()

    @staticmethod
    async def select_counter_guild_linked() -> int:
        data = await Database._select("SELECT COUNT(server_id) FROM server")
        if data is not None and len(data) != 0:
            return int(data[0][0])
        return 0

    @staticmethod
    async def select_server(server_id: int) -> int | None:
        data = await Database._select(
            "SELECT guild_id FROM server WHERE server_id=?", (server_id,)
        )
        if data is not None and len(data) != 0:
            return int(*data[0])
        return None

    @staticmethod
    async def insert_server(guild_id: int, server_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO server VALUES(?,?)",
                (
                    guild_id,
                    server_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_server(server_id: int) -> None:
        await Database._insert("DELETE FROM server WHERE server_id=?", (server_id,))

    ## orphanage
    @staticmethod
    async def select_orphanage() -> Generator[model.Orphanage]:
        data = await Database._select("SELECT * FROM orphanage")
        if data is not None and len(data) != 0:
            return (model.Orphanage(*v) for v in data)
        return ()

    @staticmethod
    async def select_orphanage_sid(server_id:int) -> Generator[model.Orphanage]:
        data = await Database._select("SELECT * FROM orphanage WHERE server_id=?",(server_id,))
        if data is not None and len(data) != 0:
            return (model.Orphanage(*v) for v in data)
        return ()

    @staticmethod
    async def insert_orphanage(channel_id: int, message_id: int, role_id: int, tier: int, active: int,server_id:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO orphanage VALUES(?,?,?,?,?,?)",
                (
                    channel_id,
                    role_id,
                    tier,
                    active,
                    message_id,
                    server_id,
                ),
            )
            return True
        except IntegrityError:
            return False


    @staticmethod
    async def update_orphanage_sid(channel_id: int, tier: int, server_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE orphanage SET server_id=? WHERE channel_id=? AND tier=?",
                (
                    server_id,
                    channel_id,
                    tier,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_orphanage_active(channel_id: int, tier: int, active: int) -> bool:
        try:
            await Database._insert(
                "UPDATE orphanage SET active=? WHERE channel_id=? AND tier=?",
                (
                    active,
                    channel_id,
                    tier,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_orphanage_msg_id(
        channel_id: int, tier: int, message_id: int
    ) -> bool:
        try:
            await Database._insert(
                "UPDATE orphanage SET message_id=? WHERE channel_id=? AND tier=?",
                (
                    message_id,
                    channel_id,
                    tier,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_orphanage(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM orphanage WHERE channel_id=?", (channel_id,)
        )

    ## requirements
    @staticmethod
    async def select_requirements(guild_id: int) -> model.Requirements | None:
        data = await Database._select(
            "SELECT * FROM requirements WHERE guild_id=?", (guild_id,)
        )
        if data is not None and len(data) != 0:
            return model.Requirements(*data[0])
        return None

    @staticmethod
    async def insert_requirements(
        guild_id: int, days: int, levels: int, npc: int, pvp: int, steps: int
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO requirements VALUES(?,?,?,?,?,?)",
                (
                    guild_id,
                    days,
                    levels,
                    npc,
                    pvp,
                    steps,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_requirements(guild_id: int) -> None:
        await Database._insert("DELETE FROM requirements WHERE guild_id=?", (guild_id,))

    ## rewards
    @staticmethod
    async def select_reward(guild_id: int) -> model.Rewards | None:
        data = await Database._select(
            "SELECT * FROM rewards WHERE guild_id=?", (guild_id,)
        )
        if data is not None and len(data) != 0:
            return model.Rewards(*data[0])
        return None

    @staticmethod
    async def insert_reward(
        guild_id: int, gold: int, x_days: int, year: int, month: int, day: int
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO rewards VALUES(?,?,?,?,?,?)",
                (
                    guild_id,
                    gold,
                    x_days,
                    year,
                    month,
                    day,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_reward(guild_id: int) -> None:
        await Database._insert("DELETE FROM rewards WHERE guild_id=?", (guild_id,))

    ## monthly reward
    @staticmethod
    async def select_monthly_reward() -> Generator[model.MonthlyRewards]:
        data = await Database._select("SELECT * FROM monthly_reward")
        if data is not None and len(data) != 0:
            return (model.MonthlyRewards(*v) for v in data)
        return ()

    @staticmethod
    async def select_monthly_reward_sid(server_id:int) -> Generator[model.MonthlyRewards]:
        data = await Database._select("SELECT * FROM monthly_reward WHERE server_id=?",(server_id,))
        if data is not None and len(data) != 0:
            return (model.MonthlyRewards(*v) for v in data)
        return ()

    @staticmethod
    async def insert_monthly_reward(role_id: int, channel_id: int,server_id:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO monthly_reward VALUES(?,?,?)",
                (
                    role_id,
                    channel_id,
                    server_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_monthly_reward_sid(channle_id: int, server_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE monthly_reward SET server_id=? WHERE channel_id=?",
                (
                    server_id,
                    channle_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_monthly_reward(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM monthly_reward WHERE channel_id=?", (channel_id,)
        )

    ## diamonds
    @staticmethod
    async def select_diamonds() -> Generator[model.Diamond]:
        data = await Database._select("SELECT * FROM diamonds")
        if data is not None and len(data) != 0:
            return (model.Diamond(*v) for v in data)
        return ()

    @staticmethod
    async def select_diamonds_sid(server_id:int) -> Generator[model.Diamond]:
        data = await Database._select("SELECT * FROM diamonds WHERE server_id=?",(server_id,))
        if data is not None and len(data) != 0:
            return (model.Diamond(*v) for v in data)
        return ()

    @staticmethod
    async def insert_diamonds(role_id: int, channel_id: int, min_price: int,server_id:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO diamonds VALUES(?,?,?,'',?)",
                (
                    role_id,
                    channel_id,
                    min_price,
                    server_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_diamonds_sid(server_id: int, channle_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE diamonds SET server_id=? WHERE channel_id=?",
                (
                    server_id,
                    channle_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_diamonds(last_min_price: str, channle_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE diamonds SET last_min_price=? WHERE channel_id=?",
                (
                    last_min_price,
                    channle_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_diamonds(channel_id: int) -> None:
        await Database._insert("DELETE FROM diamonds WHERE channel_id=?", (channel_id,))

    ## safe user
    @staticmethod
    async def select_safe_user(guild_id: int) -> Generator[model.SafeUser]:
        data = await Database._select(
            "SELECT * FROM safe_user WHERE guild_id=?", (guild_id,)
        )
        if data is not None and len(data) != 0:
            return (model.SafeUser(*v) for v in data)
        return data

    @staticmethod
    async def insert_safe_user(smmo_id: int, guild_id: int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO safe_user VALUES(?,?)",
                (
                    smmo_id,
                    guild_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_safe_user(smmo_id: int, guild_id: int) -> None:
        await Database._insert(
            "DELETE FROM safe_user WHERE smmo_id=? AND guild_id=?",
            (
                smmo_id,
                guild_id,
            ),
        )

    ## worldboss
    @staticmethod
    async def select_worldboss(timestamp: int) -> Generator[model.WorldBoss]:
        data = await Database._select(
            "SELECT * FROM worldboss WHERE enable_time >= ? ORDER BY enable_time ASC",
            (timestamp,),
        )
        if data is not None and len(data) != 0:
            return (model.WorldBoss(*v) for v in data)
        return ()

    @staticmethod
    async def select_all_worldboss() -> Generator[model.WorldBoss]:
        data = await Database._select("SELECT * FROM worldboss")
        if data is not None and len(data) != 0:
            return (model.WorldBoss(*v) for v in data)
        return ()

    @staticmethod
    async def insert_worldboss(
        id: int,
        name: str,
        avatar: str,
        level: int,
        god: int,
        strength: int,
        defence: int,
        dexterity: int,
        current_hp: int,
        max_hp: int,
        enable_time: int,
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO worldboss VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    id,
                    name,
                    avatar,
                    level,
                    god,
                    strength,
                    defence,
                    dexterity,
                    current_hp,
                    max_hp,
                    enable_time,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_all_worldboss() -> None:
        await Database._insert("DELETE FROM worldboss")

    ## gains leaderboard
    @staticmethod
    async def select_all_gains_leaderboard() -> Generator[model.GainsLeaderboard]:
        data = await Database._select("SELECT * FROM gains_leaderboard")
        if data is not None and len(data) != 0:
            return (model.GainsLeaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def select_gains_leaderboard_sid(server_id: int) -> Generator[model.GainsLeaderboard]:
        data = await Database._select("SELECT * FROM gains_leaderboard WHERE server_id=?", (server_id,))
        if data is not None and len(data) != 0:
            return (model.GainsLeaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def select_gains_leaderboard(
        channel_id: int,
    ) -> Generator[model.GainsLeaderboard]:
        data = await Database._select(
            "SELECT * FROM gains_leaderboard WHERE channel_id=?", (channel_id,)
        )
        if data is not None and len(data) != 0:
            return (model.GainsLeaderboard(*v) for v in data)
        return ()

    @staticmethod
    async def insert_gains_leaderboard(channel_id: int, message_id: int,server_id:int,timeframe:str,timestamp:int) -> bool:
        try:
            await Database._insert(
                "INSERT INTO gains_leaderboard VALUES(?,?,?,?,?)",
                (
                    channel_id,
                    message_id,
                    server_id,
                    timeframe,
                    timestamp
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_gains_leaderboard_sid(channel_id: int, server_id: int) -> bool:
        try:
            await Database._insert(
                "UPDATE gains_leaderboard SET server_id=? WHERE channel_id=?",
                (
                    server_id,
                    channel_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def update_gains_leaderboard(channel_id: int, timestamp:int, old_message_id: int, message_id:int) -> bool:
        try:
            await Database._insert(
                "UPDATE gains_leaderboard SET message_id=?, timestamp=? WHERE channel_id=? AND message_id=?",
                (
                    message_id,
                    timestamp,
                    channel_id,
                    old_message_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_gains_leaderboard(channel_id: int) -> None:
        await Database._insert(
            "DELETE FROM gains_leaderboard WHERE channel_id=?", (channel_id,)
        )

    ## raid
    @staticmethod
    async def select_all_raid() -> Generator[model.Raid]:
        data = await Database._select("SELECT * FROM raid")
        if data is not None and len(data) != 0:
            return (model.Raid(*v) for v in data)
        return ()

    @staticmethod
    async def insert_raid(
        channel_id: int, time: int, duration: int, role_id: int
    ) -> bool:
        try:
            await Database._insert(
                "INSERT INTO raid VALUES(?,?,?,?)",
                (
                    channel_id,
                    time,
                    duration,
                    role_id,
                ),
            )
            return True
        except IntegrityError:
            return False

    @staticmethod
    async def delete_raid(channel_id: int) -> None:
        await Database._insert("DELETE FROM raid WHERE channel_id=?", (channel_id,))
