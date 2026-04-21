import json
import os
import re
from pathlib import Path

import yaml
from youtube_transcript_api import YouTubeTranscriptApi

# 读取配置
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    CONFIG = yaml.safe_load(_f)

WORKSPACE_DIR = Path(os.path.expanduser(CONFIG["workspace_dir"]))
TRANSCRIPTS_DIR = WORKSPACE_DIR / "transcripts"
SUMMARIES_DIR = WORKSPACE_DIR / "summaries"


def extract_video_id(url: str) -> str:
    """从 YouTube 链接中提取视频 ID。

    支持格式:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://www.youtube.com/v/VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
    """
    patterns = [
        r"(?:v=|v/|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"无法从链接中提取视频 ID: {url}")


def fetch_transcript(url: str, languages: list[str] | None = None) -> list[dict]:
    """通过 YouTube 视频链接获取字幕列表。

    Args:
        url: YouTube 视频链接。
        languages: 优先语言列表，例如 ["zh", "en"]。默认为 ["en"]。

    Returns:
        字幕列表，每项包含 text、start、duration 字段。
        示例: [{"text": "Hello", "start": 0.0, "duration": 2.5}, ...]
    """
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=languages or ["en"])
    return [
        {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
        for snippet in transcript
    ]


def list_transcripts(url: str) -> list[dict]:
    """获取 YouTube 视频的可用字幕列表。

    Args:
        url: YouTube 视频链接。

    Returns:
        字幕信息列表，每项包含 language、language_code、is_generated、is_translatable 字段。
    """
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    return [
        {
            "language": t.language,
            "language_code": t.language_code,
            "is_generated": t.is_generated,
            "is_translatable": t.is_translatable,
        }
        for t in transcript_list
    ]


def get_total_duration(transcript: list[dict]) -> float:
    """计算字幕的总时长（秒）。"""
    if not transcript:
        return 0.0
    last = transcript[-1]
    return last["start"] + last["duration"]


def split_segments(
    transcript: list[dict],
    segment_minutes: float | None = None,
    overlap_minutes: float | None = None,
) -> list[dict]:
    """将字幕按时间窗口切分为多个段。

    Args:
        transcript: 字幕列表，每项包含 text、start、duration。
        segment_minutes: 每段时长（分钟），默认从配置读取。
        overlap_minutes: 段间重叠时长（分钟），默认从配置读取。

    Returns:
        段列表，每项包含:
        - start: 段起始时间（秒）
        - end: 段结束时间（秒）
        - items: 该段内的字幕条目列表
    """
    seg_min = segment_minutes or CONFIG["segment_minutes"]
    ovl_min = overlap_minutes or CONFIG["overlap_minutes"]
    segment_sec = seg_min * 60
    overlap_sec = ovl_min * 60

    total = get_total_duration(transcript)
    segments = []
    seg_start = 0.0

    while seg_start < total:
        seg_end = seg_start + segment_sec
        items = [
            item for item in transcript
            if item["start"] + item["duration"] > seg_start and item["start"] < seg_end
        ]
        if items:
            segments.append({
                "start": seg_start,
                "end": min(seg_end, total),
                "items": items,
            })
        seg_start += segment_sec - overlap_sec

    return segments


def save_segments(url: str, transcript: list[dict]) -> list[dict]:
    """将字幕按时间切段，每段保存为独立文件。

    Args:
        url: YouTube 视频链接。
        transcript: 字幕列表。

    Returns:
        段信息列表，每项包含 index、start、end、item_count、file_path。
    """
    video_id = extract_video_id(url)
    segments = split_segments(transcript)
    seg_dir = TRANSCRIPTS_DIR / video_id
    seg_dir.mkdir(parents=True, exist_ok=True)

    result = []
    for i, seg in enumerate(segments, 1):
        text = "\n".join(item["text"] for item in seg["items"])
        file_path = seg_dir / f"seg_{i:02d}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        result.append({
            "index": i,
            "start": seg["start"],
            "end": seg["end"],
            "item_count": len(seg["items"]),
            "file_path": str(file_path),
        })
    return result


def save_transcript(url: str, transcript: list[dict]) -> Path:
    """将字幕保存为 JSON 文件。

    Args:
        url: YouTube 视频链接。
        transcript: 字幕列表。

    Returns:
        保存的文件路径。
    """
    video_id = extract_video_id(url)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TRANSCRIPTS_DIR / f"{video_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            {"video_id": video_id, "url": url, "transcript": transcript},
            f,
            ensure_ascii=False,
            indent=2,
        )
    return file_path


def load_transcript(video_id: str) -> list[dict] | None:
    """从本地加载已保存的字幕。

    Args:
        video_id: YouTube 视频 ID。

    Returns:
        字幕列表，如果文件不存在则返回 None。
    """
    file_path = TRANSCRIPTS_DIR / f"{video_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["transcript"]


if __name__ == "__main__":
    import sys

    usage = "用法: python fetch_transcript.py <list|fetch|save> <YouTube链接> [语言代码]"

    if len(sys.argv) < 3:
        print(usage)
        sys.exit(1)

    command = sys.argv[1]
    video_url = sys.argv[2]

    if command == "list":
        for t in list_transcripts(video_url):
            kind = "自动生成" if t["is_generated"] else "人工上传"
            print(f"  {t['language']} ({t['language_code']}) - {kind}")
    elif command == "fetch":
        langs = [sys.argv[3]] if len(sys.argv) > 3 else None
        for item in fetch_transcript(video_url, languages=langs):
            print(f"[{item['start']:.1f}s] {item['text']}")
    elif command == "save":
        langs = [sys.argv[3]] if len(sys.argv) > 3 else None
        transcript = fetch_transcript(video_url, languages=langs)
        path = save_transcript(video_url, transcript)
        duration = get_total_duration(transcript)
        threshold = CONFIG["short_video_threshold_minutes"] * 60
        print(f"已保存 {len(transcript)} 条字幕 (时长 {duration / 60:.1f} 分钟)")
        print(f"字幕文件: {path}")
        if duration >= threshold:
            segs = save_segments(video_url, transcript)
            print(f"长视频，已切分为 {len(segs)} 段:")
            for seg in segs:
                print(f"  段 {seg['index']}: {seg['start'] / 60:.1f}min - {seg['end'] / 60:.1f}min ({seg['item_count']} 条字幕) -> {seg['file_path']}")
        else:
            print("短视频，无需切段，直接摘要即可")
    else:
        print(f"未知命令: {command}")
        print(usage)
        sys.exit(1)
