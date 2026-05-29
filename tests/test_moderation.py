from datetime import timedelta
from handlers.moderation import parse_mute_duration

def test_parse_mute_duration_default():
    assert parse_mute_duration("/mute") == timedelta(hours=2)
    assert parse_mute_duration("/mute   ") == timedelta(hours=2)
    assert parse_mute_duration("/mute ") == timedelta(hours=2)

def test_parse_mute_duration_valid():
    assert parse_mute_duration("/mute 30m") == timedelta(minutes=30)
    assert parse_mute_duration("/mute 2h") == timedelta(hours=2)
    assert parse_mute_duration("/mute 5") == timedelta(hours=5)
    assert parse_mute_duration("/mute 3d") == timedelta(days=3)
    assert parse_mute_duration("/mute 1w") == timedelta(weeks=1)

def test_parse_mute_duration_invalid():
    assert parse_mute_duration("/mute abc") is None
    assert parse_mute_duration("/mute -5") is None
    assert parse_mute_duration("/mute 5x") is None
