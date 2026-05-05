# My Skills

个人编写的 [Claude Code Skill](https://docs.claude.com/en/docs/claude-code/skills) 集合。每个子目录是一个独立 Skill，包含自身的 `SKILL.md`（定义与执行流程）和 `README.md`（详细说明）。

## Skills 列表

| Skill | 说明 |
| --- | --- |
| [youtube-summarizer](skills/youtube-summarizer/) | 对 YouTube 视频字幕生成结构化中文摘要，长视频自动分段处理。 |
| [wechat-article-extractor](skills/wechat-article-extractor/) | 解析微信公众号文章链接，提取标题、发布时间和正文 Markdown。 |

## 安装

### 方式 1：使用 [`skills`](https://github.com/vercel-labs/skills) CLI（推荐）

`skills` 是一个开源的 agent skills 安装工具，会自动扫描仓库内的 `SKILL.md` 并把它们符号链接到对应 agent 的目录（Claude Code 默认是 `~/.claude/skills/`）。

```bash
# 列出本仓库提供的所有 skills
npx skills add huanjuedadehen/skills --list

# 全局安装全部 skills（-g 表示装到 ~/.claude/skills）
npx skills add huanjuedadehen/skills -g

# 只装指定 skill
npx skills add huanjuedadehen/skills --skill youtube-summarizer -g
npx skills add huanjuedadehen/skills --skill wechat-article-extractor -g
```

### 方式 2：手动克隆 + 软链接

```bash
git clone git@github.com:huanjuedadehen/skills.git ~/Workspace/github/huanjuedadehen-skills

# 把整个 skills/ 目录链接到 ~/.claude/skills
ln -s ~/Workspace/github/huanjuedadehen-skills/skills ~/.claude/skills

# 或只链接需要的 Skill
mkdir -p ~/.claude/skills
ln -s ~/Workspace/github/huanjuedadehen-skills/skills/youtube-summarizer ~/.claude/skills/youtube-summarizer
```

各 Skill 自身的环境变量、依赖、配置方式见对应子目录的 `README.md`。

## 使用

本仓库内的 Skill 都设置了 `disable-model-invocation: true`，需用户主动通过 `/<skill-name>` 调用，例如：

```
/youtube-summarizer https://www.youtube.com/watch?v=xxxxx
/wechat-article-extractor https://mp.weixin.qq.com/s/xxxxx
```

## 目录结构

```
my-skills/
├── README.md
└── skills/
    ├── youtube-summarizer/
    │   ├── README.md
    │   ├── SKILL.md
    │   └── scripts/
    └── wechat-article-extractor/
        ├── README.md
        └── SKILL.md
```
