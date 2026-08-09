from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class UserStat:
    smmo_id: int
    year: int
    month: int
    day: int
    time: int
    level: int
    steps: int
    npc_kills: int
    user_kills: int
    quests_performed: int
    bounties_completed: int
    reputation: int
    chests_opened: int

@dataclass(slots=True, frozen=True)
class DeleteMessage:
        msg_id: int
        chn_id: int
        time: int

@dataclass(slots=True, frozen=True)
class Statistics:
        id: str
        time_used: int
        average_time: float
