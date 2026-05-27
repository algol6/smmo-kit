import discord
from discord import SlashCommand,SlashCommandGroup
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.api import SMMOApi
from bot.discord_cmd.modules.trial._helper import send_log, LogType
from bot.core._trial import TrialManager

class BonusModal(discord.ui.Modal):
    def __init__(self, parent_view:discord.ui.View, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parent_view = parent_view
        self.add_item(discord.ui.InputText(label="Time",placeholder="If an activity is completed before this the user can get a bonus."))
        self.add_item(discord.ui.InputText(label="Bonus",placeholder="What the bonus is."))

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.time_bonus = self.children[0].value
        self.parent_view.bonus = self.children[0].value
        
        emb = self.parent_view.create_embed()
        await interaction.response.edit_message(embed=emb, view=self.parent_view)
        

class TrialSetUpView(discord.ui.View):
    def __init__(self):
        self.log_channel_id = None
        self.notify_channel_id = None
        self.entry_channel_id = None
        super().__init__(timeout=None)

    async def send(self, ctx:discord.Interaction):
        await ctx.followup.send(embed=await self.create_embed(),view=self)
        
    async def update_message(self):
        await self.message.edit(embed=await self.create_embed(), view=self)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.name} System Configuration")

        emb.add_field(
            name="Notify channel",
            value=f"If this get selected from the list below it will use that channel to ping the user when they complete a task.\nChannel Used: {f'<#{self.notify_channel_id}>' if self.notify_channel_id else 'Not Set'}",
            inline=False
        )
        emb.add_field(
            name="Log channel",
            value=f"If this get selected from the list below it will use that channel to send a complete log of the system.\nChannel Used: {f'<#{self.log_channel_id}>' if self.log_channel_id else 'Not Set'}",
            inline=False
        )
        emb.add_field(
            name="Entry channel",
            value=f"If this get selected from the list below it will use that channel to send a message that allow to start the tasks with just a button.\nChannel Used: {f'<#{self.entry_channel_id}>' if self.entry_channel_id else 'Not Set'}",
            inline=False
        )
        return emb

    
    @discord.ui.select(
        row = 0,
        placeholder="Notify Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select1_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        self.notify_channel_id = select.values[0].id
        await self.update_message()


    @discord.ui.select(
        row = 1,
        placeholder="Log Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select2_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        self.log_channel_id = select.values[0].id
        await self.update_message()

    @discord.ui.select(
        row = 2,
        placeholder="Entry Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select3_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        self.entry_channel_id = select.values[0].id
        await self.update_message()

        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,emoji="🗑️",row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        await self.message.delete(delay=1)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,emoji="✔️",row=3)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.edit_original_message(content=
            f"Set up complete. Might take some time before the commands load.\n"
            f"Now you can configure the system with '/{self.name} admin configure'",
            delete_after=60,
            embed=None,
            view=None
        )
        
        trial_mng = TrialManager(self.server_id)
        trial_mng.create_trial(self.server_id,True,self.log_channel_id,self.notify_channel_id,self.entry_channel_id,self.guild_id,self.name)
        await trial_mng.save()
        await self.generate_commands(self.client,{self.name:[self.server_id]})
        await send_log(
            self.client,self.server_id,LogType.TRIAL_CREATION,
            value=self.name,
            usr1=self.author_id
        )

