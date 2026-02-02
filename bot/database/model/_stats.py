from dataclasses import dataclass

@dataclass
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
    quest_performed: int
    bounties_completed: int
    reputation: int
    chests_opened: int
    
@dataclass
class DeleteMessage:
        msg_id: int
        chn_id: int
        time: int

@dataclass
class Statistics:
        id: str
        time_used: int
        average_time: float