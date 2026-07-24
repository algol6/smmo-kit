
import discord
from discord import TextChannel,SelectOption
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import TrialDatabase
from bot.database.model._trial import TrialTask
from bot.discord_cmd.modules.trial._helper import send_log, LogType, generate_info_emb
from bot.discord_cmd.modules.trial._entry_view import EntryView
from datetime import datetime
from re import findall



## Configure Task

class ConfigureTaskView(discord.ui.View):
    def __init__(self,tm,parent):
        super().__init__(timeout=None)
        self.parent_view = parent
        self.tm = tm

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.tm.trial.name} Task Configuration")
        emb.add_field(
            name="",
            value="From here you can configure the tasks.\n",
            inline=False
        )
        for task in self.tm.tasks.values():
            cat = self.tm.categories[task.trial_category_id]
            msg = f"Name: {cat.name} > {task.name}\n"
            reqs = self.tm.get_requisite_for_task(task.id)
            if len(reqs) == 0:
                for r in self.tm.requisites.values():
                    if r.trial_task_id == task.id:
                        reqs[r.id] = r
            msg += "No Requisites" if len(reqs) == 0 else "\n".join(f"> {r.formula}: {r.goal:,}" for r in reqs.values())
            emb.add_field(
                name="",
                value = msg,
                inline=False
            )
        return emb

    @discord.ui.button(label="Add Task", style=discord.ButtonStyle.green,row=2)
    async def add_task_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = AddTaskView(self.tm,self)
        await view.send(interaction)

    # unused, Ignore
    #@discord.ui.button(label="Edit Task", style=discord.ButtonStyle.blurple,row=2)
    async def edit_task_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        return await interaction.followup.send("WIP")
        # TODO
        pass

    @discord.ui.button(label="Remove Task", style=discord.ButtonStyle.red,row=2)
    async def remove_task_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = RemoveTaskView(self.tm,self)
        await view.send(interaction)

    @discord.ui.button(label="Go Back", style=discord.ButtonStyle.red,row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.restore_view(interaction)

class AddTaskView(discord.ui.View):
    def __init__(self,tm,main):
        super().__init__(timeout=None)
        self.main = main
        self.tm = tm
        self.category_selected = None
        self.category_name = None
        self.name = None
        self.cooldown = None
        self.reward = None
        self.bonus = None
        self.bonus_time = None
        self.requisites = []
        self.point = 0

        options_categories = [SelectOption(label=x.name,value=str(x.id)) for x in self.tm.categories.values()]
        is_empty = False
        if len(options_categories)==0:
            is_empty = True
            options_categories = [SelectOption(label="None")]
        self.category_select = discord.ui.Select(
            row=0,
            placeholder="Choose a category..." if not is_empty else "Create a category first",
            options=options_categories,
            disabled=is_empty
        )
        self.category_select.callback = self.select1_callback
        self.add_item(self.category_select)


    def update_btn(self):
        self.confirm_button.disabled = self.category_selected is None or self.name is None or self.cooldown is None or self.reward is None or self.bonus is None or self.bonus_time is None or len(self.requisites) == 0

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.tm.trial.name} Configuration")
        req = "Not Set" if len(self.requisites) == 0 else "\n".join(f"> {r["formula"]}: {r["goal"]:,}" for r in self.requisites)
        emb.add_field(
            name="Task Creation:",
            value=(
                f"Name: {self.name or "Not Set"}\n"
                f"Category: {self.category_name or "Not Set"}\n"
                f"Cooldown: {self.cooldown or "Not Set"}\n"
                f"Reward: {self.reward or "Not Set"}\n"
                f"Bonus: {self.bonus or "Not Set"}\n"
                f"Bonus Time: {self.bonus_time or "Not Set"}\n"
                f"Requisites:\n"
            ) + req
        )
        return emb

    async def select1_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.category_select.values[0]

        for option in self.category_select.options:
            option.default = option.value == selected_value
            if option.value == selected_value:
                self.category_name = option.label


        self.category_selected = int(selected_value)
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    @discord.ui.button(label="Set Info", style=discord.ButtonStyle.blurple,row=1)
    async def set_info_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        modal = AddTaskModal(title="Set Task Info")
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.name is None:
            return
        self.name = modal.name
        self.cooldown = modal.cooldown
        self.reward = modal.reward
        self.bonus = modal.bonus
        self.bonus_time = modal.bonus_time
        self.update_btn()
        await modal.modal_interaction.edit_original_response(embed=await self.create_embed(),view=self)


    @discord.ui.button(label="Add Requisite", style=discord.ButtonStyle.blurple,row=2)
    async def add_req_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        modal = AddRequisiveModal(title="Add Requisite")
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.formula is None or modal.goal is None or not helpers.is_number(modal.goal):
            return

        self.requisites.append({"formula":modal.formula,"goal":int(modal.goal)})
        self.update_btn()
        await modal.modal_interaction.edit_original_response(embed=await self.create_embed(),view=self)



    @discord.ui.button(label="Remove Requisite", style=discord.ButtonStyle.red,row=2)
    async def remove_req_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = RemoveRequisiteView(self.tm,self)
        await view.send(interaction)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,row=3,disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        task = await self.tm.create_task(self.category_selected,self.name,self.cooldown,self.reward,self.point,self.bonus_time,self.bonus)
        for r in self.requisites:
            await self.tm.create_requisite(task.id,r["formula"],r["goal"])
            self.main.parent_view.req_add.append(r)
        self.main.parent_view.task_add.append(task)
        await interaction.followup.send(content="Task Added",ephemeral=True)
        await self.main.send(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(content="Cancelled",ephemeral=True)
        await self.main.send(interaction)

class RemoveRequisiteView(discord.ui.View):
    def __init__(self,tm,main):
        super().__init__(timeout=None)
        self.main = main
        self.tm = tm
        options_tasks = [SelectOption(label=x.name,value=str(x.id)) for x in self.tm.tasks.values()]
        is_empty = False
        if len(options_tasks)==0:
            is_empty = True
            options_tasks = [SelectOption(label="None")]

        self.tasks_select = discord.ui.Select(
            row=0,
            placeholder="Choose a task..." if not is_empty else "Create a requisite first",
            options=options_tasks,
            disabled=is_empty
        )
        self.tasks_select.callback = self.select1_callback
        self.add_item(self.tasks_select)

        self.requisite_select = discord.ui.Select(
            custom_id="requisite-selection",
            row=1,
            placeholder="Choose a requisite...",
            options=[SelectOption(label="None")],
            disabled=True
        )
        self.requisite_select.callback = self.select2_callback
        self.task = None
        self.requisite:str = None

    def update_btn(self):
        self.confirm_button.disabled = self.task is None or self.requisite is None

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title="Task Deletion")

        emb.add_field(
            name="Task Remotion:",
            value="Select a requisite to remove"
        )
        return emb

    async def select1_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.tasks_select.values[0]

        for option in self.tasks_select.options:
            option.default = option.value == selected_value
        self.task = int(selected_value)

        options_tasks = []
        for req in self.tm.get_requisite_for_task(self.task).values():
            options_tasks.append(discord.SelectOption(label=req.formula,value=str(req.id)))
        if self.task < 0:
            for req in self.tm.requisites:
                if req.trial_task_id == self.task:
                    options_tasks.append(discord.SelectOption(label=req.formula,value=str(req.id)))

        disabled = False
        if len(options_tasks) == 0:
            disabled = True
            options_tasks = [discord.SelectOption(label="None")]

        self.requisite_select.options = options_tasks
        self.requisite_select.disabled = disabled
        self.requisite_select.placeholder = f"Choose a Requisite..."

        if not self.get_item("requisite-selection"):
            self.add_item(self.requisite_select)


        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    async def select2_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.requisite_select.values[0]

        for option in self.requisite_select.options:
            option.default = option.value == selected_value

        self.requisite = selected_value

        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,row=3,disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()

        if self.requisite[0] == "n":
            self.requisite = self.requisite.split(":")[-1]
            self.main.requisites.pop(int(self.requisite))
        else:
            self.main.main.parent_view.req_removed.append(int(self.requisite))
        await self.main.send(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(content="Cancelled",ephemeral=True)
        await self.main.send(interaction)

class AddRequisiveModal(discord.ui.Modal):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Formula",placeholder="ex: NPC, NPC+STEPS*3, PVP"))
        self.add_item(discord.ui.InputText(label="Goal",placeholder="ex: 500, 1000"))
        self.formula = None
        self.goal = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.modal_interaction = interaction
        self.formula = self.children[0].value
        self.goal = self.children[1].value
        self.stop()


class AddTaskModal(discord.ui.Modal):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Name",placeholder="ex: Easy, Hard, etc..."))
        self.add_item(discord.ui.InputText(label="Cooldown",placeholder="1d, 1w, etc..."))
        self.add_item(discord.ui.InputText(label="Reward",placeholder="100 gold, friendship, etc..."))
        self.add_item(discord.ui.InputText(label="Bonus (optional)",placeholder="ex: More gold",required=False))
        self.add_item(discord.ui.InputText(label="Time x Bonus (optional)",placeholder="ex: 1d, 3d",required=False))
        self.name = None
        self.cooldown = None
        self.reward = None
        self.bonus_time = None
        self.bonus = None

        self.point = 0

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.modal_interaction = interaction
        self.name = self.children[0].value
        self.cooldown = self.converter(self.children[1].value)
        self.reward = self.children[2].value
        self.bonus = self.children[3].value
        self.bonus_time = self.converter(self.children[4].value)
        self.stop()

    @staticmethod
    def converter(value:str) -> int:
        seconds = 0
        try:
            split_time = findall(r'\d+[a-zA-Z]', value)
        except:
            return 0
        for i in split_time:
            i = i.lower()
            if "w" in i:
                seconds += 604800 * int(i.split("w")[0])
            if "d" in i:
                seconds += 86400 * int(i.split("d")[0])
            if "h" in i:
                seconds += 3600 * int(i.split("h")[0])
            if "m" in i:
                seconds += 60 * int(i.split("m")[0])
            if "s" in i:
                seconds += int(i.split("s")[0])
        return seconds


class RemoveTaskView(discord.ui.View):
    def __init__(self,tm,main):
        super().__init__(timeout=None)
        self.main = main
        self.tm = tm
        options_tasks = [SelectOption(label=x.name,value=str(x.id)) for x in self.tm.tasks.values()]

        self.tasks_select = discord.ui.Select(
            row=0,
            placeholder="Choose a task...",
            options=options_tasks
        )
        self.tasks_select.callback = self.select1_callback
        self.add_item(self.tasks_select)

        self.task = None

    def update_btn(self):
        self.confirm_button.disabled = self.task is None

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title="Task Deletion")

        emb.add_field(
            name="Task Remotion:",
            value="Select a requisite to remove"
        )
        return emb

    async def select1_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.tasks_select.values[0]

        for option in self.tasks_select.options:
            option.default = option.value == selected_value

        self.task = int(selected_value)
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,row=3)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.main.parent_view.task_removed.append(self.task)
        await self.main.send(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(content="Cancelled",ephemeral=True)
        await self.main.send(interaction)
