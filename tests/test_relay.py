import pytest
from aiogram.types import User, MessageEntity
from handlers.relay import format_header
from utils.sender import utf16_len

def test_format_header_basic():
    user = User(id=123, is_bot=False, first_name="Ivan", username="ivan_test")
    text, entities = format_header(user)
    
    assert "Ivan" in text
    assert "@ivan_test" in text
    assert "123" in text
    
    # Check that we have a bold link for the name
    assert any(e.type == "bold" for e in entities)
    assert any(e.type == "text_link" and e.url == "tg://user?id=123" for e in entities)
    # Check ID is code
    assert any(e.type == "code" for e in entities)

def test_format_header_no_username():
    user = User(id=456, is_bot=False, first_name="NoName")
    text, entities = format_header(user)
    
    assert "NoName" in text
    assert "@" not in text
    assert "456" in text

def test_format_header_entities_offset():
    user = User(id=789, is_bot=False, first_name="OffsetTest")
    text, entities = format_header(user)
    
    # Verify that entities offsets are within the text length
    text_len = utf16_len(text)
    for ent in entities:
        assert ent.offset >= 0
        assert ent.offset + ent.length <= text_len

def test_album_caption_logic():
    # Simulate logic from handle_private_message for album
    user = User(id=1, is_bot=False, first_name="User")
    header_text, header_entities = format_header(user)
    header_offset = utf16_len(header_text)
    
    # Album element 1
    user_text_1 = "Photo 1"
    user_entities_1 = [MessageEntity(type="italic", offset=0, length=5)]
    
    # Album element 2
    user_text_2 = "Photo 2"
    user_entities_2 = []
    
    # Process element 1 (i=0)
    caption_1 = header_text + user_text_1
    from utils.sender import shift_entities
    shifted_1 = shift_entities(user_entities_1, header_offset)
    entities_1 = (header_entities or []) + shifted_1
    
    # Process element 2 (i=1)
    caption_2 = user_text_2
    entities_2 = user_entities_2
    
    assert caption_1.startswith("📨")
    assert caption_1.endswith("Photo 1")
    assert entities_1[-1].offset == header_offset
    
    assert caption_2 == "Photo 2"
    assert entities_2 == []
