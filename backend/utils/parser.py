import re
from typing import List, Optional, Tuple


TRANSCRIPT_PATTERN = re.compile(
    r"^\[(\d{2}):(\d{2}):(\d{2})\s*-->\s*(\d{2}):(\d{2}):(\d{2})]\s*(.*)$"
)


def hms_to_seconds(hours: str, minutes: str, seconds: str) -> int:
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def parse_transcript_txt(content: str) -> List[Tuple[int, Optional[int], str]]:
    """
    Parse transcript text and return tuples of (start_sec, end_sec, text).
    Non-matching lines are ignored.
    """
    lines: List[Tuple[int, Optional[int], str]] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("生成时间"):
            continue
        match = TRANSCRIPT_PATTERN.match(line)
        if not match:
            continue
        start_sec = hms_to_seconds(match.group(1), match.group(2), match.group(3))
        end_sec = hms_to_seconds(match.group(4), match.group(5), match.group(6))
        text = match.group(7).strip()
        lines.append((start_sec, end_sec, text))
    return lines
