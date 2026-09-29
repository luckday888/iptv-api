import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import config


def test_admin_config_defaults():
    assert isinstance(config.admin_session_days, int)
    assert config.admin_session_days == 7
    assert config.admin_login_rate_limit == 5
    # admin_password 是字符串，默认空
    assert isinstance(config.admin_password, str)
