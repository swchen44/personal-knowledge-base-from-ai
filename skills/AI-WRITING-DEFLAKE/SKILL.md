---
name: ai-writing-deflake
description: >
  Scan AI-generated Traditional Chinese copy for the "8 Pitfalls of AI Writing"
  identified by 吳淡如 (50 years of writing experience). Detects: (1) 不是...而是 pattern,
  (2) 換句話說 redundancy, (3) forced emotional interpretation, (4) forced sublimation,
  (5) forced drama, (6) "有人說" lazy anchoring, (7) stiff emotion labels & English-translation tone,
  (8) pretentious hollow terminology. Outputs a lint-style report (error/warning/info)
  rather than auto-rewriting — final edit decisions belong to the human author.
license: MIT
allowed-tools: read
metadata:
  author: swchen44
  version: "1.0.0"
  category: writing-quality
  derived_from: "[[2026-05-13-WHY-YOUR-AI-COPY-LOOKS-FAKE-8-AI-WRITING-PITFALLS]]"
---

# AI 寫作除味 (AI Writing Deflake) — 8 大地雷檢查

> 本技能 (Skill) 根據吳淡如 EP5「為什麼你的 AI 文案這麼假？」拆解出的 8 大地雷，
> 用 lint 思維檢查 AI 產出的中文文案。**不自動改寫**——只標出可疑之處，最終由人類決定。

## 何時使用 (When to Use)

- 收到 AI 產出的文章草稿、PR description、產品文案、簡報稿
- 自己用 ChatGPT/Claude/Gemini 寫的中文初稿要送出之前
- 審閱同事/小編用 AI 生成的內容
- 處理長文「精煉化」階段（先讓 AI 寫長，再用此 skill 找出可刪段落）

## 何時不要使用 (When NOT to Use)

- **學術論文 / 法律文書**：這類文體本來就需要「不是 X 而是 Y」精確界定
- **教學內容**：需要先擊破誤解再建立新觀念，「不是……而是」反而是教學優勢
- 純英文文章（地雷規則為中文 AI 寫作特徵）

## 8 大地雷檢查規則 (8 Pitfall Detection Rules)

### Rule 1: 「不是……而是……」句型 — ❌ Error

**偵測 (Detection)**：
- Regex：`不是.{0,30}而是` 或 `不是.{0,30}，?而是`
- 一段內出現 ≥ 2 次：升級為 ❌ Error；出現 1 次：⚠️ Warning

**修正建議 (Fix Suggestion)**：
- 改為直接陳述：刪除「不是 X」前綴，保留「而是 Y」
- 例：「真正的財富不是口袋裡的數字，而是你對世界的認知」→「真正的財富是你對這世界的認知」

### Rule 2: 「換句話說」過度囉唆 — ⚠️ Warning

**偵測**：
- 同一段內出現「換句話說」「也就是說」「換言之」「簡單來說」≥ 2 次
- 或前後句字面差異 < 30%（語意重複）

**修正建議**：
- 套用原則：「**每一句話都要有新增資訊**」
- 刪除重複句，只留最具體的那一句

### Rule 3: 強行解釋情緒與過度下結論 — ⚠️ Warning

**偵測**：
- 句型模式：`他/她終於明白了...` / `她/他這才意識到...` / `突然頓悟...`
- 每段結尾都出現「金句式」收束（短句 + 哲理感）

**修正建議**：
- 檢查是否有真實邏輯支持
- 移除「悟到了什麼」的生硬轉折

### Rule 4: 強行昇華 / 小題大作 — ❌ Error

**偵測**：
- 關鍵詞配對：小事件 + 「深刻對話 / 全宇宙 / 人性 / 哲學 / 本質 / 終極」
- 例：「孩子拒絕棉花糖，這其實是一場關於人性慾望與自我克制的深刻對話」

**修正建議**：
- 把昇華語句刪掉，只保留事件本身
- 規模對等原則：小事用小描述，大事才用大道理

### Rule 5: 強行製造戲劇感 — ⚠️ Warning

**偵測**：
- 轉折詞密度：「然而 / 然而真正的 / 但這只是開始 / 真正的問題才剛要開始」每 300 字出現 ≥ 3 次
- 每段第一句都是轉折開頭

**修正建議**：
- 縮減轉折詞至最多每 500 字 1 次
- 先讓 AI 寫長（700-800 字）再人工剪裁為 300-400 字

### Rule 6: 「有人說」腐爛句法 — ❌ Error

**偵測**：
- 直接 grep：`有人說` / `有些人認為` / `據說` / `坊間流傳`
- **任何一次出現**都標 Error，因為這幾乎是 AI 寫作的 fingerprint

