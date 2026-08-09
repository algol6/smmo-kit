from dataclasses import dataclass, field

@dataclass(slots=True, frozen=True)
class ShortGuildInfo:
    id: int = field(default_factory=None)
    name: str = field(default_factory=None)


@dataclass(slots=True, frozen=True)
class GuildMemberInfo:
    user_id: int = field(default_factory=None)
    position: str = field(default_factory=None)
    name: str = field(default_factory=None)
    level: int = field(default_factory=None)
    safe_mode: bool = field(default_factory=None)
    banned: bool = field(default_factory=None)
    current_hp: int = field(default_factory=None)
    max_hp: int = field(default_factory=None)
    warrior: bool = field(default_factory=None)
    steps: int = field(default_factory=None)
    npc_kills: int = field(default_factory=None)
    user_kills: int = field(default_factory=None)
    last_activity: int = field(default_factory=None)


@dataclass(slots=True, frozen=True)
class GuildInfo:
    id: int
    name: str
    tag: str
    owner: int
    exp: int
    current_season_exp: int
    passive: bool
    icon: str
    legacy_exp: int
    member_count: int
    eligible_for_guild_war: bool
    members: list[GuildMemberInfo] = field(default_factory=list)

@dataclass(slots=True, frozen=True)
class TaxContribution:
    guild_bank: int
    sanctuary: int

@dataclass(slots=True, frozen=True)
class GuildMemberContribution:
    user_id: int
    gold_deposited: int
    power_points_deposited: int
    pve_kills: int
    pve_exp: int
    pvp_kills: int
    pvp_exp: int
    steps_taken: int
    steps_experience: int
    nodes_gathered: int
    nodes_experience: int
    tax_contribution: TaxContribution
