# WeChat Article Extractor

解析微信公众号文章链接的 Claude Code Skill。基于 [wechat-article-parser](https://github.com/huanjuedadehen/wechat-article-parser) 提取文章的标题、发布时间和正文 Markdown，可选择直接展示或保存到本地工作目录。

## 功能特性

- **结构化提取**：标题、发布时间（人类可读格式）、正文 Markdown 一次返回。
- **时间戳转换**：自动把秒级 Unix 时间戳转为 `YYYY-MM-DD HH:MM:SS`。
- **可选落盘**：设置工作目录后，按 `{article_id}-{article_title}.md` 命名保存；未设置则直接返回给用户。
- **依赖自管理**：每次执行前以 `pip install --upgrade` 确保解析包为最新版本。
- **批量处理**：支持一次传入多个链接，按序处理并报告进度。
- **错误兜底**：识别微信风控（`WeChatVerifyError`）和文章失效（`is_valid=False`）两种失败场景。

## 目录结构

```
wechat-article-extractor/
├── README.md
└── SKILL.md    # Skill 主定义与执行流程（解析逻辑以内联 Python 形式包含其中）
```

## 配置

### 环境变量（可选）

`WECHAT_ARTICLE_EXTRACTOR_WORKSPACE`：解析结果保存目录。

- **若设置**：结果以 `{article_id}-{article_title}.md` 的格式保存到该目录。
- **若未设置**：结果直接返回给用户，不落盘。

推荐在 `~/.claude/settings.json` 的 `env` 字段中配置：

```json
{
  "env": {
    "WECHAT_ARTICLE_EXTRACTOR_WORKSPACE": "~/Workspace/wechat-articles"
  }
}
```

## 使用方式

该 Skill 设置了 `disable-model-invocation: true`，需用户主动调用。在 Claude Code 中输入 `/wechat-article-extractor` 并附上微信文章链接即可：

```
/wechat-article-extractor https://mp.weixin.qq.com/s/xxxxx
```

也可以一次传入多个链接批量处理。

## 输出格式

```
文章标题

发布时间：2024-06-01 12:00:00

文章内容（Markdown）
```

设置了工作目录时，文件会保存到：

```
$WECHAT_ARTICLE_EXTRACTOR_WORKSPACE/{article_id}-{article_title}.md
```

文件名中的非法字符（`\ / : * ? " < > |`）和所有空白字符（空格、换行、制表符等）会被替换为 `_`，避免保存失败并便于命令行操作。

## 依赖

- Python ≥ 3.10
- [`wechat-article-parser`](https://pypi.org/project/wechat-article-parser/)（Skill 会在每次运行时自动安装/升级）

## 故障排查

| 现象 | 可能原因 | 处理建议 |
| --- | --- | --- |
| `WeChatVerifyError` | 微信触发安全验证 | 稍后重试，或更换网络/代理 |
| `is_valid=False` | 文章已失效或被删除 | 确认链接是否仍可访问 |
| `pip install` 失败 | Python 版本低于 3.10 | 升级 Python 后重试 |
