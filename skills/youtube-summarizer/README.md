# YouTube Summarizer

对 YouTube 视频生成结构化中文摘要的 Claude Code Skill。拉取视频字幕后，按视频类型（访谈、教程、Vlog、评论、评测、演讲等）生成侧重点合适的摘要，帮助快速判断视频是否值得观看。

## 功能特性

- **自动拉取字幕**：支持指定语言，失败时可列出可用字幕语言。
- **长短视频分流**：短视频直接摘要；长视频按时间分段、段间保留重叠，先逐段摘要再合并。
- **本地缓存**：字幕和摘要落盘到工作目录，重复处理同一视频不会重新拉取。
- **批量处理**：支持一次传入多个链接，按序处理并报告进度。
- **结构化输出**：包含一句话总结、关键要点、详细内容、时间线（长视频）、观看建议等章节。

## 目录结构

```
youtube-summarizer/
├── SKILL.md              # Skill 主定义与执行流程
├── config.yaml           # 工作目录、阈值、分段参数
├── prompts/              # 摘要提示词模板
│   ├── direct_summary.md     # 短视频直接摘要
│   ├── segment_summary.md    # 长视频分段摘要
│   └── merge_summary.md      # 长视频合并摘要
└── scripts/
    └── fetch_transcript.py   # 字幕拉取与分段脚本
```

## 配置

编辑 `config.yaml`：

| 字段 | 说明 | 默认值 |
| --- | --- | --- |
| `workspace_dir` | 字幕和摘要的工作目录 | `~/Workspace/Gang/jinxiaozi/youtube` |
| `short_video_threshold_minutes` | 短视频阈值（分钟），低于此值走直接摘要流程 | `30` |
| `segment_minutes` | 分段时长（分钟） | `10` |
| `overlap_minutes` | 段间重叠时长（分钟），避免话题在边界被切断 | `1` |

## 使用方式

该 Skill 设置了 `disable-model-invocation: true`，需用户主动调用。在 Claude Code 中输入 `/youtube-summarizer` 并附上 YouTube 链接即可：

```
/youtube-summarizer https://www.youtube.com/watch?v=xxxxx
```

也可以一次传入多个链接批量处理。

## 输出位置

- 字幕：`{workspace_dir}/transcripts/{video_id}.json`
- 长视频分段：`{workspace_dir}/transcripts/{video_id}/seg_XX.txt`
- 短视频摘要：`{workspace_dir}/summaries/{video_id}.md`
- 长视频段摘要与最终合并：`{workspace_dir}/summaries/{video_id}/seg_XX_summary.md` 及 `final.md`

## 依赖

- Python 3，`pyyaml`
- `fetch_transcript.py` 所需的 YouTube 字幕拉取库（见脚本内 import）
