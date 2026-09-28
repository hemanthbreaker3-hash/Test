import pytest
from unittest.mock import MagicMock
from pyrogram.types import User
from bot.modules.users_settings import get_user_settings


@pytest.mark.asyncio
async def test_ffset_button_layout():
    mock_client = MagicMock()
    mock_client.parse_mode = "html"
    dummy_user = User(id=1001, first_name="TestUser", username="testuser", client=mock_client)

    text, btns = await get_user_settings(dummy_user, stype="ffset")
    rows = btns.inline_keyboard

    assert len(rows) >= 3
    # First row is the toggle button alone
    assert len(rows[0]) == 1
    assert "FFmpeg Commands:" in rows[0][0].text

    # All remaining body and footer rows must have 2 buttons each
    for i, row in enumerate(rows[1:], start=1):
        assert len(row) == 2, f"Row {i} has {len(row)} buttons instead of 2: {[b.text for b in row]}"
