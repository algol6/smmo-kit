from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Task:
    item_type:str
    current_amount:int
    target_amount:int
    exp_reward:int
    power_point_reward:int
