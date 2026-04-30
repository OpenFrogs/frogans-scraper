# -*- coding: utf-8 -*-
import platform
import re

class FrogansRequest:
    def __init__(self, address: str, method: str = "get", data: str = ""):
        self.address = address
        self.method = method
        self.data = data
    def __str__(self):
        return self.address

class Scraper:
    def __init__(self, settings: dict):
        pass
    def scrape(self, request: FrogansRequest) -> list[FrogansRequest]:
        pass

# https://stackoverflow.com/a/60498038/8507259
def b36_encode(i):
    if i < 36: return "0123456789abcdefghijklmnopqrstuvwxyz"[i]
    return b36_encode(i // 36) + b36_encode(i % 36)

def unicode_to_b36(s: str) :
    result = ""
    for chr in s:
        # Convert the codepoint to base 36 and pad it with 0s to a length of 4
        base36_str = b36_encode(ord(chr)).zfill(4)
        result += base36_str
    return result

LINUX_CHARMAP = {chr(0): chr(9216)}
LINUX_FILENAME_MAP = {".": "~.", "..": "~.."}
MACOS_CHARMAP = {chr(0): chr(9216), chr(58): chr(8758)}
MACOS_FILENAME_MAP = {".": "~.", "..": "~.."}
WINDOWS_SPECIAL_CHARMAP = {chr(60): chr(65124), chr(62): chr(65125), chr(58): chr(8282), chr(34): chr(65282), chr(92): chr(10741), chr(124): chr(9474), chr(63): chr(65046), chr(42): chr(65121)}
CONTROL_CHARMAP = {chr(i): chr(9216 + i) for i in range(32)}
WINDOWS_CHARMAP = WINDOWS_SPECIAL_CHARMAP | CONTROL_CHARMAP
WINDOWS_BAD_FILENAMES = ["CON", "PRN", "AUX", "NUL", *["COM"+str(i+1) for i in range(9)], *["LPT"+str(i+1) for i in range(9)]]
FILENAME_PATTERN = re.compile("(.+?)([^\\\\/.]+)(\\.[^\\\\/]+)?$")

def sanitize_filename(fn: str):
    match platform.system():
        case "Linux":
            tmp = "".join(LINUX_CHARMAP.get(c, c) for c in fn)
            return LINUX_FILENAME_MAP.get(tmp, tmp)
        case "Darwin":
            tmp = "".join(MACOS_CHARMAP.get(c, c) for c in fn)
            return MACOS_FILENAME_MAP.get(tmp, tmp)
        case "Windows":
            tmp = "".join(WINDOWS_SPECIAL_CHARMAP.get(c, c) for c in fn)
            m = FILENAME_PATTERN.match(tmp)
            if m is not None:
                g = m.group(2)
                if g is not None and g.upper() in WINDOWS_BAD_FILENAMES:
                    ext = m.group(3)
                    return m.group(1) + "~" + g + ("" if ext is None else ext)
            return tmp