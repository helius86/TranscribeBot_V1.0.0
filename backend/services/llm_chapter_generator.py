import json
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

from ..config import get_settings
from ..models import TranscriptLine


@dataclass
class ChapterData:
    title: str
    start_sec: int
    end_sec: Optional[int]
    summary: Optional[str]
    tags: Optional[str]
    source: str = "auto"
    confidence: Optional[float] = None
    order: Optional[int] = None


def _format_seconds(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _hms_to_seconds(time_str: str) -> int:
    parts = time_str.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Invalid time format: {time_str}")


def _build_transcript_text(transcript_lines: List[TranscriptLine]) -> str:
    sorted_lines = sorted(transcript_lines, key=lambda l: l.start_sec)
    segments = []
    for line in sorted_lines:
        end_value = line.end_sec if line.end_sec is not None else line.start_sec
        segments.append(
            f"[{_format_seconds(line.start_sec)} --> {_format_seconds(end_value)}] {line.text}"
        )
    return "\n".join(segments)


PROMPT_TEMPLATE = """你现在扮演一名非常懂中文财经/聊天直播节奏的「长视频剪辑编辑 + 文案总监」，要帮主播给一整场直播回放做【人类风格】的章节划分。

视频总时长约 {VIDEO_DURATION_MINUTES} 分钟。

请严格输出 JSON（必须符合下面规则）：
1）必须输出 10 个章节，index 从 1 递增。
2）章节必须按时间顺序【连续覆盖】整段直播，不允许出现时间空档（gap）。
   - 第 1 章 start 必须是直播开头附近的一个 transcript 时间戳。
   - 对于 1~9 章：第 i 章的 end 必须等于第 i+1 章的 start（end = next_start）。
   - 第 10 章 end 必须是直播结束附近的一个 transcript 时间戳。
3）start 和 end 的时间戳请【优先/尽量严格使用 transcript 中已经出现过的时间戳】；不要虚构不存在的时间点。
4）不要均分时间。每章标题<=18汉字，reason<=40字。

输出 JSON 格式如下：
{{
  "chapters": [
    {{
      "index": 1,
      "start": "HH:MM:SS",
      "end": "HH:MM:SS",
      "title": "章节标题（不超过18个汉字）",
      "reason": "简要说明这一章的结构/逻辑作用（不超过40字）"
    }}
  ]
}}

标题风格参考：
- 开场 / 正题 / 小结 / 总结 / 锦囊 / 收盘
- 正题开始：2026新趋势
- 逆天SC借屏道歉
- 下周锦囊：为什么波动加大

下面是 transcript（逐字稿，带时间戳）：
{TRANSCRIPT_TEXT}
"""


def _call_volcengine_chat(prompt: str) -> Optional[dict]:
    settings = get_settings()
    if not settings.volcengine_api_key:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.volcengine_api_key}",
    }
    payload = {
        "model": settings.volcengine_model,
        "messages": [
            {"role": "system", "content": "你是一个资深中文财经直播剪辑师，擅长拆分长视频章节并输出JSON。"},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(settings.volcengine_base_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure fallback
        body = exc.response.text if exc.response is not None else ""
        logging.error("Volcengine API call failed (status): %s | body: %s", exc, body)
        return None
    except Exception as exc:  # pragma: no cover - network failure fallback
        logging.error("Volcengine API call failed: %s", exc)
        return None


def _parse_llm_response(data: dict) -> List[ChapterData]:
    if not data or "choices" not in data or not data["choices"]:
        return []
    content = data["choices"][0]["message"].get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logging.error("Failed to decode LLM content as JSON.")
        return []

    chapters_raw = parsed.get("chapters", [])
    chapters: List[ChapterData] = []
    for idx, ch in enumerate(chapters_raw):
        try:
            start_sec = _hms_to_seconds(ch.get("start", "00:00:00"))
            end_sec = _hms_to_seconds(ch.get("end", "00:00:00"))
            title = ch.get("title", f"Chapter {idx + 1}")
            summary = ch.get("reason") or ch.get("summary")
            order = ch.get("index", idx + 1)
            chapters.append(
                ChapterData(
                    title=title,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    summary=summary,
                    tags=None,
                    source="auto_llm",
                    confidence=None,
                    order=order,
                )
            )
        except Exception as exc:
            logging.error("Failed to parse chapter row: %s", exc)
            continue
    return chapters


def _nearest_time(target: int, candidates: List[int]) -> int:
    if not candidates:
        return target
    closest = min(candidates, key=lambda x: abs(x - target))
    return closest


def _snap_chapters_to_transcript(
    chapters: List[ChapterData], transcript_lines: List[TranscriptLine]
) -> List[ChapterData]:
    if not chapters or not transcript_lines:
        return chapters

    starts = [l.start_sec for l in transcript_lines]
    ends = [l.end_sec if l.end_sec is not None else l.start_sec for l in transcript_lines]
    min_time = min(starts)
    max_time = max(ends)

    snapped: List[ChapterData] = []
    for ch in chapters:
        start_raw = max(min(ch.start_sec, max_time), min_time)
        end_raw = max(min(ch.end_sec if ch.end_sec is not None else ch.start_sec, max_time), min_time)

        snapped_start = _nearest_time(start_raw, starts)
        snapped_end = _nearest_time(end_raw, ends)
        if snapped_end < snapped_start:
            snapped_end = snapped_start

        snapped.append(
            ChapterData(
                title=ch.title,
                start_sec=snapped_start,
                end_sec=snapped_end,
                summary=ch.summary,
                tags=ch.tags,
                source=ch.source,
                confidence=ch.confidence,
                order=ch.order,
            )
        )
    return snapped


def _fallback_stub(transcript_lines: List[TranscriptLine], max_chapters: int) -> List[ChapterData]:
    if not transcript_lines:
        return []
    sorted_lines = sorted(transcript_lines, key=lambda l: l.start_sec)
    duration = sorted_lines[-1].end_sec or sorted_lines[-1].start_sec
    duration = max(duration, sorted_lines[-1].start_sec)
    chapter_count = min(max_chapters or 10, 10)
    step = max(duration // chapter_count, 1)

    chapters: List[ChapterData] = []
    for idx in range(chapter_count):
        start = idx * step
        end = min((idx + 1) * step, duration)
        title = f"Chapter {idx + 1}: {_format_seconds(start)} - {_format_seconds(end)}"
        chapters.append(
            ChapterData(
                title=title,
                start_sec=start,
                end_sec=end,
                summary="Placeholder summary for this segment.",
                tags=None,
                source="auto_stub",
                confidence=0.5,
                order=idx + 1,
            )
        )
    return chapters


def generate_chapters_from_transcript(
    transcript_lines: List[TranscriptLine], max_chapters: int = 10
) -> List[ChapterData]:
    if not transcript_lines:
        return []

    sorted_lines = sorted(transcript_lines, key=lambda l: l.start_sec)
    duration_sec = sorted_lines[-1].end_sec or sorted_lines[-1].start_sec
    duration_sec = max(duration_sec, sorted_lines[-1].start_sec)
    duration_minutes = max(1, int(duration_sec // 60))  # avoid zero

    transcript_text = _build_transcript_text(sorted_lines)
    prompt = PROMPT_TEMPLATE.format(
        VIDEO_DURATION_MINUTES=duration_minutes,
        TRANSCRIPT_TEXT=transcript_text,
    )

    api_response = _call_volcengine_chat(prompt)
    chapters = _parse_llm_response(api_response) if api_response else []

    if chapters:
        chapters_snapped = _snap_chapters_to_transcript(chapters, sorted_lines)
        chapters_sorted = sorted(chapters_snapped, key=lambda c: (c.order or 0, c.start_sec))
        return chapters_sorted[: max_chapters or 10]

    # fallback stub
    return _fallback_stub(transcript_lines, max_chapters)


def regenerate_single_chapter(
    transcript_lines: List[TranscriptLine],
    new_start_sec: int,
    existing_title: str,
    existing_summary: Optional[str],
) -> ChapterData:
    """
    Stub that rewrites chapter metadata based on a new start time.
    """
    context_line = None
    for line in transcript_lines:
        if line.start_sec >= new_start_sec:
            context_line = line
            break
    context_text = context_line.text if context_line else "No nearby transcript context."
    title = f"Adjusted Chapter @ {_format_seconds(new_start_sec)}"
    summary = f"Auto-updated using nearby transcript: {context_text[:120]}"
    return ChapterData(
        title=title,
        start_sec=new_start_sec,
        end_sec=None,
        summary=summary,
        tags=None,
        source="ai_edit",
        confidence=0.6,
        order=None,
    )
