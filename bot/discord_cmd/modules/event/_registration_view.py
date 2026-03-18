import discord
from bot.discord_cmd.helpers import helpers 
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database 
from datetime import datetime

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.user_registered = 0
        if self.message is not None:
            if len(self.message.embeds) != 0:
                self.name = self.message.embeds[0].title
                self.desc = self.message.embeds[0].description
                self.custom_image = self.message.embeds[0].image.url
                self.custom_thumbnail = self.message.embeds[0].thumbnail.url
                self.author_name = self.message.embeds[0].author.name
                self.author_icon = self.message.embeds[0].author.icon_url
                self.template = self.parse_values_npart(self.message.embeds[0].fields[1].value)
                self.event_id = self.parse_values_id(self.message.embeds[0].fields[0].value)


    async def send(self, ctx: discord.Interaction):
        await ctx.followup.send(view=self)
        if not await Database.update_event(self.event_id,self.s_year,self.s_month,self.s_day,int(self.s_date),ctx.guild_id,self.e_year,self.e_month,self.e_day,int(self.e_date),self.name,self.desc,self.event_formula,int(self.guildies_only),self.team_size,self.message.id,ctx.channel_id):
            logger.error("Could not update the event: %s",self.name)
        await self.update_message()
        
    async def update_message(self):
        await self.message.edit(embed=await self.create_embed(), view=self)

    async def create_embed(self):
        try:
            emb = helpers.Embed(title=self.name, description=self.desc, 
                                image=self.custom_image,
                                thumbnail=self.custom_thumbnail,
                                color=0x11ac4d)
            emb.add_field(name="Event Info",
                        value=f"**Starting date**: <t:{int(self.s_date)}>\n"
                                f"**Ending date**: <t:{int(self.e_date)}>\n"
                                f"**Event Formula**: `{self.event_formula.upper()}`\n"
                                f"**Participants**: {"Guild Members only" if self.guildies_only else "Open to all"}\n"
                                f"**Teams size**: {self.team_size}\n"
                                f"**Event ID**: `{self.event_id}`",
                                inline=False
                        )
            emb.add_field(name="",value=f"Registered users: {self.user_registered:,}",inline=False)
            emb.add_field(name="_________",
                        value=f"You need to be registered to the bot, this can be done by using `/user verify` and following the instructions of that command.",
                        inline=False
                        )
            emb.set_author(name=self.author_name,icon_url=self.author_icon)
        except AttributeError:
            await self.init_vars()
            emb = helpers.Embed(title=self.name, description=self.desc, 
                                image=self.custom_image,
                                thumbnail=self.custom_thumbnail,
                                color=0x11ac4d)
            emb.add_field(name="Event Info",value=self.message.embeds[0].fields[0].value,inline=False)
            emb.add_field(name="",value=self.template.format(n_part=self.user_registered),inline=False)
            emb.add_field(name="_________",
                        value=f"You need to be registered to the bot, this can be done by using `/user verify` and following the instructions of that command.",
                        inline=False
                        )
            emb.set_author(name=self.author_name,icon_url=self.author_icon)
        return emb

    @discord.ui.button(label="Join Event", style=discord.ButtonStyle.green,custom_id="join-event-btn")
    async def join_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.init_vars()
        if datetime.now().timestamp() > self.e_date:
            button.disabled = True
            return await interaction.followup.send("Event Ended",ephemeral=True)
        player = await helpers.get_user(user=interaction.user)
        if player is None:
            return await interaction.followup.send("You are not linked in the bot. Use '/user verify' to link.",ephemeral=True)
        if not await Database.insert_event_partecipant(player.id,player.name,interaction.user.id,self.event_id,""):
            return await interaction.followup.send("You already joined the event",ephemeral=True)
        self.user_registered = await Database.select_counter_event_user_partecipants(self.event_id)
        await self.update_message()
        await interaction.followup.send("Successfully Registered.",ephemeral=True)

    async def init_vars(self) -> None:
        if len(self.message.embeds) != 0:
            self.name = self.message.embeds[0].title
            self.desc = self.message.embeds[0].description
            self.custom_image = self.message.embeds[0].image.url
            self.custom_thumbnail = self.message.embeds[0].thumbnail.url
            self.author_name = self.message.embeds[0].author.name
            self.author_icon = self.message.embeds[0].author.icon_url
            self.template = self.parse_values_npart(self.message.embeds[0].fields[1].value)
            self.event_id = self.parse_values_id(self.message.embeds[0].fields[0].value)
            self.s_date,self.e_date = self.parse_values_dates(self.message.embeds[0].fields[0].value)
            self.user_registered = await Database.select_counter_event_user_partecipants(self.event_id)

    @staticmethod
    def parse_values_npart(data:str) -> str:
        lines = data.split(":")
        lines[1] = " {n_part}"
        return ":".join(lines)

    @staticmethod
    def parse_values_id(data:str) -> int:
        lines = data.split("\n")
        id_evt = lines[5].split(":")[1].split("`")[1]
        return int(id_evt)
    
    @staticmethod
    def parse_values_dates(data:str) -> tuple[int,int]:
        b = data.split("\n")
        s = b[0].split(":")[2]
        e = b[1].split(":")[2]
        return int(s[:-1]),int(e[:-1])