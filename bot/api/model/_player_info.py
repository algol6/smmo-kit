from dataclasses import dataclass, field

from ._guild import ShortGuildInfo
from ._location import Location


@dataclass
class PlayerInfo:
    id: int
    name: str
    avatar: str
    motto: str
    level: int
    profile_number: str
    exp: int
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
    last_activity: int
    max_hp: int
    safeMode: bool
    banned: bool
    background: int
    membership: bool
    tasks_completed: int
    boss_kills: int
    market_trades: int
    reputation: int
    creation_date: str
    bounties_completed: int
    dailies_unlocked: int
    chests_opened: int
    current_location: Location
    guild: ShortGuildInfo  = field(default_factory=None)

    def __post_init__(self):
        self.current_location = Location(**self.current_location)
        self.guild = ShortGuildInfo(**self.guild)
