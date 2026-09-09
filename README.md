# JOBOLE Image Creator Team

2026-09-07に、添付 `jobole-agents-set.zip` の11件を `.claude/agents/` の正式定義へ反映し、同名旧版を置き換えました。[正式版一覧と接続状況](.claude/agents/README.md)を参照してください。以下は既存v5フローの説明です。新定義とのschema・出力形式の接続は未対応です。

**Phase 1 Codex Native ImageGen v5**

JOBOLE向け求人広告画像を、**最高責任者のCodex CCOが指揮するCodex Integrated Creative DesignerとClaude専門Agent**で制作します。正式なClaude Agentは11役割、以下の図は既存v5経路の基本構成です。

## 最重要方針
Codex CCO自身が案件内容を理解し、各Claude Agentへの作業指示・成果物レビュー・修正指示・再レビュー・最終承認を行います。共通の指揮系統は [AGENTS.md](AGENTS.md)、各専門役割は [正式Agent一覧](.claude/agents/README.md) に定義しています。

匿名化した求人条件・コピーのClaudeへの送信は、2026-09-07にユーザーが継続許可しています。共有する範囲と実行の判断はCodex CCOが担い、送信ごとのユーザー再承認は求めません。Claudeの専門レビュー結果をCCOが評価し、正式納品を承認します。

標準制作ではPythonやDirect OpenAI Images APIを画像生成責任者にしません。

```text
Human
↓
Codex CCO
├─ Claude Recruitment Analyst
├─ Claude Creative Director
├─ Codex Integrated Creative Designer + ImageGen
└─ Independent Creative Reviewer（標準Codex、CCOが選択）
↓
Codex Final QA
↓
Human Final Approval
```

**人物・写真はダウンロード済みAdobe素材を優先し、使える素材がない場合だけ人物から生成します。写真・装飾・日本語コピー・Typography・レイアウトは、Codex Integrated Creative DesignerがImageGen capabilityで一体制作します。**

素材フォルダは `G:\共有ドライブ\ジョブオレチーム\ジョブオレチーム\JOBOLE-Image-Creator-Team\Adobe\_image`（`ADOBE_IMAGE_ROOT` で変更可能）。ユーザーが制作利用を許可済みです。各案で素材を目視選定し、採用パス・理由をCreative Specへ保存します。未検索・接続不可は素材なしと判定しません。[Adobe素材優先フロー](docs/adobe-material-first.md)を参照してください。

標準 `codex_imagegen` 経路では、このプロジェクトへ `OPENAI_API_KEY` を設定することを必須にしません。
ImageGen capabilityが利用できない場合も、勝手にAPI fallbackしません。

詳細: `docs/codex-native-imagegen-v5.md`

## User Intake
必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

求人ファイル1つだけでも制作できます。

## Responsibilities
### Codex CCO
- 案件内容の理解・全体方針と作業順序の決定
- 正式11役割から必要なClaude Agentを選び、具体的な作業を指示
- 各Agentの成果物レビュー・修正指示・再レビュー
- Project作成/保存Gate
- Fact Gate
- benchmark選定
- Adobe素材選定（適合素材がない場合のみ人物生成へ進む）
- Creative Spec承認
- ImageGen capability Gate
- Integrated Creative Designerへの制作委譲
- Revision routing
- Final QA / formal approval

### Claude Recruitment Analyst
- exact role/employment/facts
- verbatim claims
- critical numeric facts
- evidence / claim boundary
- job reality

### Claude Creative Director
- strategy
- copy
- benchmark translation
- photo/art direction
- typography direction
- exact text contract
- Codex ImageGen execution brief
- 複数枚のデザイン差別化

### Codex Integrated Creative Designer
Role: `.codex/agents/integrated-creative-designer.md`
Skill: `.codex/skills/recruitment-imagegen/SKILL.md`

- ImageGenで完成広告を直接制作
- 人物/背景/装飾/文字/Typography/Layoutを統合
- required text自己確認
- 局所不具合はedit優先
- Candidateを案件配下へ保存

