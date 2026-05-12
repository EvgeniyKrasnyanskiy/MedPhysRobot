import pytest
from aiogram.types import MessageEntity
from utils.sender import utf16_len, shift_entities

def test_utf16_len():
    # Regular text
    assert utf16_len("hello") == 5
    # Emoji (usually 2 units in UTF-16)
    assert utf16_len("📨") == 2
    # Combined
    assert utf16_len("📨 hello") == 2 + 1 + 5 # emoji + space + hello

def test_shift_entities():
    original_entities = [
        MessageEntity(type="bold", offset=0, length=5),
        MessageEntity(type="text_link", offset=6, length=5, url="https://example.com")
    ]
    
    # Shift by 10
    shifted = shift_entities(original_entities, 10)
    
    assert len(shifted) == 2
    assert shifted[0].offset == 10
    assert shifted[0].length == 5
    assert shifted[1].offset == 16
    assert shifted[1].length == 5
    assert shifted[1].url == "https://example.com"

def test_shift_entities_none():
    assert shift_entities(None, 10) == []
    assert shift_entities([], 10) == []

def test_shift_entities_zero_offset():
    original = [MessageEntity(type="bold", offset=0, length=5)]
    shifted = shift_entities(original, 0)
    assert shifted == original
