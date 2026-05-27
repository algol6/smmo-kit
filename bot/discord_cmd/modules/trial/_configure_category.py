
import discord
from discord import TextChannel,SelectOption
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import TrialDatabase
from bot.discord_cmd.modules.trial._helper import send_log, LogType, generate_info_emb
from bot.discord_cmd.modules.trial._entry_view import EntryView
from datetime import datetime



## Configure Category
class ConfigureCategoryView(discord.ui.View):
    def __init__(self,tm,parent):
        super().__init__(timeout=None)
        self.parent_view = parent
        self.tm = tm

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.tm.trial.name} Configuration")
        emb.add_field(
            name="Category Configuration",
            value=(
                f"From here you can configure the categories:\n"
                f""
            )
        )
        for category in self.tm.categories.values():
            count = len(self.tm.get_tasks_for_category(category.id))
            emb.add_field(
                name=f"==={category.name.title()}===",
                value=f"Tasks in this category: {count:,}\nAllow parallel: {":white_check_mark:" if category.allow_parallel else ":x:"}",
                inline=False
            )
        return emb

    @discord.ui.button(label="Add Category", style=discord.ButtonStyle.green,row=1)
    async def add_category_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = AddCategoryView(self.tm,self.parent_view)
        await view.send(interaction)

    # disabled for now   
    #@discord.ui.button(label="Edit Category", style=discord.ButtonStyle.blurple,row=1)
    async def edit_category_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        # TODO

    @discord.ui.button(label="Remove Category", style=discord.ButtonStyle.red,row=1)
    async def remove_category_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = RemoveCategoryView(self.tm,self.parent_view)
        await view.send(interaction)
    
    @discord.ui.button(label="Go Back",style=discord.ButtonStyle.red,row=2)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.restore_view(interaction)

class AddCategoryView(discord.ui.View):
    def __init__(self,tm,main):
        super().__init__(timeout=None)
        self.tm = tm
        self.main = main
        self.name = None
        self.allow_parallel = None

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    def update_buttons(self):
        self.save_button.disabled = not (self.name and self.allow_parallel)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.tm.trial.name} Configuration")
        emb.add_field(
            name="Overall Bot System",
            value=(
                f"A cateogory is just a group of tasks, used to keep some order."
                f"From here you can create a new category in the system:\n"
                f"- Name.\n"
                f"  > Name... not much to explain here.\n"
                f"- Parallel Task.\n"
                f"  > Do you want the user to just do one task at the time or they can choose more than one?\n"
                f"  > It only work for the current category, that means two or more categories allow doing more tasks even if the parallel task is off."
            )
        )
        emb.add_field(
            name="Settings:",
            value=(
                f"Name: {self.name or "Not Set"}\n"
                f"Allow Parallel Tasks: {self.allow_parallel or 'Not Set'}\n"
            ),
            inline=False
        )
        return emb

    @discord.ui.select(
        row = 1,
        placeholder="Allow Parallel Task",
        options=[
            SelectOption(label="Yes"),
            SelectOption(label="No")
        ]
    )
    async def select1_callback(self, select, interaction):
        await interaction.response.defer()
        self.allow_parallel = select.values[0]
        self.update_buttons()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    @discord.ui.button(label="Set Name", style=discord.ButtonStyle.green,row=0)
    async def name_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        modal = AddCategoryModal(title="Add Category")
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.name is None:
            return
        self.name = modal.name
        self.update_buttons()
        await modal.modal_interaction.edit_original_response(embed=await self.create_embed(),view=self)


    @discord.ui.button(label="Save", style=discord.ButtonStyle.green,row=2)
    async def save_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.tm.create_category(self.name,self.allow_parallel[0]=="Y")
        await interaction.followup.send(content="Category added",ephemeral=True)
        await self.main.restore_view(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,row=2)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(content="Cancelled",ephemeral=True)
        await self.main.restore_view(interaction)

class AddCategoryModal(discord.ui.Modal):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Add category name",placeholder="ex: Pve Only, Huggers, etc..."))
        self.name = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() 
        self.name = self.children[0].value
        self.modal_interaction = interaction
        self.stop()

class EditNameModal(discord.ui.Modal):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Edit name",placeholder=""))
        self.value = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() 
        self.value = self.children[0].value
        self.modal_interaction = interaction
        self.stop()

class RemoveCategoryView(discord.ui.View):
    def __init__(self,tm,main):
        super().__init__(timeout=None)
        self.tm = tm
        self.main = main
        self.cid = None
        options_categories = []
        if not tm.categories:
            options_categories.append(SelectOption(label="None"))
        else:
            for cat in tm.categories.values():
                options_categories.append(SelectOption(label=cat.name.title(),value=str(cat.id)))
                
        self.category_select = discord.ui.Select(
            row=0,
            placeholder="Choose a category...",
            options=options_categories,
            disabled=not tm.categories
        )
        self.category_select.callback = self.select1_callback
        self.add_item(self.category_select)

    def create_embed(self):
        emb = helpers.Embed(title="Remove Category")
        emb.add_field(
            name="",
            value="Removing a category will delete all of its tasks"
        )
        return emb

    def update_btn(self):
        self.save_button.disabled = self.cid == None

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=self.create_embed(),view=self)

    async def select1_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.category_select.values[0]
        for option in self.category_select.options:
            option.default = option.value == selected_value
        self.cid = int(selected_value)
        self.update_btn()
        await interaction.edit_original_response(embed=self.create_embed(),view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,row=1,disabled=True)
    async def save_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.main.category_removed.append(self.cid)
        await interaction.followup.send(content="Category removed!",ephemeral=True)
        await self.main.restore_view(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,row=1)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(content="Operation Cancelled",ephemeral=True)
        await self.main.restore_view(interaction)
