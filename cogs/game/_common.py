"""Helpers shared by the game cogs. The leading underscore keeps the cog loader from loading it."""


async def require_player(interaction, db):
    """Return the player's row, or tell them to /start and return None."""
    player = await db.get_player(interaction.user.id)
    if player is None:
        await interaction.response.send_message(
            "You need a fighter first. Use /start.", ephemeral=True)
    return player
