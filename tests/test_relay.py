import pytest
import html
from aiogram.types import User
from handlers.relay import format_header

def test_format_header_basic():
    user = User(id=123, is_bot=False, first_name="Ivan", username="ivan_test")
    html_text = format_header(user)
    
    assert "Ivan" in html_text
    assert "@ivan_test" in html_text
    assert "123" in html_text
    assert "<b>" in html_text
    assert "tg://user?id=123" in html_text
    assert "<code>" in html_text

def test_format_header_no_username():
    user = User(id=456, is_bot=False, first_name="NoName")
    html_text = format_header(user)
    
    assert "NoName" in html_text
    assert "@" not in html_text
    assert "456" in html_text

def test_album_caption_logic():
    user = User(id=1, is_bot=False, first_name="User")
    header_html = format_header(user)
    
    user_html = "<i>Photo 1</i>"
    caption = header_html + user_html
    
    assert caption.startswith("📨")
    assert "<i>Photo 1</i>" in caption
    assert "<b>" in caption
