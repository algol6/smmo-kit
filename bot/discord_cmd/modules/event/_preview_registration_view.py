import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.modules.event._registration_view import RegistrationView
from bot.database import Database
from bot.api import SMMOApi

from string import digits
from random import choice

class PreviewRegistrationView(discord.ui.View):
    def __init__(self):
        # HOST, HOST GUILD ONLY, GLOBAL (SHARED), LB
        self.checks = [None,None,None,None]
        self.host = [None,None]
        self.guild = None
        self.user_registered = 0
        self.guildies_only = False
        super().__init__(timeout=None)

    async def send(self, ctx:discord.Interaction, content:str=None):
        await ctx.followup.send(content=content,view=self)
        await self.update_message()
        
    async def update_message(self):
        await self.message.edit(embed=await self.create_embed(), view=self)

    async def create_embed(self):
        emb = helpers.Embed(title=f"(Preview) {self.name}", description=self.desc, 
                            image=self.custom_image,
                            thumbnail=self.custom_thumbnail,
                            color=0x11ac4d)
        emb.add_field(name="Event Info",
                    value=f"Starting date: <t:{int(self.s_date.timestamp())}>\n"
                            f"Ending date: <t:{int(self.e_date.timestamp())}>\n"
                            f"Event Formula: `{self.event_formula.upper()}`\n"
                            f"Participants: {"Guild Members only" if self.guildies_only else "Open to all"}\n"
                            f"Teams size: {self.team_size}\n"
                            f"Event ID: `X`",
                            inline=False
                    )
        emb.add_field(name="",value=f"Registered users: {self.user_registered:,}",inline=False)
        emb.add_field(name="_________",
                    value=f"You need to be registered to the bot, this can be done by using `/user verify` and following the instructions of that command.",
                    inline=False
                    )
        if self.host[0] is not None:
            emb.set_author(name=self.host[0],icon_url=self.host[1])
        return emb

    
    @discord.ui.select(
        row = 0,
        placeholder="Select Host",
        options = [
            discord.SelectOption(label="You",description="Show yourself as the Event Host"),
            discord.SelectOption(label="Guild",description="Show your guild as the Event Host"),
            ]
    )
    async def select1_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        if select.values[0] == "You":
            self.children[1].disabled = True
            self.children[0].options[0].default = True
            self.children[0].options[1].default = False
            self.host[0] = self.player.name
            self.host[1] = f"https://simple-mmo.com{self.player.avatar}"
        elif self.player.guild is not None:
            self.children[1].disabled = False
            self.children[0].options[0].default = False
            self.children[0].options[1].default = True
            if self.guild is None:
                self.guild = await SMMOApi.get_guild_info(self.player.guild.id)
            self.host[0] = self.guild.name
            self.host[1] = f"https://simple-mmo.com/img/icons/{self.guild.icon}"
        else:
            await interaction.followup.send(content="You are not in a Guild", ephemeral=True)
            self.children[0].options[0].default = True
            self.children[0].options[1].default = False
            self.children[0].disabled = True
            self.host[0] = self.player.name
            self.host[1] = f"https://simple-mmo.com{self.player.avatar}"
        self.checks[0] = str(select.values[0])
        self.final_check()
        await self.update_message()

    @discord.ui.select(
        row = 1,
        placeholder="Make it only for your guild?",
        disabled=True,
        options = [
            discord.SelectOption(label="Yes",description="Only Your guild mates can join the event"),
            discord.SelectOption(label="No",description="Everyone can join the event"),
            ]
    )
    async def select2_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        if str(select.values[0]) == "Yes":
            self.children[2].disabled = True
            self.children[1].options[0].default = True
            self.children[1].options[1].default = False
            self.guildies_only = True
        else:
            self.children[2].disabled = False
            self.children[1].options[0].default = False
            self.children[1].options[1].default = True
            self.guildies_only = False
        self.checks[1] = str(select.values[0])
        self.final_check()
        await self.update_message()


    @discord.ui.select(
        row = 2,
        placeholder="Make The Event Global?",
        disabled=True,
        options = [
            discord.SelectOption(label="Yes",description="The Event can be seen by the public event list of the bot"),
            discord.SelectOption(label="No",description="Make the event private"),
            ]
    )
    async def select3_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        if select.values[0] == "Yes":
            self.children[2].options[0].default = True
            self.children[2].options[1].default = False
        else:
            self.children[2].options[0].default = False
            self.children[2].options[1].default = True
        self.checks[2] = str(select.values[0])
        
        self.final_check()
        await self.update_message()

    @discord.ui.select(
        row = 3,
        placeholder="Set Up Leaderboard",
        options = [
            discord.SelectOption(label="Yes",description="The Event leaderboard will be set up"),
            discord.SelectOption(label="No",description="No leaderboard will be set up. You can still set up one afterward with '/admin event setup_lb'"),
            ]
    )
    async def select4_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        if select.values[0] == "Yes":
            self.children[3].options[0].default = True
            self.children[3].options[1].default = False
        else:
            self.children[3].options[0].default = False
            self.children[3].options[1].default = True
        self.checks[3] = str(select.values[0])
        self.final_check()
        await self.update_message()


    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,emoji="🗑️")
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,emoji="✔️",disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        is_global = self.checks[2] == "Yes"
        id = int("".join(choice(digits) for _ in range(15)))
        await Database.insert_event(
            self.s_date.year,
            self.s_date.month,
            self.s_date.day,
            int(self.s_date.timestamp()),
            interaction.guild_id,
            self.e_date.year,
            self.e_date.month,
            self.e_date.day,
            int(self.e_date.timestamp()),
            self.name,
            self.desc,
            self.event_formula,
            int(self.guildies_only),
            id,
            interaction.channel_id,
            self.team_size,
            self.custom_image,
            self.custom_thumbnail,
            is_global,
            f"{self.host[0]}:{self.host[1]}",
            self.igguild_id
            )
        event = await Database.select_events_by_message(interaction.guild_id,id)

        view = RegistrationView()
        view.name = self.name
        view.desc = self.desc
        view.custom_image = self.custom_image
        view.custom_thumbnail = self.custom_thumbnail
        view.s_date = self.s_date.timestamp()
        view.s_year = self.s_date.year
        view.s_month = self.s_date.month
        view.s_day = self.s_date.day
        view.e_date = self.e_date.timestamp()
        view.e_year = self.e_date.year
        view.e_month = self.e_date.month
        view.e_day = self.e_date.day
        view.event_formula = self.event_formula
        view.guildies_only = self.guildies_only
        view.team_size = self.team_size
        view.event_id = event.id
        view.author_name = self.host[0]
        view.author_icon = self.host[1]
        await view.send(interaction)
        
        if self.checks[3] == "Yes":
            msg = await interaction.followup.send(content="The Event leaderboar was set.\n The bot will edit this message to show the Leaderboard.")
            if not await Database.insert_event_lb(interaction.channel_id,msg.id,event.id):
                await interaction.followup.send(content="Error on setting up the Event Leaderboard.")
        await self.message.delete()

    def final_check(self):
        if self.checks[0] == "You" and self.checks[3] is not None:
            self.children[5].disabled = False
            return   
        elif self.checks[0] == "Guild":
            if self.checks[1] == "Yes" and self.checks[3] is not None:
                self.children[5].disabled = False
                return
            elif self.checks[1] == "No" and self.checks[2] is not None and self.checks[3] is not None:
                self.children[5].disabled = False
                return  
        self.children[5].disabled = True
