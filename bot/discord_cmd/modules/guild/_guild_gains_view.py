import discord
from bot.discord_cmd.helpers import helpers
from bot.database import Database
from datetime import datetime, timedelta

class GuildGainsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    current_page: int = 0

    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.message = await ctx.followup.send(view=self)
        await self.update_message()
        

    async def update_message(self):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(), view=self)
        except discord.errors.Forbidden:
            await self.ctx.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")


    async def update_buttons(self):
        if self.current_page == 0:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary

    async def create_embed(self):
        msg: str = ""
        title: list = ["Celestial","Legendary","Epic","Elite","Rare"]
        emb = helpers.Embed(title=f"{self.timeframe} guild gains",
                            description=f"**Stats**: from <t:{int(self.date.timestamp())}> to <t:{int(self.to_date.timestamp() + 86400)}>\n"
                                        f"**Last update**: <t:{self.last_update}:R>\n"
                                        f"**Season**: {self.season.id}\n"
                                        f"**Season Ending**: <t:{int(datetime.fromisoformat(self.season.ends_at[:-1]).timestamp())}>")
        if self.current_page==0:
            for count in range(5):
                for i,g in enumerate(self.season_lb[count*5:5+(count*5)]):
                        s = await Database.select_guild_stats(g.guild["id"], self.date.year,self.date.month,self.date.day,self.season.id)
                        if self.timeframe == "Yesterday":
                            if s is None:
                                msg += "No data"
                                continue
                            temp_date = helpers.get_current_date_game()
                            g_stats = await Database.select_guild_stats(g.guild["id"], temp_date.year,temp_date.month,temp_date.day,self.season.id)
                            if g_stats is not None:
                                g.experience = g_stats.experience
                                g.position = s.position
                        
                        msg = f"{msg}{"\n" if i != 0 else ""}#{g.position} **[{g.guild["name"]}](https://simple-mmo.com/guilds/view/{g.guild["id"]})**: {format(g.experience, ",d")}xp (+*{format(abs((s.experience if s is not None else 0)-g.experience), ",d")}*)"
                        if s is not None:
                            if g.position == s.position:
                                pass
                            elif g.position<s.position:
                                msg = f"{msg} :arrow_up: +{s.position-g.position}"
                            else:
                                msg = f"{msg} :arrow_down: {s.position-g.position}"
                emb.add_field(name=title[count],
                            value=msg,
                            inline=False)
                msg = ""
        else:
            for count in range(5):
                for i,g in enumerate(self.season_lb[25+count*5:30+(count*5)]):
                    s = await Database.select_guild_stats(g.guild["id"], self.date.year,self.date.month,self.date.day,self.season.id)
                    if self.timeframe == "Yesterday":
                        if s is None:
                            msg += "No data"
                            continue
                        temp_date = helpers.get_current_date_game()
                        g_stats = await Database.select_guild_stats(g.guild["id"], temp_date.year,temp_date.month,temp_date.day,self.season.id)
                        if g_stats is not None:
                            g.experience = g_stats.experience
                            g.position = s.position
                    
                    msg = f"{msg}{"\n" if i != 0 else ""}#{g.position} **[{g.guild["name"]}](https://simple-mmo.com/guilds/view/{g.guild["id"]})**: {format(g.experience, ",d")}xp (+*{format(abs((s.experience if s is not None else 0)-g.experience), ",d")}*)"
                    if s is not None:
                        if g.position == s.position:
                            pass
                        elif g.position<s.position:
                            msg = f"{msg} :arrow_up: +{s.position-g.position}"
                        else:
                            msg = f"{msg} :arrow_down: {s.position-g.position}"
                emb.add_field(name="",
                            value=msg,
                            inline=False)
                msg = ""
        emb.set_footer(text="Name Guild: Total GXP (+Daily GXP gained)")
        return emb
            
    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 0
        await self.update_message()


    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        await self.update_message()
