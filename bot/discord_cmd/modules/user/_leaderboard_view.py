import discord
from bot.discord_cmd.helpers import helpers 

class LeaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    separator: int = 10

    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.type = 0
        self.message = await ctx.followup.send(view=self)
        await self.update_message(self.data[self.type][:self.separator])


    async def update_message(self, data):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(data), view=self)
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



    async def create_embed(self, data):
        TITLE = ["Steps","NPC Kills","PVP Kills","Levels Gains"]
        position = 0
        your_value = 0
        msg = ""
        for usr,i in zip(self.data[self.type],range(1,len(self.data[self.type])+1)):
            if position == 0:
                position = i if usr.smmo_id == self.user_id else 0
                if self.type == 0:
                    your_value = usr.steps if usr.smmo_id == self.user_id else 0
                elif self.type == 1:
                    your_value = usr.npc if usr.smmo_id == self.user_id else 0
                elif self.type == 2:
                    your_value = usr.pvp if usr.smmo_id == self.user_id else 0
                elif self.type == 3:
                    your_value = usr.levels if usr.smmo_id == self.user_id else 0
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
            msg += f"#{i} [{usr.name}](https://simple-mmo.com/user/view/{usr.smmo_id}): **{value:,}** <t:{int(usr.date-86400)}>-<t:{int(usr.date)}>\n"
        # TODO: betterfix
        if len(msg) > 1024:
            msg = ""
            for usr,i in zip(self.data[self.type],range(1,len(self.data[self.type])+1)):
                if position == 0:
                    position = i if usr.smmo_id == self.user_id else 0
                    if self.type == 0:
                        your_value = usr.steps if usr.smmo_id == self.user_id else 0
                    elif self.type == 1:
                        your_value = usr.npc if usr.smmo_id == self.user_id else 0
                    elif self.type == 2:
                        your_value = usr.pvp if usr.smmo_id == self.user_id else 0
                    elif self.type == 3:
                        your_value = usr.levels if usr.smmo_id == self.user_id else 0
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
                msg += f"#{i} {usr.name}: **{value:,}** <t:{int(usr.date-86400)}>-<t:{int(usr.date)}>\n"
        emb = helpers.Embed(title=f"{TITLE[self.type]} Leaderboard",description=f"You are placed #{position}/{len(self.data[self.type])} ({your_value:,})")
        emb.add_field(name="", 
                      value=msg, 
                      inline=False)
        if position != 0:
            emb.set_footer(text=f"Data limited to the database")
        return emb
    
    @discord.ui.button(label="Steps", emoji="🥾", style=discord.ButtonStyle.primary)
    async def step_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 0
        await self.update_message(self.data[self.type][:self.separator])

    @discord.ui.button(label="NPC Kills", emoji="👾",style=discord.ButtonStyle.primary)
    async def npc_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 1
        await self.update_message(self.data[self.type][:self.separator])

    @discord.ui.button(label="PVP Kills", emoji="💀", style=discord.ButtonStyle.primary)
    async def pvp_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 2
        await self.update_message(self.data[self.type][:self.separator])

    @discord.ui.button(label="Levels Gain", emoji="🔝", style=discord.ButtonStyle.primary)
    async def lvl_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.type = 3
        await self.update_message(self.data[self.type][:self.separator])
    