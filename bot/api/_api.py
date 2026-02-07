from bot.discord_cmd.helpers.logger import logger
from asyncio import sleep, Semaphore
from os import getenv
from time import time
from aiohttp import ClientSession
import bot.api.model as model

class ApiError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"ApiError: {self.message}"
    
sem = Semaphore(1)
class SMMOApi:
    _API_URL: str = "https://api.simple-mmo.com/"
    _API_TOKEN: str = getenv("SMMO_TOKEN")
    rate_limit_remaining: int = 0
    _first_request_time: float = 0.0
    @staticmethod
    async def _request(endpoint:str,api_key:str=None) -> dict | list | None:
        async with sem:
            if SMMOApi.rate_limit_remaining <= 0 and SMMOApi._first_request_time > 0.0:
                await sleep(60)
                SMMOApi._first_request_time = 0.0
            async with ClientSession() as session:
                async with session.post(
                    url=f"{SMMOApi._API_URL}{endpoint.lstrip('/')}",
                    data={
                        "api_key": api_key if api_key is not None else SMMOApi._API_TOKEN
                    }
                ) as resp:
                    if not resp.ok:
                        import re
                        result = re.search('<title>(.*)</title>', await resp.text())
                        if result:
                            result=result.group(1)
                        ## TODO: return a message error to let know is a server problem
                        if not result:
                            result = await resp.text()
                        logger.error(result)
                        raise ApiError(result)
                    if "X-RateLimit-Remaining" in resp.headers:
                        SMMOApi.rate_limit_remaining = int(resp.headers.get("X-RateLimit-Remaining"))
                        if SMMOApi._first_request_time == 0.0:
                            SMMOApi._first_request_time = time()

                    return SMMOApi._fix_fucking_names(await resp.json())

    @staticmethod
    def _fix_fucking_names(obj: dict | list) -> dict | list | None:
        name_replacements = {
            "def": "defence",
            "str": "strength",
            "dex": "dexterity",
            "type": "item_type"
        }

        if type(obj) is dict:
            if "error" in obj:
                return None
            result: dict = {}

            for k, v in obj.items():
                result[k] = v

                if type(v) is dict:
                    v = SMMOApi._fix_fucking_names(obj[k])
                    result[k] = v

                if k in name_replacements:
                    new_key = name_replacements[k]
                    result[new_key] = v
                    del result[k]

            if 'motto' in result and not 'guild' in result:
                result["guild"] = {"id":None,"name":None}

            return result
        else:
            result: list = []

            for v in obj:
                if type(v) is dict:
                    v = SMMOApi._fix_fucking_names(v)
                    result.append(v)

            return result

    @staticmethod
    async def get_me(api_key: str) -> model.SelfPlayerInfo | None:
        resp = await SMMOApi._request(f"v1/player/me",api_key)
        if resp is not None:
            return model.SelfPlayerInfo(**resp)
        return None

    @staticmethod
    async def get_player_info(player_id: str) -> model.PlayerInfo | None:
        resp = await SMMOApi._request(f"v1/player/info/{player_id}")
        if resp is not None:
            return model.PlayerInfo(**resp)

        return None

    @staticmethod
    async def get_player_equipment(player_id: str) -> tuple[model.Equipment]:
        resp = await SMMOApi._request(f"v1/player/equipment/{player_id}")
        if resp is not None:
            return (model.Equipment(**v) for k, v in resp.items())

        return ()

    @staticmethod
    async def get_player_skills(player_id: str) -> tuple[model.Skill]:
        resp = await SMMOApi._request(f"v1/player/skills/{player_id}")
        if resp is not None:
            return (model.Skill(**v) for v in resp)

        return ()

    @staticmethod
    async def get_diamond_market() -> tuple[model.DiamondMarketEntry]:
        resp = await SMMOApi._request(f"v1/diamond-market")
        if resp is not None and type(resp) is list:
            return (model.DiamondMarketEntry(**v) for v in resp)

        return ()

    @staticmethod
    async def get_orphanage() -> tuple[model.OrphanageEntry]:
        resp = await SMMOApi._request(f"v2/orphanage")
        if resp is not None and type(resp) is list:
            return (model.OrphanageEntry(**v) for v in resp)
        return ()

    @staticmethod
    async def get_world_bosses() -> tuple[model.Boss]:
        resp = await SMMOApi._request(f"v1/worldboss/all")
        if resp is not None and type(resp) is list:
            return (model.Boss(**v) for v in resp)

        return []

    @staticmethod
    async def get_item_info(item_id: str) -> model.ItemInfo | None:
        resp = await SMMOApi._request(f"v1/item/info/{item_id}")
        if resp is not None:
            return model.ItemInfo(**resp)

        return None

    @staticmethod
    async def get_guild_info(guild_id: int) -> model.GuildInfo | None:
        resp = await SMMOApi._request(f"v1/guilds/info/{guild_id}")
        if resp is not None:
            return model.GuildInfo(**resp)

        return None

    @staticmethod
    async def get_guild_members(guild_id: int) -> tuple[model.GuildMemberInfo]:
        resp = await SMMOApi._request(f"v1/guilds/members/{guild_id}")
        if resp is not None and type(resp) is list:
            return (model.GuildMemberInfo(**v) for v in resp)

        return ()

    @staticmethod
    async def get_guild_member_contribution(guild_id: int, user_id: int, api_key:str=None) -> model.GuildMemberContribution | None:
        resp = await SMMOApi._request(f"v1/guilds/members/{guild_id}/contribution/{user_id}", api_key)
        if resp is not None:
            return model.GuildMemberContribution(**resp)

        return None

    @staticmethod
    async def get_guild_season() -> tuple[model.Season]:
        resp = await SMMOApi._request("v1/guilds/seasons")
        if resp is not None and type(resp) is list:
            return (model.Season(**v) for v in resp)
        
        return ()
    
    @staticmethod
    async def get_guild_season_leaderboard(season_id: int) -> tuple[model.GuildSeasonLeaderboard]:
        resp = await SMMOApi._request(f"v1/guilds/seasons/{season_id}")
        if resp is not None and type(resp) is list:
            return (model.GuildSeasonLeaderboard(**v) for v in resp)
        
        return ()
    
    @staticmethod
    async def get_guild_wars(guild_id: int, status_id: int) -> tuple[model.Wars]:
        resp = await SMMOApi._request(f"v1/guilds/wars/{guild_id}/{status_id}")
        if resp is not None and type(resp) is list:
            return (model.Wars(**v) for v in resp)
        
        return ()
    
    @staticmethod
    async def get_task(guild_id:int) -> model.Task | None:
        resp = await SMMOApi._request(f"v1/guilds/task/{guild_id}")
        if resp is not None and len(resp) != 0:
            return model.Task(**resp)
        return None