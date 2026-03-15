---
name: add-article
description: Standard SOP for adding a new knowledge note to this personal knowledge base. Ensures consistent formatting, tagging, and Obsidian compatibility.
license: MIT
allowed-tools: read write
metadata:
  author: swchen44
  version: "1.1.0"
  category: knowledge-management
---

# Add Article — Standard SOP

## Purpose
This skill defines the step-by-step process for adding any new piece of knowledge (article, video, research paper, tool, etc.) to this knowledge base in a consistent, Obsidian-compatible format.

---

## Steps

### 1. Determine the Category

Choose the correct folder based on the content type:

| Category | Use when... |
|----------|-------------|
| `AI/` | AI frameworks, LLMs, agents, prompting, ML |
| `DevTools/` | Developer tools, CLIs, SDKs, editors, platforms |
| `WebArticles/` | Blog posts, news articles, opinion pieces |
| `Videos/` | YouTube videos, conference talks, tutorials |
| `Research/` | Academic papers, technical deep dives |
| `Productivity/` | Workflows, personal systems, GTD, tools |
| `Finance/` | Economics, investing, fintech, crypto |
| `Design/` | UI/UX, product design, visual thinking |
| `Science/` | Physics, biology, astronomy, general science |
| `Books/` | Book summaries and key highlights |
| `OpenSource/` | Open source projects and communities |
| `Security/` | Cybersecurity, privacy, infosec |

### 2. Create the File

- File location: `CATEGORY/NOTE-TITLE-IN-CAPS.md`
- File name: ALL CAPS with hyphens, English only
- Example: `AI/GITAGENT-FRAMEWORK-ANALYSIS.md`

### 3. Fill in the Frontmatter

Every note MUST start with this YAML frontmatter block:

```yaml
---
title: "Full Title of the Note"
date: YYYY-MM-DD
category: AI
tags:
  - tag1
  - tag2
  - tag3
source: "https://original-url.com"
source_type: article
author: "Original Author Name"
status: notes
links:
  - "[[RELATED-NOTE-1]]"
  - "[[RELATED-NOTE-2]]"
---
```

### 4. Write the Note Body

Use this structure:

```markdown
## Summary
One paragraph describing what this is about and why it matters.

## Key Insights
- Insight 1
- Insight 2
- Insight 3

## Details
(Deeper notes, code snippets, diagrams, quotes)

## My Takeaways
What I learned and how I might apply it.

## Related
- [[RELATED-NOTE-1]]
- [[RELATED-NOTE-2]]
```

### 5. Update README.md

Add a line under `## 📌 Recent Notes` in the root `README.md`:

```markdown
- [NOTE-TITLE](./CATEGORY/NOTE-TITLE.md) — One-line description
```

---

## 📺 YouTube Knowledge Graph Workflow

A dedicated workflow for the `Videos/` category to extract, transcribe, and convert YouTube content into structured knowledge notes — including videos with no subtitles.

### Method 1: yt-dlp (Recommended — works on most videos)

Use when the video has official or auto-generated captions.

```bash
# Install yt-dlp
pip install yt-dlp

# Download auto-generated subtitles (Traditional Chinese first, then Simplified, then English)
yt-dlp --write-auto-sub --sub-lang "zh-Hant,zh-Hans,en" --skip-download "YOUTUBE_URL"

# Convert to SRT format
yt-dlp --write-sub --write-auto-sub --convert-subs srt --skip-download "YOUTUBE_URL"

# Also grab the video description text
yt-dlp --write-description --write-auto-sub --skip-download "YOUTUBE_URL"
```

### Method 2: Python youtube-transcript-api

Use when you need to batch-process multiple videos programmatically.

```python
from youtube_transcript_api import YouTubeTranscriptApi

video_id = "VIDEO_ID"  # Extract from URL: ?v=VIDEO_ID

# Try Chinese first, fall back to English
transcript = YouTubeTranscriptApi.get_transcript(
    video_id, languages=["zh-Hant", "zh-Hans", "en"]
)

# Join into full transcript
full_text = " ".join([t["text"] for t in transcript])
print(full_text)
```

Install: `pip install youtube-transcript-api`

### Method 3: No Subtitles — Whisper AI Auto-Transcription

Use when a video has absolutely no subtitles (no manual or auto-generated captions).

```bash
# Step 1: Download audio only with yt-dlp
yt-dlp -f "bestaudio" -o "audio.%(ext)s" "YOUTUBE_URL"

# Step 2: Install and run OpenAI Whisper
pip install openai-whisper
whisper audio.mp4 --language Chinese --output_format txt

# Faster alternative
pip install faster-whisper
```

Python example:

```python
import whisper

model = whisper.load_model("base")  # Options: tiny / base / small / medium / large
result = model.transcribe("audio.mp4", language="zh")
print(result["text"])
```

### Method 4: Google NotebookLM (No-Code Option)

Use when you want a fast AI-generated summary without writing any code.

1. Go to https://notebooklm.google.com/
2. Add Source → paste the YouTube video URL
3. NotebookLM auto-fetches subtitles and generates a knowledge summary
4. Use the Q&A panel to extract key points
5. Copy the output and paste into this repo's Note Body format

> Best for: TED Talks, tech talks, tutorial videos that have captions.

### Method 5: Claude AI Summarization (Fastest)

1. Get the transcript text using Method 1 or 2
2. Paste into Claude with this prompt:
   > "Please turn this YouTube transcript into a structured knowledge note with: Summary, Key Insights, Key Concepts, and My Action Items"
3. Paste Claude's output into the Note Body format and save to `Videos/`

---

### Videos/ Frontmatter Template

Add these extra fields when creating a Videos note:

```yaml
---
title: "Video Title"
date: YYYY-MM-DD
category: Videos
source_type: video
source: "https://youtube.com/watch?v=VIDEO_ID"
channel: "Channel Name"
duration: "00:00"
transcript_method: yt-dlp
tags:
  - youtube
  - tag2
---
```

`transcript_method` options: `yt-dlp` | `whisper` | `notebooklm` | `manual`

### YouTube Note Quality Checklist

- [ ] Transcript or summary obtained (method recorded in frontmatter)
- [ ] `channel` field filled in
- [ ] `transcript_method` field set
- [ ] Video URL included (clickable link back to YouTube)
- [ ] Video description text included in Details section (if available)

---

## Quality Checklist

- [ ] Frontmatter is complete (title, date, tags, source, links)
- [ ] File name is ALL-CAPS with hyphens
- [ ] Correct category folder
- [ ] At least 3 tags
- [ ] At least 1 `links` reference to a related note (if applicable)
- [ ] README.md updated
