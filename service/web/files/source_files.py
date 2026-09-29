import os
import tempfile

import utils.constants as constants
from utils.config import config

SUPPORTED_KINDS = (
    "template", "local", "subscribe", "epg", "whitelist", "blacklist", "alias",
)

# 固定路径源类型映射
_KIND_PATHS = {
    "local": constants.local_path,
    "subscribe": constants.subscribe_path,
    "epg": constants.epg_path,
    "whitelist": constants.whitelist_path,
    "blacklist": constants.blacklist_path,
}


def resolve_path(kind: str) -> str:
    # 按类型解析源文件路径，未知类型抛 ValueError
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"不支持的源类型: {kind}")
    if kind == "template":
        return config.source_file
    if kind == "alias":
        return constants.alias_path
    return _KIND_PATHS[kind]


def read_raw(kind: str) -> str:
    # 读取源文件原始文本，文件不存在时返回空串
    path = resolve_path(kind)
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""


def write_raw(kind: str, content: str) -> str:
    # 原子写入源文件：先写同目录临时文件再 os.replace，失败抛 ValueError
    if not isinstance(content, str):
        raise ValueError("内容必须为字符串")
    path = resolve_path(kind)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".source.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise ValueError(f"写入失败: {exc}") from exc
    return path
