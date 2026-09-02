# Design Spec v3

## Purpose
画像AIへ日本語文字を描かせず、Claude Creative Directorが広告デザイン判断をJSON化し、Pythonが正確に再現する。

## Required flow
```text
creative-context.json
+ Fact JSON
+ benchmark max 3
↓
Creative Director
↓
design_spec
↓
Codex approval
↓
preview_design_spec.py
↓
Codex preview approval
↓
generate_creative.py
```

## Layout families
- numeric_impact
- short_power_word
- concept_message
- work_scene
- benefit_stack
- emotional_message

## Example
```json
{
  "version": "1.0",
  "layout_family": "numeric_impact",
  "accent_color": "#1F95B4",
  "text_zone": "left",
  "headline": {
    "lines": ["月給33万750円〜", "42万8,750円"],
    "emphasis": ["33万750円", "42万8,750円"]
  },
  "subcopy": {"text": "児童発達支援管理責任者"},
  "facts": ["駅徒歩4分", "交通費全額支給"],
  "cta": {"text": "詳しく見る"},
  "image": {
    "prompt": "realistic recruitment photo ...",
    "negative_prompt": "text, watermark, malformed hands"
  },
  "benchmark_refs": ["R0001"],
  "decorations": {
    "accent_bar": true,
    "rays": false,
    "soft_shape": true,
    "bottom_band": false
  }
}
```

## Responsibility boundary
### Claude / Codex
- Copy
- semantic line breaks
- emphasis
- layout family
- benchmark translation
- visual direction
- accent color

### Python
- validation
- exact text rendering
- font sizing within approved boundaries
- layout execution
- output size
- file saving

Python must not invent copy or change semantic line breaks unless the approved text physically cannot fit; in that case rendering fails and returns to Creative Director rather than silently shrinking into unreadable text.
