import discord
from pandas.core.generic import ValueKeyFunc
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi

class RequirementsModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Days",placeholder="Write just the number. ex: 7"))
        self.add_item(discord.ui.InputText(label="Steps",placeholder="Leave empty to skip",required=False))
        self.add_item(discord.ui.InputText(label="NPCs",placeholder="Leave empty to skip.",required=False))
        self.add_item(discord.ui.InputText(label="PVPs",placeholder="Leave empty to skip.",required=False))
        self.add_item(discord.ui.InputText(label="Levels",placeholder="Leave empty to skip.",required=False))
        self.days = 0
        self.steps = 0
        self.npc = 0
        self.pvp = 0
        self.lvl = 0

    async def callback(self, interaction: discord.Interaction):
        self.modal_interaction = interaction
        await interaction.response.defer(ephemeral=True)
        try:
            self.days = int(self.children[0].value or 0)
            self.steps = int(self.children[1].value or 0)
            self.npc = int(self.children[2].value or 0)
            self.pvp = int(self.children[3].value or 0)
            self.lvl = int(self.children[4].value or 0)
        except ValueError:
            pass
        self.stop()

class ConfMonitor(discord.ui.View):
    def __init__(self,server_id:int|None,guild_id:int,client):
        super().__init__(timeout=None)
        self.sid = server_id
        self.gid = guild_id
        self.client = client
        self.ch = None
        self.conf = (None,None)

        self.TEMPLATE = (
            "Monitors Set:",
            "Requisites:",
            "<#{chid}>",
            "Steps: {step:,}\nNPCs: {npc:,}\nPVPs: {pvp:,}\nLvls: {lvl:,}\nIn {days:,} days."
        )

    async def load_conf(self):
        self.conf = (
            tuple(await Database.select_monitors_config_by_server_id(self.sid)),
            (await Database.select_requirements(self.gid),)
        )

    async def send(self, ctx:discord.ApplicationContext):
        await self.load_conf()
        self.update_btn()
        await ctx.followup.send(embed=await self.create_embed(),view=self)

    def update_btn(self):
        self.confirm_button.disabled = self.ch is None
        self.delete_button.disabled = self.conf[0] is None or len(self.conf[0]) == 0
        self.set_r_button.disabled = self.conf[1] is not None and self.conf[1][0] is not None
        self.rm_r_button.disabled = self.conf[1] is None or self.conf[1][0] is None

    async def update_message(self, interaction:discord.Interaction):
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title="Configure Monitoring System",description="")
        emb.add_field(
            name="Guild Requirements",
            value="Set guild requirements.\nDays indicate how long it takes to meet the requirements.\nThe Steps are... well... the steps to be done in x days, same thing with NPCs, PVP and Levels",
            inline=False
        )
        emb.add_field(
            name="Channel",
            value="Used to send a message with a live monitoring of the guild, showing who doesn't meet the requirements.",
            inline=False
        )
        emb.add_field(
            name="",
            value="",
            inline=False
        )
        if self.conf is not None:
            for i,c in enumerate(self.conf):
                if c is None or len(c) == 0:
                    continue
                fmsg = ""
                for x in c:
                    if x is None:
                        continue
                    match i:
                        case 0:
                            msg = self.TEMPLATE[i+(len(self.TEMPLATE)//2)].format(chid=x.channel_id)
                        case 1:
                            msg = self.TEMPLATE[i+(len(self.TEMPLATE)//2)].format(step=x.steps,npc=x.npc,pvp=x.pvp,lvl=x.levels,days=x.days)
                        case _:
                            msg = ""
                    fmsg += msg + "\n"
                emb.add_field(
                    name=self.TEMPLATE[i],
                    value=fmsg,
                    inline=False
                )
        return emb

    @discord.ui.select(
        row = 0,
        placeholder="Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select0_callback(self, select, interaction):
        await interaction.response.defer()
        self.ch = select.values[0]
        await self.update_message(interaction)

    @discord.ui.button(label="Remove Requirements", style=discord.ButtonStyle.blurple,row=1)
    async def rm_r_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        await interaction.response.defer()

        await Database.delete_requirements(self.gid)
        await interaction.followup.send(content="Requirements removed, if there were any.",ephemeral=True)

        await self.load_conf()
        await self.update_message(interaction)

    @discord.ui.button(label="Set Requirements", style=discord.ButtonStyle.blurple,row=1)
    async def set_r_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        modal = RequirementsModal(title="Set Guild Requirements")
        await interaction.response.send_modal(modal)
        await modal.wait()
        await Database.insert_requirements(self.gid,modal.days,modal.lvl,modal.npc,modal.pvp,modal.steps)
        await interaction.followup.send(content="Requirements Updated.",ephemeral=True)

        await self.load_conf()
        await self.update_message(interaction)
        await modal.modal_interaction.edit_original_response(embed=await self.create_embed(),view=self)


    @discord.ui.button(label="Exit", style=discord.ButtonStyle.red,row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=helpers.Embed(title="Operation cancelled"),view=None)

    @discord.ui.button(label="Delete Message", style=discord.ButtonStyle.red,disabled=True,emoji="🗑️",row=2)
    async def delete_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.load_conf()

        await Database.delete_monitor_config(self.ch)
        await interaction.followup.send(content="Message removed, if there were any.",ephemeral=True)



    @discord.ui.button(label="Add Message", style=discord.ButtonStyle.green,emoji="✔️",disabled=True,row=2)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()

        try:
            channel = await self.client.fetch_channel(self.ch.id)
            await channel.send(content="test message.", delete_after=1)
        except discord.Forbidden:
            return await interaction.followup.send(content="Bot doesn't have the perms to see/write the channel.", ephemeral=True)
        message = await channel.send(content="May take up to one hour to show the message")
        error = not await Database.insert_monitors_config(self.sid,self.ch.id,self.gid,message.id)

        self.ch = None

        if error:
            await interaction.followup.send(content="Message already set, remove it before setting up a new one.")
            await message.delete()
        else:
            await interaction.followup.send(content="Set up complete.", ephemeral=True)

        await self.load_conf()
        await self.update_message(interaction)
