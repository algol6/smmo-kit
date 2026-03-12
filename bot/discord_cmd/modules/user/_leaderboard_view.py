import discord
from bot.discord_cmd.helpers import helpers 

class LeaderboardView(discord.ui.View):
    def __init__(self):
        self.TITLE = ["Steps","NPC Kills","PVP Kills","Levels Gains"]
        self.TEMPLATE = "#{pos} [{name}](https://simple-mmo.com/user/view/{id}): **{value:,}** <t:{sdate}:D>"
        super().__init__(timeout=None)

    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.type = 0
        self.message = await ctx.followup.send(view=self)
        await self.update_message()


    async def update_message(self):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(), view=self)
        except discord.errors.Forbidden:
            await self.ctx.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")

    async def update_buttons(self):
        if self.type == 0:
            self.step_button.disabled = True
            self.npc_button.disabled = False
            self.pvp_button.disabled = False
            self.lvl_button.disabled = False
        elif self.type == 1:
            self.step_button.disabled = False
            self.npc_button.disabled = True
            self.pvp_button.disabled = False
            self.lvl_button.disabled = False
        elif self.type == 2:
            self.step_button.disabled = False
            self.npc_button.disabled = False
            self.pvp_button.disabled = True
            self.lvl_button.disabled = False
        elif self.type == 3:
            self.step_button.disabled = False
            self.npc_button.disabled = False
            self.pvp_button.disabled = False
            self.lvl_button.disabled = True

    def generate_msg(self):
        position = 0
        your_value = 0
        msgs = []
        for i,usr in enumerate(self.data[self.type],start=1):
            if position == 0:
                if usr.smmo_id == self.user_id:
                    position = i
                    if self.type == 0:
                        your_value = usr.steps
                    elif self.type == 1:
                        your_value = usr.npc
                    elif self.type == 2:
                        your_value = usr.pvp
                    elif self.type == 3:
                        your_value = usr.levels
            if i>10:
                continue
            if self.type == 0:
                value = usr.steps
            elif self.type == 1:
                value = usr.npc
            elif self.type == 2:
                value = usr.pvp
            elif self.type == 3:
                value = usr.levels
            msgs.append(self.TEMPLATE.format(pos=i,name=usr.name,id=usr.smmo_id,value=value,sdate=int(usr.date-86400)))
            if position<=10 and position == i:
                msgs[-1] = msgs[-1] + " :arrow_left:"
        return position,your_value,msgs
    
    async def create_embed(self):
        your_pos,your_val,msg = self.generate_msg()
        desc = f"You are placed #{your_pos}/{len(self.data[self.type])}\nYour stat: {your_val:,}" if your_pos > 10 else ""
        emb = helpers.Embed(title=f"{self.TITLE[self.type]} Leaderboard",description=desc)
        emb.add_field(name="", 
                      value="\n".join(msg[:5]), 
                      inline=False)
        emb.add_field(name="", 
                      value="\n".join(msg[5:]), 
                      inline=False)
        if your_pos != 0:
            emb.set_footer(text=f"Data limited to the database")
        return emb
    
    @discord.ui.button(label="Steps", emoji="🥾", style=discord.ButtonStyle.primary)
    async def step_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 0
        await self.update_message()

    @discord.ui.button(label="NPC Kills", emoji="👾",style=discord.ButtonStyle.primary)
    async def npc_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 1
        await self.update_message()

    @discord.ui.button(label="PVP Kills", emoji="💀", style=discord.ButtonStyle.primary)
    async def pvp_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 2
        await self.update_message()

    @discord.ui.button(label="Levels Gain", emoji="🔝", style=discord.ButtonStyle.primary)
    async def lvl_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 3
        await self.update_message()
    