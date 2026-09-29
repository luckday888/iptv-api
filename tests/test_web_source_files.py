import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from service.web.files.source_files import (
    resolve_path, read_raw, write_raw, SUPPORTED_KINDS,
)


def test_supported_kinds():
    assert set(SUPPORTED_KINDS) == {
        "template", "local", "subscribe", "epg", "whitelist", "blacklist", "alias",
    }


def test_resolve_and_read():
    path = resolve_path("subscribe")
    assert path.endswith("subscribe.txt")
    content = read_raw("subscribe")
    assert isinstance(content, str)


def test_unknown_kind():
    with pytest.raises(ValueError):
        resolve_path("evil")
