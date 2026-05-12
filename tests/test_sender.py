import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot
from aiogram.types import Message, User, Chat, MessageEntity
from utils.sender import send_content_to_group, utf16_len

@pytest.mark.asyncio
async def test_send_content_to_group_text_with_links():
    # Setup mocks
    bot = AsyncMock(spec=Bot)
    
    # Mock user message with a link
    user = User(id=1, is_bot=False, first_name="User")
    chat = Chat(id=1, type="private")
    
    # Text "Hello world" where "world" is a link
    text = "Hello world"
    original_entities = [
        MessageEntity(type="text_link", offset=6, length=5, url="https://world.com")
    ]
    
    message = MagicMock(spec=Message)
    message.text = text
    message.entities = original_entities
    message.caption = None
    message.caption_entities = None
    message.photo = None
    message.video = None
    message.document = None
    message.audio = None
    message.voice = None
    message.animation = None
    message.sticker = None
    message.video_note = None
    message.poll = None
    message.media_group_id = None
    message.chat = chat
    message.message_id = 123
    
    prefix = "HEADER " # Length 7
    prefix_entities = [MessageEntity(type="bold", offset=0, length=6)]
    
    # Run
    await send_content_to_group(
        message=message,
        bot=bot,
        chat_id=999,
        prefix=prefix,
        prefix_entities=prefix_entities
    )
    
    # Verify
    bot.send_message.assert_called_once()
    args, kwargs = bot.send_message.call_args
    
    sent_text = kwargs["text"]
    sent_entities = kwargs["entities"]
    
    assert sent_text == "HEADER Hello world"
    assert len(sent_entities) == 2
    
    # Prefix entity should be at 0
    assert sent_entities[0].type == "bold"
    assert sent_entities[0].offset == 0
    
    # Original entity should be shifted by 7
    assert sent_entities[1].type == "text_link"
    assert sent_entities[1].offset == 6 + 7
    assert sent_entities[1].url == "https://world.com"

@pytest.mark.asyncio
async def test_send_content_to_group_emoji_shift():
    bot = AsyncMock(spec=Bot)
    chat = Chat(id=1, type="private")
    
    # Prefix with emoji: "📨 Msg: "
    # "📨" is 2 UTF-16 units. " Msg: " is 6 units. Total prefix offset = 8.
    prefix = "📨 Msg: "
    prefix_entities = []
    
    text = "Test"
    original_entities = [MessageEntity(type="italic", offset=0, length=4)]
    
    message = MagicMock(spec=Message)
    message.text = text
    message.entities = original_entities
    message.caption = None
    message.caption_entities = None
    message.chat = chat
    message.photo = None
    message.video = None
    message.document = None
    message.audio = None
    message.voice = None
    message.animation = None
    message.sticker = None
    message.video_note = None
    message.poll = None
    message.media_group_id = None
    
    await send_content_to_group(
        message=message,
        bot=bot,
        chat_id=999,
        prefix=prefix,
        prefix_entities=prefix_entities
    )
    
    args, kwargs = bot.send_message.call_args
    sent_entities = kwargs["entities"]
    
    # The italic entity should be shifted by 8 (because of the emoji)
    assert sent_entities[0].offset == 8
