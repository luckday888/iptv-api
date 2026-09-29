import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from service.web.auth.session import create_session, verify_session


def test_session_roundtrip():
    token = create_session()
    assert verify_session(token) is True


def test_bad_token():
    assert verify_session("not-a-valid-token") is False
    assert verify_session("") is False
