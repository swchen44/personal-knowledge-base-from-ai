---
name: add-article
description: Standard SOP for adding a new knowledge note to this personal knowledge base. Ensures consistent formatting, tagging, and Obsidian compatibility.
license: MIT
allowed-tools: read write
metadata:
  author: swchen44
    version: "1.0.0"
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
      category: AI  # One of the categories above
      tags:
        - tag1
          - tag2
            - tag3
            source: "https://original-url.com"
            source_type: article  # article | video | paper | tool | book | podcast
            author: "Original Author Name"
            status: notes  # notes | reviewed | complete
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

                ## Quality Checklist

                - [ ] Frontmatter is complete (title, date, tags, source, links)
                - [ ] File name is ALL-CAPS with hyphens
                - [ ] Correct category folder
                - [ ] At least 3 tags
                - [ ] At least 1 `links` reference to a related note (if applicable)
                - [ ] README.md updated
