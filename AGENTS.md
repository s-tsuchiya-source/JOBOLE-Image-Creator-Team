# AGENTS.md

## Goal
ユーザーがVSCode Codexへ求人ファイルを渡すだけでも、**案件作成 → Fact確認 → benchmark選定 → Creative設計 → 画像生成 → Review → Google Drive保存**まで進められる状態を維持する。

Phase 1では量産より納品品質を優先する。ただしAgentを増やして複雑化せず、Codex CCO + Claude 3専門家で運用する。

## User Intake
必須:
- 求人ファイル 1つ以上

任意:
- ヒアリングシート
- 補足テキスト

求人ファイルが正常に読めれば、ヒアリング無しでも制作可能。

## Source Priority
1. 求人ファイル = Fact正本
2. ヒアリング = 希望/媒体/枚数/NG/テイスト
3. 補足テキスト = 追加希望
4. `ORIGINAL_IMAGE_ROOT` = デザインbenchmark

## Hard Rule: Project First
Claude分析より先に:

```powershell
python scripts/create_project_from_intake.py --job-posting "<求人>" --hearing "<hearing optional>"
```

標準:
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

取得:
- PROJECT_ID
- PROJECT_DIR
- QUANTITY
- QUANTITY_SOURCE

ヒアリングCSVに `制作枚数` があれば、明示 `--quantity` が無い限り自動採用する。

案件作成失敗時にDesktop/repo/tmpへ正式成果物を代替保存しない。

## Hard Rule: Compact Context Before Claude
案件作成後:

```powershell
python scripts/prepare_creative_context.py --project-id PJ-XXXX
```

生成:
- `creative-context.json`
- source index/bundle
- original_image catalog
- original_image contact sheet
- resolved output spec

Claudeへの一次入力はcompact context。raw CSVはFact疑義時だけ読む。

## Benchmark Library
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

`.env`:
```env
ORIGINAL_IMAGE_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
REFERENCE_SHORTLIST_MAX=3
```

Pythonはcatalog/contact sheetだけ作る。最終benchmark選定はCodex CCO。
Creative Directorへ渡す参考は最大3件。

## Hearing Overrides Generic Defaults
ヒアリングに媒体・サイズ・枚数等の明示がある場合はgeneric defaultより優先。

例:
```text
JOBOLE（4:3） -> configs/media.yaml -> 1200x900 / 4:3
```

4:3指定案件を1200x628で生成しない。

## AI Organization
### Codex CCO
最高責任者。
- Project確認
- compact context gate
- Fact Gate
- Benchmark Gate
- hearing/media alignment
- Direction Gate
- Revision Routing
- Final QA

詳細: `.codex/chief-creative-officer.md`

### Recruitment Analyst
- exact role/employment type
- Fact/Evidence
- Advertising Leverage
- Claim Boundary
- Job Reality
- hearingとFactの分離

別職種・別雇用形態を勝手に追加しない。

### Creative Director
- benchmark translation
- message strategy
- Copy
- Visual Route
- Art Direction
- Typography Direction
- Image Prompt

原則route最大2。人物写真benchmarkなら理由なく抽象イラストへ逸脱しない。

### Creative Reviewer
- Fact/Hearing/Benchmark blocker
- 1-second / 3-second test
- Copy/Typography/Job Reality
- Generation Artifact
- Root Cause Routing

読めるだけでPASSしない。

## Fixed Workflow
```text
Human
↓
Codex CCO
↓
Project creation
↓
Python compact context + original_image catalog/contact sheet
↓
Recruitment Analyst
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Director
↓
Codex Direction Gate
↓
Image Generation + deterministic Japanese Typography
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

## Output Contract
正式成果物:
```text
03_batches/<creative-id>/v001/background.png
03_batches/<creative-id>/v001/image-prompt.txt
05_delivery/<creative-id>.png
05_delivery/<creative-id>-copy.md
```

`generate_creative.py` は:
- `--project-id` 必須
- `creative-context.json` 必須
- hearing-resolved aspect ratioを尊重
- Fact最大 `FACT_CHIP_MAX`
- デフォルト `benchmark_recruit`

## Typography
日本語重要文言を画像AIへ描かせない。

```text
Image AI -> 人物/職場/仕事/構図/余白
Python -> 正確な日本語Typography
```

標準:
- `benchmark_recruit`: 大きなHeadline + 1色アクセント + 補助帯 + 少数Fact
- `modern_recruit`: 比較用の従来レイアウト

## Token Efficiency
- compact context first
- raw source fallback only
- Claude出力はcompact JSON
- benchmark最大3
- route最大2
- Fact最大3
- Revision最大2
- root cause工程だけ再実行
- 同じCSV全文を複数Agentへ繰り返し渡さない

## Python Responsibilities
やってよい:
- Project作成
- CSV/docx/xlsx/pdf抽出
- compact context
- benchmark catalog/contact sheet
- 媒体サイズ解決
- 画像生成
- Typography
- copy.md
- リサイズ/保存

やってはいけない:
- benchmark最終選定
- Target/訴求/Copy/Art Directionの判断
- Claude承認
- Codex Final QA
- AI組織自動オーケストレーション

## Quality Blockers
- wrong role
- wrong employment type
- unsupported claim
- hearing/media mismatch
- benchmark quality mismatch
- abstract/generic visual that loses job reality without approved reason
- mechanical typography
- inaccurate/unreadable text
- major generation artifact

## Success Condition
納品判断できる実画像を案件内へ作り、人間が:
- Fact
- hearing alignment
- benchmark alignment
- Copy
- Typography
- Job Reality
- Ad Impact

を評価できること。
