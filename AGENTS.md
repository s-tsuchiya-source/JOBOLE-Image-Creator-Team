# AGENTS.md

## Goal
求人ファイルだけでも、**Project → Fact → Benchmark → Premium Creative Spec → 文字込み完成広告Candidate → Text/Creative Review → Formal Delivery**まで進める。

標準はPremium Integrated AI。Safe Python Typographyはfallback。

## User Intake
必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

## Source Priority
1. 求人ファイル = Fact正本
2. ヒアリング = 希望/媒体/枚数/NG/テイスト
3. 補足テキスト
4. `ORIGINAL_IMAGE_ROOT` = design benchmark

## Project First
最初に案件を作る。

```powershell
python scripts/create_project_from_intake.py --job-posting "<求人>" --hearing "<optional>"
```

正式保存先:
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

## Compact Context
```powershell
python scripts/prepare_creative_context.py --project-id PJ-XXXX
```

`creative-context.json` を一次入力にする。raw sourceはFact疑義だけ。

## Benchmark
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

Pythonはcatalog/contact sheet。Codex CCOが最大3件を選ぶ。

## Active AI Organization
### Codex CCO
最高責任者。
- Project Gate
- Fact Gate
- Benchmark Gate
- Premium Creative Spec Gate
- Text Integrity Gate
- Safe fallback decision
- Final QA
- Formal delivery approval

### Recruitment Analyst
- exact Fact/Evidence
- Claim Boundary
- Advertising Leverage
- verbatim claims
- critical numeric facts
- Job Reality

### Creative Director
- Strategy/Copy
- Benchmark Translation
- Art/Photo Direction
- Integrated Typography Direction
- Exact Text Contract
- Premium Image Prompt

### Creative Reviewer
- Fact/Hearing/Benchmark
- image visual text readback
- OCR assessment
- Copy/Visual/Typography
- Job Reality/Generation Quality
- delivery blocker

## Premium Mode
Default:
```env
CREATIVE_RENDER_MODE=premium_ai
PREMIUM_IMAGE_BACKEND=openai
```

Creative Director outputs:
```text
02_direction/<creative-id>-creative-spec.json
```

Premium image AI generates:
- photo
- background
- decoration
- Japanese typography
- exact contracted copy

Python does NOT overlay text in Premium Mode.

## Exact Text Contract
Each required block has:
- id
- role
- exact text
- required
- fact_ids
- line-break flexibility
- priority

Image AI may change visual line breaks only when permitted; characters, digits, punctuation and meaning must stay exact.

## Candidate First
Generate:
```powershell
python scripts/generate_creative.py --project-id PJ-XXXX --creative-id CR001
```

Output:
```text
03_batches/CR001/v001/candidate.png
03_batches/CR001/v001/creative-spec.json
03_batches/CR001/v001/expected-copy.md
04_project_review/CR001-v001-text-verification.json
```

**未審査Candidateを05_deliveryへ直接保存しない。**

## Text Verification
3 layers:
1. Local OCR if available
2. Claude Reviewer visual readback mandatory
3. Codex final visual check mandatory

Optional OCR:
```powershell
python scripts/verify_generated_text.py --project-id PJ-XXXX --creative-id CR001 --version v001
```

OCRは唯一の正解ではない。

## Review Rules
Automatic blocker:
- wrong role/employment type
- unsupported claim
- wrong number/unit
- missing required text
- misspelled required text
- invented extra text
- hearing/media mismatch
- benchmark quality mismatch
- unreadable typography
- weak integrated design
- major generation artifact

## Safe Mode
Premiumで同じrequired text errorが原則2回続く場合、Codexが判断して:

```powershell
python scripts/generate_creative.py --project-id PJ-XXXX --creative-id CR001 --mode safe_python
```

旧Design Spec + Python Rendererを利用。

## Formal Promotion
Codex Final Approval JSON必須。

```powershell
python scripts/promote_creative.py --project-id PJ-XXXX --creative-id CR001 --version v001 --approval-file "<approval.json>"
```

Approval flags:
- creative_reviewer_pass
- codex_final_qa_pass
- fact_integrity_pass
- text_integrity_pass

## Token Efficiency
- compact context first
- raw source fallback only
- Agent output compact JSON
- benchmark max 3
- route max 2
- required text typical max 5 / hard max 6
- Creative Spec reuse downstream
- OCR全文をAIへ渡さない
- revisionはroot causeのみ
- 全Agent再実行禁止

## Python Responsibilities
Allowed:
- Project/input/context
- benchmark indexing
- media size
- spec validation
- image backend call
- OCR helper
- deterministic text comparison
- candidate/version management
- promotion
- Safe Mode renderer

Not allowed in Premium:
- Copy decision
- Art Direction
- Typography design
- benchmark final selection
- Creative Final QA

## Formal Output
```text
05_delivery/<creative-id>.png
05_delivery/<creative-id>-copy.md
05_delivery/<creative-id>-approval.json
```

Formal output exists only after explicit promotion.

## Detailed Design
`docs/premium-integrated-ai-v4.md`
