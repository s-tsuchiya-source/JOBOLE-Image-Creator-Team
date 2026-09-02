# JOBOLE Image Creator Team

**Phase 1 Benchmark Quality v2**

JOBOLE向け求人広告画像を、**VSCode Codex Chief Creative Officer + Claude 3専門家 + Python機械処理**で制作します。

## ユーザーが送るもの
必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

求人ファイル1つだけでも制作可能です。

## AI組織
```text
Human
↓
VSCode Codex = Chief Creative Officer / 最高責任者
│
├─ Claude Recruitment Analyst
├─ Claude Creative Director
└─ Claude Creative Reviewer
```

実働Claudeは3人だけです。品質改善ではAgent数を増やすより、active Agent定義とbenchmarkを調整します。

## Shared Benchmark Library
制作時の参考サンプルはここへ保存します。

```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

`.env`:
```env
ORIGINAL_IMAGE_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
REFERENCE_SHORTLIST_MAX=3
REFERENCE_CONTACT_SHEET_MAX=24
CREATIVE_ROUTE_MAX=2
FACT_CHIP_MAX=3
REVISION_MAX=2
```

Pythonは参考画像の良し悪しを判断しません。
`scripts/prepare_creative_context.py` がcatalog/contact sheetを作り、Codex CCOが案件に合う参考を最大3件選びます。

## Google Drive Project Hard Rule
画像制作依頼を受けたら、Claude分析より先に案件を作成します。

```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

```text
projects/
└─ PJ-XXXX_案件名/
   ├─ project.yaml
   ├─ 00_request/
   ├─ 01_strategy/
   ├─ 02_direction/
   ├─ 03_batches/
   ├─ 04_project_review/
   └─ 05_delivery/
```

案件外のDesktop/repo/tmpへ正式成果物を代替保存しません。

## Token-Efficient Context
案件作成後、Claudeを呼ぶ前にCodexが実行します。

```powershell
python scripts/prepare_creative_context.py --project-id PJ-XXXX
```

生成:
```text
00_request/normalized/
├─ creative-context.json
├─ source-bundle.md
└─ reference_library/
   ├─ reference-catalog.json
   └─ reference-contact-sheet-01.jpg ...
```

`creative-context.json` をAI間の一次入力にします。
raw CSV全文を3Agentへ毎回渡さず、Fact疑義がある箇所だけ原文へ戻ります。

## Hearing Priority
ヒアリングの明示条件はgeneric defaultより優先します。

例:
```text
ヒアリング: JOBOLE（4:3）
↓
configs/media.yaml
↓
resolved_output_spec: 1200x900 / 4:3
↓
画像生成も4:3で固定
```

1200x628のgeneric defaultへ勝手に戻しません。

## 3 Claude Specialists

### Recruitment Analyst
担当:
- exact role / employment type
- Fact / Evidence
- Advertising Leverage
- Claim Boundary
- Job Reality
- hearingとFactの分離

求人に1職種しかなければ別職種を追加しません。正社員だけならアルバイト等を追加しません。

出力: compact JSON

### Creative Director
担当:
- hearing alignment
- benchmark translation
- message strategy
- Copy
- Art Direction
- Typography Direction
- Image Prompt

原則Visual Routeは最大2案。参考サンプルが人物写真主体なら、理由なく抽象図形主体へ逃げません。

目標:
- 1〜2秒で主訴求
- 3秒で仕事内容＋魅力
- 人物/仕事写真主体
- 大きく広告らしい日本語Headline
- 1つの主アクセントカラー
- 装飾は補助
- UIカードを並べただけの見た目を避ける

出力: compact JSON

### Creative Reviewer
独立Reviewerとして以下をblockします。
- Fact誤り
- hearing無視
- 媒体比率違反
- benchmark大幅乖離
- 人物写真benchmarkなのに理由のない抽象イラスト化
- 機械的Typography
- 1秒/3秒テスト失敗
- 画像生成破綻

出力: compact JSON

## Codex CCO
`.codex/chief-creative-officer.md`

担当:
- Project作成
- compact context gate
- Fact Gate
- Benchmark Gate
- hearing/media alignment
- Direction Gate
- root-cause revision
- Final QA

ClaudeのRecommendedをそのまま採用しません。

## Standard Workflow
```text
求人ファイル [必須]
+ hearing [任意]
+ text [任意]
↓
Codex CCO
↓
Project creation
↓
Python compact context + original_image catalog/contact sheets
↓
Recruitment Analyst
↓
Codex Fact Gate
↓
Codex Benchmark Gate（最大3サンプル）
↓
Creative Director（最大2 Visual Routes）
↓
Codex Direction Gate
↓
Image Generation
↓
Python deterministic Japanese Typography
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

## Japanese Typography
重要な日本語は画像生成AIに描かせません。

```text
Image AI
→ 人物・職場・仕事内容・構図・余白

Python
→ 承認済み日本語を正確に描画
```

標準スタイル:
- `benchmark_recruit`: 参考サンプル寄り。大きなHeadline、1色アクセント、補助帯、少数Fact
- `modern_recruit`: 既存の比較的UI寄りレイアウト

デフォルトは `benchmark_recruit`。

## Formal Output
```text
03_batches/CR001/v001/background.png
03_batches/CR001/v001/image-prompt.txt
05_delivery/CR001.png
05_delivery/CR001-copy.md
```

`generate_creative.py` は `creative-context.json` を必須とし、ヒアリングで解決された媒体比率を守ります。

## Python Responsibilities
Pythonが行う:
- Project作成
- 入力抽出/compact化
- reference catalog/contact sheet
- 媒体サイズ解決
- 画像生成
- 日本語Typography
- copy.md
- リサイズ/保存

Pythonが行わない:
- Target判断
- 訴求選定
- benchmark最終選定
- Copy選定
- Art Direction
- Final QA
- AI組織オーケストレーション

## Token Efficiency Rules
- compact context first
- raw sourceはFact疑義だけ
- Agent出力はcompact JSON
- benchmark最大3
- Visual Route最大2
- Fact最大3
- Revision最大2
- 問題工程だけ再実行

## Agent Tuning
詳細:
- `.claude/agents/README.md`

優先順位:
1. `creative-director.md`
2. `creative-reviewer.md`
3. `recruitment-analyst.md`
4. `.codex/chief-creative-officer.md`
5. Renderer/Image Backend（実装問題の場合）

## Validation
```powershell
python -m pip install -r requirements.txt
python -m compileall scripts services
python scripts/validate_system.py
python scripts/validate_system.py --runtime-config
```

期待値:
```text
SYSTEM VALIDATION: PASS
Claude specialists: 3
Codex CCO: VSCode highest authority
Python AI orchestration: DISABLED
Text API keys required: NO
Compact context: REQUIRED before Claude/image generation
Benchmark library: original_image -> catalog/contact sheet -> Codex shortlist max 3
Hearing media spec: overrides generic size defaults
Final output: PROJECT_DIR/05_delivery + companion copy.md
```

## Optional `_index.csv` for original_image
参考画像が増えたら `original_image/_index.csv` を置くとPythonの候補補助精度が上がります。

推奨列:
```csv
file_path,job_category,role,theme,main_color,layout_type,media,size,notes
```

これは自動採用ではなく、Codexのbenchmark選定を軽くするmetadataです。