### Independent Creative Reviewer（標準Codex）
制作担当から独立して検証し、結果をCCOへ返します。Claudeを担当に選ぶ場合も、正式納品の最終承認者はCCOです。
- exact text readback
- Fact/Hearing/Benchmark review
- typography / ad impact
- job reality
- AI artifact
- multi-creative diversity

### Python
標準では画像生成しません。

担当:
- Project / Context
- benchmark catalog/contact sheet
- Codex Candidate registration
- size/aspect validation
- optional OCR
- delivery promotion
- Safe Python fallback

## Standard Workflow
```text
求人/Hearing
↓
Project First
↓
Compact Context
↓
Recruitment Analyst
↓
Codex Fact Gate
↓
Codex Benchmark Gate（最大3）
↓
Creative Director
↓
Codex Creative Spec Approval
↓
Codex ImageGen Capability Gate
↓
Codex Integrated Creative Designer
↓
ImageGenで完成広告
↓
Designer Self Check
↓
Candidate Registration
↓
Optional OCR
↓
Independent Reviewer（標準Codex）
↓
Codex Final QA
↓
Approval JSON
↓
05_delivery Promotion
↓
Human Final Approval
```

## Formal Candidate Path
ImageGen完成候補:

```text
PROJECT_DIR/
├─ 02_direction/
│  └─ CR001-creative-spec.json
├─ 03_batches/
│  └─ CR001/v001/
│     ├─ candidate.png
│     ├─ creative-spec.json
│     ├─ expected-copy.md
│     └─ generation-metadata.json
├─ 04_project_review/
│  ├─ CR001-v001-text-verification.json
│  ├─ CR001-v001-final-approval.json
│  └─ delivery_records/CR001/v001/
│     ├─ CR001-copy.md
│     ├─ CR001-approval.json
│     └─ CR001-generation-metadata.json
└─ 05_delivery/
   └─ CR001.png
```

`05_delivery` は完成画像のみ。コピー文・承認JSON・生成記録は `04_project_review/delivery_records/<creative-id>/<version>/` に保存します。説明文やステータス等の管理ファイルも `04_project_review` 配下に置きます。

## Candidate Registration
Codex Designerが `candidate.png` を作った後だけ実行:

```powershell
python scripts/register_codex_candidate.py --project-id <PJ-XXXX> --creative-id CR001 --version v001
```

このスクリプトは画像を生成/再デザインしません。
サイズ/Creative Spec/OCR/metadataを機械的に登録します。

## Fallback
### Safe Python
文字精度がどうしても安定しない場合だけ。

```env
CREATIVE_RENDER_MODE=safe_python
```

### Direct API
標準では無効。
ImageGen capabilityが使えず、ユーザーが明示承認した場合のみ:

```env
CREATIVE_RENDER_MODE=api_fallback
API_FALLBACK_ENABLED=true
```

この場合だけ `OPENAI_API_KEY` が必要です。

## .env Minimum
通常は以下が中心です。

```env
PROJECTS_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
ORIGINAL_IMAGE_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
ADOBE_IMAGE_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/Adobe/_image
KNOWLEDGE_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/knowledge
CREATIVE_RENDER_MODE=codex_imagegen
CODEX_IMAGEGEN_REQUIRED=true
SILENT_API_FALLBACK_ALLOWED=false
```

## Validation
```powershell
python -m compileall scripts services
python scripts/validate_system.py
python scripts/test_premium_contract.py
python scripts/test_codex_imagegen_contract.py
python scripts/test_promote_creative.py
```

Runtime確認:

```powershell
python scripts/validate_system.py --runtime-config --verify-login
```

`--verify-image` は `codex_imagegen` では外部APIを叩かず、ImageGen capability GateがCodex runtime内で必要であることを確認します。

## Quality Rule
「読める」「破綻していない」だけではPASSしません。

必須:
- 一流benchmark同等系列のpolish
- photo + typography integration
- 1秒で主訴求
- 3秒で仕事内容/魅力
- required text exactness
- job reality
- 複数枚の有意なデザイン差
- generic AI poster / Python template感がない

## Security
標準経路ではAPIキー不要。
Direct API fallbackを使う場合のみ `.env` にキーを設定し、Gitへコミットしないでください。
