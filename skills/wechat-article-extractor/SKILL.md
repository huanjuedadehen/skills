---
name: wechat-article-extractor
description: 解析微信公众号文章链接，提取标题、发布时间和正文。当用户提供 mp.weixin.qq.com 链接并希望提取或保存文章内容时触发。
disable-model-invocation: true
allowed-tools: Bash Write
---

# 微信公众号文章解析

依赖 Python 第三方包 [wechat-article-parser](https://github.com/huanjuedadehen/wechat-article-parser) 解析微信公众号文章，输出标题、发布时间（人类可读格式）和正文 Markdown。

## 环境变量

- `WECHAT_ARTICLE_EXTRACTOR_WORKSPACE`（可选）：解析结果保存目录。若设置，结果以 `{article_id}-{article_title}.md` 的格式保存到该目录；若未设置，结果直接返回给用户，不落盘。

## 执行流程

收到用户提供的微信公众号文章链接后，按以下步骤执行：

### 第一步：确保依赖已安装且为最新版本

每次执行前确保 `wechat-article-parser` 已安装且为 PyPI 最新版本。直接运行：

```bash
python -m pip install --upgrade wechat-article-parser
```

`pip install --upgrade` 在已是最新版本时不做改动，幂等且安全。如果命令失败（如 Python 版本低于 3.10），向用户说明并停止。

### 第二步：解析文章

对每个用户提供的链接，运行以下命令（将 `<URL>` 替换为实际链接）：

```bash
python - "<URL>" <<'EOF'
import os, re, sys
from datetime import datetime
from wechat_article_parser import parse, WeChatVerifyError

url = sys.argv[1]

try:
    result = parse(url)
except WeChatVerifyError:
    print("[ERROR] 微信触发了安全验证，请稍后重试或更换网络/代理", file=sys.stderr)
    sys.exit(2)

if not result.is_valid:
    print("[ERROR] 关键字段解析失败，链接可能已失效或被删除", file=sys.stderr)
    sys.exit(1)

publish_time = datetime.fromtimestamp(result.article_publish_time).strftime("%Y-%m-%d %H:%M:%S")
body = (
    f"# {result.article_title}\n\n"
    f"发布时间：{publish_time}\n\n"
    f"{result.article_markdown}\n"
)

workspace = os.environ.get("WECHAT_ARTICLE_EXTRACTOR_WORKSPACE")
if workspace:
    os.makedirs(workspace, exist_ok=True)
    safe_title = re.sub(r'[\\/:*?"<>|\s]', "_", result.article_title.strip())
    path = os.path.join(workspace, f"{result.article_id}-{safe_title}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"[SAVED] {path}")
else:
    print(body)
EOF
```

### 第三步：返回给用户

- 若设置了 `WECHAT_ARTICLE_EXTRACTOR_WORKSPACE`：告知用户保存路径即可，不要再读取文件展示内容。
- 若未设置：直接展示标准输出中的标题、发布时间和正文。

## 输出格式

```
文章标题

发布时间：2024-06-01 12:00:00

文章内容
```

## 批量处理

如果用户提供了多个链接，按顺序逐个解析，每篇完成后告知进度（如「已完成 2/5」）。

## 注意事项

- `article_markdown` 已是 Markdown 格式，无需二次转换。
- 文件名中的非法字符（`\ / : * ? " < > |`）和所有空白字符（空格、换行、制表符等）会被替换为 `_`，避免保存失败并便于命令行操作。
- 微信偶发触发风控（`WeChatVerifyError`），出现时建议用户稍后重试或更换网络/代理。
- 链接已失效或被删除时 `is_valid` 为 `False`，此时不要继续保存或展示残缺内容。
