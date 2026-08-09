from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Trial:
  server_id: int
  enabled: bool
  log_channel_id: int
  notify_channel_id: int
  entry_channel_id: int
  guild_id: int
  name: str

@dataclass(slots=True, frozen=True)
class TrialEntry:
  message_id: int
  channel_id: int
  trial_id: int

@dataclass(slots=True, frozen=True)
class TrialCategory:
  id: int
  trial_id: int
  name: str
  allow_parallel: bool

@dataclass(slots=True, frozen=True)
class TrialTask:
  id: int
  trial_category_id: int
  name: str
  cooldown: int
  reward: str
  point: int
  bonus_time: int
  bonus: str

@dataclass(slots=True, frozen=True)
class TrialTaskRequisite:
  id: int
  trial_task_id: int
  formula: str
  goal: int

@dataclass(slots=True, frozen=True)
class TrialRecord:
  id: int
  trial_task_id: int
  smmo_id: int
  user_id: int
  status: bool
  cancelled: bool
  start_time: int
  end_time: int
  update_time: int
  start_npc: int
  start_steps: int
  start_pvp: int
  start_levels: int
  current_npc: int
  current_steps: int
  current_pvp: int
  current_levels: int

class TrialUser:
  trial_id: int
  smmo_id: int
  points: int
