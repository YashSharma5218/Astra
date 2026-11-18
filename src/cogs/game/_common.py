"""Helpers shared by the game cogs. The leading underscore keeps the cog loader from loading it."""
import discord

VIEW_SECONDS = 180      # buttons on a screen stop working after this; run the command again


async def require_player(interaction, db):
    """Return the player's row, or tell them to /start and return None."""
    player = await db.get_player(interaction.user.id)
    if player is None:
        await interaction.response.send_message(
            "You need a fighter first. Use /start.", ephemeral=True)
    return player


class OwnerView(discord.ui.View):
    """Base of the confirm and craft screens: only the player who ran the command can press the buttons."""

    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__(timeout=VIEW_SECONDS)
        self.bot = bot
        self.interaction = interaction              # the original command, edited when the buttons expire
        self.user_id = interaction.user.id
        self.busy = False                           # a second click while the first runs is ignored

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message("This is not your screen.", ephemeral=True)
        return False

    async def on_timeout(self):
        try:
            await self.interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass


async def choose_items(interaction, db, code, rarity, verb: str):
    """Work out which items /salvage or /sell should act on: one item by code, or every unequipped
    item of a rarity. Equipped items (in any preset) are never included. Tells the player what is
    wrong and returns None when there is nothing valid to act on."""
    uid = interaction.user.id
    if (code is None) == (rarity is None):
        await interaction.response.send_message(
            "Give either a code (like H12) or a rarity, not both and not neither.", ephemeral=True)
        return None
    equipped = await db.equipped_item_ids(uid)
    if code is not None:
        item = await db.get_item_by_uid(code)
        if item is None or item.owner_id != uid:
            await interaction.response.send_message("You do not own an item with that code.", ephemeral=True)
            return None
        if item.id in equipped:
            await interaction.response.send_message(
                f"{item.uid} is equipped. Equip something else in its place first.", ephemeral=True)
            return None
        return [item]
    items = [i for i in await db.list_items(uid) if i.rarity == rarity and i.id not in equipped]
    if not items:
        await interaction.response.send_message(
            f"You have no unequipped {rarity} items to {verb}.", ephemeral=True)
        return None
    return items
