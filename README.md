# JOBOLE Image Creator Team

**Phase 1 Codex Native ImageGen v5**

JOBOLE向け求人広告画像を、**VSCode Codex CCO + Codex Integrated Creative Designer + Claude 3専門家**で制作します。

## 最重要方針
標準制作ではPythonやDirect OpenAI Images APIを画像生成責任者にしません。

```text
Human
↓
Codex CCO
├─ Claude Recruitment Analyst
├─ Claude Creative Director
├─ Codex Integrated Creative Designer + ImageGen
└─ Claude Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

**人物・背景・装飾・日本語コピー・Typography・レイアウトまで、Codex Integrated Creative DesignerがImageGen capabilityで一体生成します。**

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
- Project作成/保存Gate
- Fact Gate
- benchmark選定
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

### Claude Creative Reviewer
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
Claude Reviewer
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
│  └─ CR001-v001-final-approval.json
└─ 05_delivery/
   ├─ CR001.png
   ├─ CR001-copy.md
   └─ CR001-approval.json
```

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