**修正建議**：
- 強制要求「**指名道姓**」：是誰說的？哪一份研究？哪一年？
- 若查不到出處，直接刪除整句
- 工具建議：用 Gemini（背後是 Google 搜尋）查證來源

### Rule 7: 生硬情緒標籤與英文翻譯感 — ⚠️ Warning

**偵測**：
- 句首「這……」氾濫：每 200 字出現 ≥ 3 次的「這令人」「這顯示」「這代表」
- 直接情緒詞彙：「令人心酸」「孤獨」「無奈」「悲涼」當作標籤使用

**修正建議**：
- 用**意象**取代情緒詞：「一江春水向東流」優於「她的離開令人心酸」
- 刪除句首多餘的「這」

### Rule 8: 結構性的空洞 / 吊書袋 — ❌ Error

**偵測**：
- 「結構性的 X」「系統性的 X」「本質上的 X」這類抽象修飾語
- 名詞化過度：「進行 X」「展開 Y」「實現 Z」
- 反問 AI：該詞彙與前後文的具體關聯是什麼？

**修正建議**：
- 反問法：對 AI 說「請解釋這個術語跟前文的具體關聯」
- 若 AI 無法說明 → 直接刪除或替換為具體描述

## 輸出格式 (Output Format)

```markdown
## AI 寫作除味檢查報告

📝 **檢查文本**：{文章標題/段落 ID}
📏 **總字數**：{N}
🚨 **整體評分**：{0-100，扣分制}

### ❌ Errors（{N} 條）

1. **[Rule 1 — 不是而是]** Line 12-13
   原文：「真正的財富不是口袋裡的數字，而是你對世界的認知」
   建議：「真正的財富是你對這世界的認知」

### ⚠️ Warnings（{N} 條）

1. **[Rule 3 — 強行解釋情緒]** Line 45
   原文：「他終於明白了，什麼才是家」
   建議：補充前文邏輯，或刪除此句

### ℹ️ Info（{N} 條）

...

### 💡 整體建議

- 字數先長後短策略：建議先讓 AI 寫到 {X} 字，再剪裁為 {Y} 字
- 高密度地雷段落：第 {N} 段（5 個地雷集中）建議整段重寫
```

## 實作骨架 (Implementation Skeleton)

```python
import re
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class LintFinding:
    rule_id: int
    severity: Literal["error", "warning", "info"]
    line: int
    snippet: str
    suggestion: str

RULES = {
    1: {  # 不是...而是
        "pattern": re.compile(r"不是.{0,30}，?而是"),
        "threshold": 2,  # 段內 >=2 次為 error
        "severity_low": "warning",
        "severity_high": "error",
    },
    6: {  # 有人說
        "pattern": re.compile(r"有人說|有些人認為|據說|坊間流傳"),
        "threshold": 1,
        "severity_low": "error",
        "severity_high": "error",
    },
    # ... 其他規則
}

def lint_chinese_ai_text(text: str) -> List[LintFinding]:
    findings = []
    paragraphs = text.split("\n\n")
    for p_idx, p in enumerate(paragraphs):
        for rule_id, rule in RULES.items():
            matches = rule["pattern"].findall(p)
            if not matches:
                continue
            severity = rule["severity_high"] if len(matches) >= rule["threshold"] else rule["severity_low"]
            findings.append(LintFinding(
                rule_id=rule_id,
                severity=severity,
                line=p_idx,
                snippet=p[:80],
                suggestion=f"參見 Rule {rule_id} 修正建議",
            ))
    return findings
```

## 進階用法 (Advanced Usage)

### 與 LLM 整合：自動修正建議

把本 skill 的偵測結果丟給 LLM，要求它**逐條解釋為何觸發**並提供修正版本：

```
請對以下 AI 寫作內容套用 8 大地雷檢查：
{原文}

對每一條觸發的規則，請：
1. 引用觸發句
2. 說明為什麼這違反規則 N
3. 提供 2 種修正版本（保守版 + 激進版）
```

### 與「先長後短」工作流結合

```
Step 1: 讓 AI 寫長文（目標字數的 2-2.5 倍，例如 700-800 字）
Step 2: 用 ai-writing-deflake 標記地雷
Step 3: 人工選擇刪除哪些段落
Step 4: 最終字數收斂到 300-400 字
```

## 引用 (References)

- 來源筆記：[[2026-05-13-WHY-YOUR-AI-COPY-LOOKS-FAKE-8-AI-WRITING-PITFALLS]]
- 原始影片：[吳淡如 EP5](https://www.youtube.com/watch?v=eIeqTmCM9Vo)
- 互補 skill：[[ADD-ARTICLE]]（撰寫筆記 SOP，本 skill 可作為其後處理階段）
