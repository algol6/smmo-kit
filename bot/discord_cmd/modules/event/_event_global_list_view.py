import discord
from bot.discord_cmd.helpers import helpers
from bot.database import Database

class EventListView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    current_page: int = 1

    async def send(self, ctx: discord.ApplicationContext):
        await ctx.followup.send(embed=await self.create_embed(self.events[self.current_page-1]),view=self)        

    async def update_message(self):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(self.events[self.current_page-1]), view=self)
        except discord.errors.Forbidden:
            await self.message.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")


    async def update_buttons(self):
        if self.current_page == 1:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
            self.first_button.disabled = True
            self.first_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary
            self.first_button.disabled = False
            self.first_button.style = discord.ButtonStyle.green

        if self.current_page == len(self.events):
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
            self.last_button.disabled = True
            self.last_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary
            self.last_button.disabled = False
            self.last_button.style = discord.ButtonStyle.green

    async def create_embed(self, data):
        emb = helpers.Embed(title=f"{data.name}",thumbnail=data.thumbnail,image=data.image)
        host = data.host.split(":")
        emb.add_field(name="Hosted By:",value=host[0],inline=False)
        if data.start_time < self.ts:
            emb.add_field(name="Status:",value=f"Ongoing :green_circle:\nEnding: <t:{data.end_time}:R>",inline=False)
        else:
            emb.add_field(name="Status:",value=f"Waiting to start... :orange_circle:\nStarting: <t:{data.start_time}> (<t:{data.start_time}:R>)\nEnding: <t:{data.end_time}> (<t:{data.end_time}:R>)",inline=False)
        emb.add_field(name="",value=f"User joined: {await Database.select_counter_event_user_partecipants(data.id)}",inline=False)
        
        emb.set_footer(text=f"Page {self.current_page}/{(len(self.events))}")
        return emb

    @discord.ui.button(label="|<", style=discord.ButtonStyle.green)
    async def first_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        await self.update_message()
            

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message()

    @discord.ui.button(label="Join", style=discord.ButtonStyle.primary)
    async def join_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        player = await helpers.get_user(user=interaction.user)
        if player is None:
            return await interaction.followup.send("You are not linked in the bot. Use '/user verify' to link.",ephemeral=True)
        if not await Database.insert_event_partecipant(player.id,player.name,interaction.user.id,self.events[self.current_page-1].id,""):
            return await interaction.followup.send("You already joined the event",ephemeral=True)
        await interaction.followup.send("Successfully Registered.",ephemeral=True)
        await self.update_message()

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message()

    @discord.ui.button(label=">|", style=discord.ButtonStyle.green)
    async def last_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = len(self.events)
        await self.update_message()
