import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import TrialDatabase
from bot.discord_cmd.modules.trial._helper import send_log, LogType, generate_info_emb
from datetime import datetime

class AcceptTaskView(discord.ui.View):
    def __init__(self,options_categories):
        super().__init__(timeout=None)
        self.category_select = discord.ui.Select(
            row=0,
            placeholder="Choose a category...",
            options=options_categories
        )
        self.category_select.callback = self.select1_callback
        self.add_item(self.category_select)

        self.task_select = discord.ui.Select(
            custom_id="task-selection",
            row = 1,
            placeholder="Choose a Task...",
            disabled=True,
            options=[discord.SelectOption(label="None", value="none")] 
        )
        self.task_select.callback = self.select2_callback

        
        #self.add_item(self.task_select)
        self.selected_c = None
        self.selected_t = None

    async def send(self, ctx:discord.Interaction):
        await ctx.followup.send(embed=await self.create_embed(),view=self,ephemeral=True)
        
    def update_btn(self):
        self.confirm_button.disabled = self.selected_t is None

    async def create_embed(self):
        name = helpers.make_title(self.trial_mng.trial.name)
        if not self.selected_c:
            return helpers.Embed(title=f"Select a {name}")
        emb = helpers.Embed(title=name)

        msg = ""
        for task in self.trial_mng.get_tasks_for_category(self.selected_c).values():
            msg += f"{":arrow_right: " if self.selected_t == task.id else ""}**{task.name.title()}** | {helpers.formattime(task.cooldown/60)} :stopwatch: | {task.reward}:\n"
            requisites = self.trial_mng.get_requisite_for_task(task.id)
            values = []
            for requisite in requisites.values():
                msg += f"> `{requisite.formula.upper()}` | {requisite.goal:,}\n"
            msg += f"Bonus: {task.bonus} if completed in {helpers.formattime(task.bonus_time/60)}\n"
        if msg == "":
            emb.add_field(
                name=category.name.title(),
                value=f"No {name} for this category."
            )
            return emb
        emb.add_field(
            name=f"==={self.trial_mng.categories[self.selected_c].name.title()}===",
            value=msg,
            inline=False
        )
        emb.set_footer(text="Name | Cooldown | Reward")
        return emb

    async def select1_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()

        selected_value = self.category_select.values[0]

        for option in self.category_select.options:
            option.default = option.value == selected_value

        self.selected_c = int(selected_value)
        self.selected_t = None
        tasks = self.trial_mng.get_tasks_for_category(self.selected_c)

        options_tasks = []
        for task in tasks.values():
            options_tasks.append(discord.SelectOption(label=task.name.title(),value=str(task.id)))
        self.task_select.options = options_tasks
        self.task_select.disabled = False
        self.task_select.placeholder = f"Choose a {helpers.make_title(self.trial_mng.trial.name)}..."
        
        if not self.get_item("task-selection"):
            self.add_item(self.task_select)
            
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)


    async def select2_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.task_select.values[0]

        for option in self.task_select.options:
            option.default = option.value == selected_value
        
        self.selected_t = int(selected_value)
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)
        

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,emoji="🗑️",row=2)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=helpers.Embed(title=f"Operation cancelled"),view=None)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,emoji="✔️",disabled=True,row=2)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        active_records = await self.trial_mng.fetch_user_active_records(self.ig_user.id)
        category_active = any(
            self.trial_mng.tasks[r.trial_task_id].trial_category_id == self.selected_c 
            for r in active_records.values()
        )
        task_active = any(
            r.trial_task_id == self.selected_t 
            for r in active_records.values()
        )
        if task_active:
            return await interaction.followup.send(content=f"{self.trial_mng.tasks[self.selected_t].name.title()} already active", ephemeral=True)
        if not self.trial_mng.categories[self.selected_c].allow_parallel and category_active:
            return await interaction.followup.send(content=f"No parallel {helpers.make_title(self.trial_mng.trial.name)} allowed. Complete the active one", ephemeral=True)

        last_records = await self.trial_mng.fetch_user_last_records(self.ig_user.id)
        if self.selected_c in last_records:
            last = last_records[self.selected_c]
            task = self.trial_mng.tasks[last.trial_task_id]

            dt = int(datetime.now().timestamp())
            remaining = (last.end_time + task.cooldown) - dt
            if remaining > 0:
                return await interaction.followup.send(content=f"Task still in cooldown. (<t:{int(dt + remaining)}:R>)", ephemeral=True)

        await interaction.edit_original_response(embed=helpers.Embed(title=f"{self.trial_mng.categories[self.selected_c].name.title()} > {self.trial_mng.tasks[self.selected_t].name.title()} started."))
        
        await send_log(
            self.client,self.trial_mng.trial.server_id,LogType.TASK_ACCEPTED,
            value=f"{self.trial_mng.categories[self.selected_c].name.title()} > {self.trial_mng.tasks[self.selected_t].name.title()}",
            usr1=self.author_id
        )
        ts = int(datetime.now().timestamp()) 
        await self.trial_mng.create_record(self.trial_mng.tasks[self.selected_t].id,self.ig_user.id,self.author_id,False,False,ts,None,ts,self.ig_user.npc_kills,self.ig_user.steps,self.ig_user.user_kills,self.ig_user.level,self.ig_user.npc_kills,self.ig_user.steps,self.ig_user.user_kills,self.ig_user.level)
        await self.trial_mng.save()


