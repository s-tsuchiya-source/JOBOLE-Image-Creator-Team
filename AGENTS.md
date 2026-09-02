# AGENTS.md

## Goal
求人ファイルだけでも、**案件作成 → Fact確認 → benchmark選定 → Design Spec作成 → 無料Typography Preview → 文字なし画像生成 → Python高品質Typography → Review → Drive保存**まで進める。

Phase 1 v3ではAgent数を増やさず、Codex CCO + Claude 3専門家 + Design Spec Rendererで品質を上げる。

## User Intake
必須:
- 求人ファイル 1つ以上

任意:
- ヒアリングシート
- 補足テキスト

## Source Priority
1. 求人ファイル = Fact正本
2. ヒアリング = 希望/媒体/枚数/NG/テイスト
3. 補足テキスト
4. `ORIGINAL_IMAGE_ROOT` = デザインbenchmark

## Project First
```powershell
python scripts/create_project_from_intake.py --job-posting "<求人>" --hearing "<optional>"
```

標準保存先:
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

正式成果物をDesktop/repo/tmpへ代替保存しない。

## Compact Context Before Claude
```powershell
python scripts/prepare_creative_context.py --project-id PJ-XXXX
```

`creative-context.json` を一次入力にする。raw CSVはFact疑義のみ。

## Benchmark Library
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

Pythonはcatalog/contact sheetだけ作り、Codex CCOが最大3件を選ぶ。

## Hearing Priority
ヒアリング指定はgeneric defaultより優先。

例:
```text
JOBOLE（4:3） -> 1200x900 / 4:3
```

## AI Organization
### Codex CCO
- Fact Gate
- Benchmark Gate
- Design Spec Gate
- Typography Preview Gate
- Layout Familyの使い分け
- Revision Routing
- Final QA

### Recruitment Analyst
- exact role/employment type
- Fact/Evidence
- Advertising Leverage
- Claim Boundary
- Job Reality

### Creative Director
- message strategy
- Copy
- benchmark translation
- Art Direction
- Layout Family選択
- 意味改行
- 強調語/数字
- Image Prompt
- renderer-ready Design Spec

### Creative Reviewer
- Fact/Hearing/Benchmark
- Design Spec fidelity
- Layout Family品質
- 1-second / 3-second test
- Typography
- Job Reality
- Generation Artifact

## Design Spec First
```text
Creative Director
↓
Codex Approval
↓
02_direction/CR001-design-spec.json
↓
Python Preview
↓
Codex Preview Approval
↓
Image AI = 文字なし背景
↓
Python = Design Spec通りの日本語描画
```

Pythonへデザイン判断を委譲しない。

## Layout Families
`configs/layouts.yaml`

- numeric_impact
- short_power_word
- concept_message
- work_scene
- benefit_stack
- emotional_message

複数枚案件で全て同じFamilyへ流し込まない。

## Design Spec Contract
`services/design_spec.py`

必須:
- layout_family
- accent_color
- text_zone
- headline.lines
- headline.emphasis
- image.prompt

任意:
- subcopy
- facts 最大3
- CTA
- benchmark_refs 最大3
- decorations

Headlineの意味改行はCreative Directorが決める。Python自動折返しは最終fallbackのみ。

## Preview Before Image Cost
```powershell
python scripts/preview_design_spec.py --project-id PJ-XXXX --creative-id CR001
```

確認:
- 意味改行
- 強調語/数字
- Layout Family
- Fact/CTA密度
- 余白
- テンプレ感

Previewで直せる問題のために画像AIを再生成しない。

## Fixed Workflow
```text
Human
↓
Codex CCO
↓
Project creation
↓
Python compact context + benchmark catalog/contact sheet
↓
Recruitment Analyst
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Director
↓
Codex Design Spec Gate
↓
Design Spec Preview
↓
Codex Preview Gate
↓
Image Generation (no required text)
↓
Python Design Spec Renderer
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

## Formal Output
```text
02_direction/<creative-id>-design-spec.json
02_direction/previews/<creative-id>-design-preview.png
03_batches/<creative-id>/v001/background.png
03_batches/<creative-id>/v001/image-prompt.txt
03_batches/<creative-id>/v001/design-spec.json
05_delivery/<creative-id>.png
05_delivery/<creative-id>-copy.md
```

## Generate
Preview PASS後:
```powershell
python scripts/generate_creative.py --project-id PJ-XXXX --creative-id CR001
```

## Token / Cost Efficiency
- compact context first
- raw source fallback only
- Claude出力 compact JSON
- benchmark最大3
- route最大2
- Fact最大3
- Design SpecをPreview/Renderer/Reviewerで再利用
- Revision最大2
- root cause工程だけ再実行
- PreviewでTypography問題を先に潰す

## Python Responsibilities
やってよい:
- Project作成
- file extraction
- compact context
- benchmark catalog/contact sheet
- media size resolution
- Design Spec validation
- typography preview
- image generation
- exact Japanese rendering
- copy.md / save / resize

やってはいけない:
- Target/訴求/Copy判断
- benchmark最終選定
- Layout Family選定
- Headline意味改行判断
- Art Direction判断
- Final QA

## Quality Blockers
- wrong role/employment type
- unsupported claim
- hearing/media mismatch
- benchmark quality mismatch
- Design Spec mismatch
- mechanical template repetition
- inaccurate/unreadable text
- major generation artifact

## Local Renderer Test
```powershell
python scripts/test_design_renderer.py
```

6 Layout Familyを画像APIなしで確認できる。
