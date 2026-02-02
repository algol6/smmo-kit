from dataclasses import dataclass, field

from ._player_info import ShortGuildInfo
from ._location import Location

@dataclass
class SelfPlayerInfo:
    id: int
    name: str
    level: int
    avatar: str
    motto: str
    profile_number: int
    exp: int
    last_activity: int
    gold: int
    steps: int
    npc_kills: int
    user_kills: int
    quests_complete: int
    quests_performed: int
    dexterity: int
    defence: int
    strength: int
    bonus_dex: int
    bonus_def: int
    bonus_str: int
    hp: int
    max_hp: int
    safeMode: int
    banned: int
    background: int
    membership: int
    tasks_completed: int
    boss_kills: int
    market_trades: int
    reputation: int
    creation_date: str
    bounties_completed: int
    dailies_unlocked: int
    chests_opened: int
    current_location: Location
    quest_points: int
    maximum_quest_points: int
    energy: int
    maximum_energy: int
    total_tasks_complete: int
    diamonds: int
    task_complete_today: str
    safe_mode_time: str
    guild: ShortGuildInfo = field(default_factory=None)
