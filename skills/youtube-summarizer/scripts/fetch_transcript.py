import argparse
import json
import os
import re
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

DEFAULT_SHORT_THRESHOLD_MINUTES = 30.0
DEFAULT_SEGMENT_MINUTES = 10.0
DEFAULT_OVERLAP_MINUTES = 1.0

WORKSPACE_ENV = "YOUTUBE_SUMMARIZER_WORKSPACE"


def get_workspace_dir() -> Path:
    """从环境变量读取工作目录。未设置时给出清晰的报错。"""
    value = os.environ.get(WORKSPACE_ENV)
    if not value:
        raise SystemExit(
            f"环境变量 {WORKSPACE_ENV} 未设置。\n"
            f"请在 ~/.claude/settings.json 的 env 字段中配置，例如:\n"
            f'  {{ "env": {{ "{WORKSPACE_ENV}": "~/Workspace/youtube" }} }}'
        )
    return Path(os.path.expanduser(value))


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
    """通过 YouTube 视频链接获取字幕列表。"""
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=languages or ["en"])
    return [
        {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
        for snippet in transcript
    ]


def list_transcripts(url: str) -> list[dict]:
    """获取 YouTube 视频的可用字幕列表。"""
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
    segment_minutes: float = DEFAULT_SEGMENT_MINUTES,
    overlap_minutes: float = DEFAULT_OVERLAP_MINUTES,
) -> list[dict]:
    """将字幕按时间窗口切分为多个段。"""
    segment_sec = segment_minutes * 60
    overlap_sec = overlap_minutes * 60

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


def save_segments(
    url: str,
    transcript: list[dict],
    segment_minutes: float = DEFAULT_SEGMENT_MINUTES,
    overlap_minutes: float = DEFAULT_OVERLAP_MINUTES,
) -> list[dict]:
    """将字幕按时间切段，每段保存为独立文件。"""
    video_id = extract_video_id(url)
    segments = split_segments(transcript, segment_minutes, overlap_minutes)
    seg_dir = get_workspace_dir() / "transcripts" / video_id
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
    """将字幕保存为 JSON 文件。"""
    video_id = extract_video_id(url)
    transcripts_dir = get_workspace_dir() / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    file_path = transcripts_dir / f"{video_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            {"video_id": video_id, "url": url, "transcript": transcript},
            f,
            ensure_ascii=False,
            indent=2,
        )
    return file_path


def load_transcript(video_id: str) -> list[dict] | None:
    """从本地加载已保存的字幕。"""
    file_path = get_workspace_dir() / "transcripts" / f"{video_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["transcript"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YouTube 字幕拉取与切段工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出视频可用的字幕语言")
    p_list.add_argument("url")

    p_fetch = sub.add_parser("fetch", help="拉取字幕并打印到 stdout")
    p_fetch.add_argument("url")
    p_fetch.add_argument("--lang", default="en", help="字幕语言代码（默认: en）")

    p_save = sub.add_parser("save", help="拉取字幕、保存到工作目录，并在需要时切段")
    p_save.add_argument("url")
    p_save.add_argument("--lang", default="en", help="字幕语言代码（默认: en）")
    p_save.add_argument(
        "--short-threshold-minutes",
        type=float,
        default=DEFAULT_SHORT_THRESHOLD_MINUTES,
        help=f"短视频阈值（分钟），低于此值不切段。默认: {DEFAULT_SHORT_THRESHOLD_MINUTES}",
    )
    p_save.add_argument(
        "--segment-minutes",
        type=float,
        default=DEFAULT_SEGMENT_MINUTES,
        help=f"分段时长（分钟）。默认: {DEFAULT_SEGMENT_MINUTES}",
    )
    p_save.add_argument(
        "--overlap-minutes",
        type=float,
        default=DEFAULT_OVERLAP_MINUTES,
        help=f"段间重叠（分钟）。默认: {DEFAULT_OVERLAP_MINUTES}",
    )

    args = parser.parse_args(argv)

    if args.command == "list":
        for t in list_transcripts(args.url):
            kind = "自动生成" if t["is_generated"] else "人工上传"
            print(f"  {t['language']} ({t['language_code']}) - {kind}")
    elif args.command == "fetch":
        for item in fetch_transcript(args.url, languages=[args.lang]):
            print(f"[{item['start']:.1f}s] {item['text']}")
    elif args.command == "save":
        transcript = fetch_transcript(args.url, languages=[args.lang])
        path = save_transcript(args.url, transcript)
        duration = get_total_duration(transcript)
        print(f"已保存 {len(transcript)} 条字幕 (时长 {duration / 60:.1f} 分钟)")
        print(f"字幕文件: {path}")
        if duration >= args.short_threshold_minutes * 60:
            segs = save_segments(
                args.url,
                transcript,
                segment_minutes=args.segment_minutes,
                overlap_minutes=args.overlap_minutes,
            )
            print(f"长视频，已切分为 {len(segs)} 段:")
            for seg in segs:
                print(
                    f"  段 {seg['index']}: {seg['start'] / 60:.1f}min - "
                    f"{seg['end'] / 60:.1f}min ({seg['item_count']} 条字幕) -> "
                    f"{seg['file_path']}"
                )
        else:
            print("短视频，无需切段，直接摘要即可")
    return 0


if __name__ == "__main__":
    sys.exit(main())
