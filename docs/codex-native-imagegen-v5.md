# Codex Native ImageGen v5 — System Design

## 0. Decision
標準制作方式を次へ変更する。

### v4
```text
Claude Creative Director
→ Creative Spec
→ Python
→ Direct Image API
→ Candidate
```

### v5
```text
Claude Creative Director
→ Creative Spec
→ Codex Integrated Creative Designer
→ Codex ImageGen capability
→ Candidate
```

**画像実制作責任をPython/API呼び出しからCodex自身へ移す。**

Codexモデル単体が画像を直接出力するという意味ではない。
Codex runtimeで利用可能なImageGen capabilityをCodex Agentが操作し、制作責任を持つ。

---

# 1. 新方式のシステム設計

## 1.1 Goal
求人ファイル1つだけでも、最終的に一流の日本人求人広告デザイナーが制作したものと比較できる品質を目指す。

品質対象:
- 人物
- 背景
- 仕事内容表現
- 装飾
- 日本語コピー
- Typography
- レイアウト
- 色
- 視線誘導
- 広告としての1秒/3秒理解

これらを別工程で機械的に合成せず、**一枚の広告として統合制作する。**

## 1.2 Active Team
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

## 1.3 Responsibility Boundary
### Codex CCO
- 案件責任
- Fact Gate
- benchmark選定
- Creative Spec承認
- ImageGen capability確認
- Production委譲
- Revision routing
- Final QA
- Formal delivery approval

### Recruitment Analyst
- Fact正確性
- verbatim claims
- critical numbers
- job reality

### Creative Director
- 訴求
- コピー
- benchmark翻訳
- Art/Typography方向
- exact text contract
- Codex ImageGen用brief

### Integrated Creative Designer
- ImageGen実制作
- 人物/背景/装飾/文字/Typography/Layout統合
- 生成後self-check
- edit / regenerate判断
- Candidate保存

### Creative Reviewer
- 独立品質審査
- exact text readback
- Fact/Hearing/Benchmark
- Typography/Ad impact
- Job reality
- 多様性

### Python
- deterministic utilities only

## 1.4 Standard Flow
```text
Input
↓
Project First
↓
Compact Context
↓
Recruitment Analysis
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Direction
↓
Codex Creative Spec Approval
↓
Codex ImageGen Capability Gate
↓
Integrated Creative Designer
↓
ImageGen completed ad
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
Approval
↓
Promotion
↓
Human Final Approval
```

## 1.5 Capability Gate
標準経路はCodex runtimeにImageGen capabilityが存在することを前提とする。

### Available
制作続行。

### Unavailable
```text
IMAGEGEN_CAPABILITY_UNAVAILABLE
```
で停止する。

禁止:
- Direct OpenAI APIへ自動切替
- APIキーをユーザーへ暗黙要求
- Safe Modeへ勝手に切替

CCOが状況を説明し、ユーザー判断を得る。

---

# 2. Agentファイル改修設計

## 2.1 New Codex Integrated Creative Designer
File:
`.codex/agents/integrated-creative-designer.md`

このAgentはプロジェクト管理をしない。
**実制作だけに集中する。**

責任:
- Creative Spec遵守
- benchmark品質理解
- ImageGen操作
- integrated composition
- text accuracy self-check
- edit before regenerate
- multi-creative diversity

禁止:
- Fact変更
- コピー勝手変更
- API fallback
- Python overlay依存

## 2.2 Recruitment ImageGen Skill
File:
`.codex/skills/recruitment-imagegen/SKILL.md`

目的:
Designerが毎回同じ品質ルールでImageGenを扱うための実行規約。

含む:
- exact text rule
- completed ad rule
- no extra text
- composition rule
- edit loop
- saving contract
- failure behavior

## 2.3 Codex CCO
CCOへ追加:
- Codex production agent管理
- ImageGen capability gate
- standard pathにAPIキー不要
- Candidate registration工程
- edit/regenerate routing
- API fallback明示承認ルール

## 2.4 Creative Director
v4ではImage API向けPromptだった。
v5では**Codex Designerが判断・操作できるexecution brief**へ変更。

新必須:
```json
"execution": {
  "generation_owner": "codex_integrated_creative_designer",
  "generation_capability": "codex_imagegen",
  "prefer_edit_before_regenerate": true
}
```

## 2.5 Creative Reviewer
生成者がCodexになっても独立性を維持。

root causeを以下へ分ける:
- designer_edit
- designer_regenerate
- designer_text_fix
- creative_director strategy/copy/art
- recruitment analyst fact

---

# 3. Pythonの役割を縮小・再定義

## 3.1 Pythonがやらないこと
標準 `codex_imagegen` ではPythonは以下をしない。

- image generation
- typography design
- layout design
- copy design
- direct OpenAI Images API call
- production creative decisions

## 3.2 Pythonがやること
### Intake
- project folder
- input copy
- project.yaml

### Context
- CSV parsing
- compact context
- benchmark catalog
- contact sheets

### Candidate Registration
New:
`scripts/register_codex_candidate.py`

責任:
- candidate存在確認
- canonical pathへ揃える
- aspect ratio確認
- Creative Spec snapshot
- expected-copy保存
- optional OCR
- metadata保存

重要:
**既存Candidateを登録するだけ。画像を生成しない。**

### Text Verification
- Tesseract optional
- deterministic text normalization
- report

### Formal Promotion
- approval JSON検証
- 05_deliveryへ昇格

## 3.3 Existing generate_creative.py
v5ではfallback-only。

標準mode `codex_imagegen` で呼ばれた場合は明示終了:
```text
v5 primary generation is owned by Codex Integrated Creative Designer + ImageGen
```

### safe_python
残す。

### api_fallback
残すが:
- `API_FALLBACK_ENABLED=true`
- user explicit approval
- OPENAI_API_KEY
が必要。

標準で勝手に起動しない。

---

# 4. OCR / 事実照合設計

ImageGen一体生成は日本語を含められる一方、求人では一文字・一数字の誤りも重要。
そのため4層Gateにする。

## Layer 1: Designer Self Check
生成直後にCodex Integrated Creative Designerが確認。

対象:
- required text
- job title
- employment type
- salary
- access
- numeric claims

明確な局所誤り:
→ ImageGen edit優先。

## Layer 2: Local OCR
Tesseractがある場合だけ。

目的:
- 自動警告
- 数字ミス候補
- missing text候補

OCR自体の日本語誤読があるため、単独でFAIL確定しない。

## Layer 3: Claude Visual Readback
Reviewerが画像そのものを見て:
```json
{
  "expected": "月給33万750円",
  "observed": "月給33万750円",
  "exact_match": true
}
```
を返す。

## Layer 4: Codex CCO
最終確認。

特に:
- 職種
- 雇用形態
- 給与
- 時間
- 休日
- 駅名
- 数字

確認エラーはdelivery block。

## Fact Trace
Creative Spec `text_contract.fact_ids` とRecruitment Analyst Fact IDを使い、画像文字を求人Factへトレース可能にする。

---

# 5. GitHub改修方針

## 5.1 New Files
- `.codex/agents/integrated-creative-designer.md`
- `.codex/skills/recruitment-imagegen/SKILL.md`
- `scripts/register_codex_candidate.py`
- `scripts/test_codex_imagegen_contract.py`
- `docs/codex-native-imagegen-v5.md`

## 5.2 Updated Files
- `.codex/chief-creative-officer.md`
- `.claude/agents/creative-director.md`
- `.claude/agents/creative-reviewer.md`
- `.claude/agents/README.md`
- `configs/agents.yaml`
- `configs/workflow.yaml`
- `configs/render_modes.yaml`
- `configs/quality.yaml`
- `services/creative_spec.py`
- `scripts/generate_creative.py`
- `scripts/validate_system.py`
- `.env.example`
- `.github/workflows/validate.yml`
- `README.md`
- `AGENTS.md`
- `CLAUDE.md`

## 5.3 Compatibility
v4 `premium_integrated` Creative Specは読み込み互換を残し、内部では `codex_integrated` にnormalizeする。

Safe Python:
- `services/design_spec.py`
- `services/overlay_renderer.py`
- `configs/layouts.yaml`
はfallbackとして維持。

---

# 6. File / State Contract

## Before Generation
```text
00_request/normalized/creative-context.json
02_direction/CR001-creative-spec.json
```

## After Codex ImageGen
```text
03_batches/CR001/v001/candidate.png
```

## After Registration
```text
03_batches/CR001/v001/creative-spec.json
03_batches/CR001/v001/expected-copy.md
03_batches/CR001/v001/generation-metadata.json
04_project_review/CR001-v001-text-verification.json
```

## After Approval
```text
04_project_review/CR001-v001-final-approval.json
```

## After Promotion
```text
05_delivery/CR001.png
05_delivery/CR001-copy.md
05_delivery/CR001-approval.json
```

---

# 7. .env Contract

## Standard
```env
CREATIVE_RENDER_MODE=codex_imagegen
CODEX_IMAGEGEN_REQUIRED=true
SILENT_API_FALLBACK_ALLOWED=false
API_FALLBACK_ENABLED=false
```

`OPENAI_API_KEY` は標準経路の必須項目ではない。

## Explicit API Fallback
ユーザーが承認した場合だけ:
```env
CREATIVE_RENDER_MODE=api_fallback
API_FALLBACK_ENABLED=true
OPENAI_API_KEY=...
OPENAI_IMAGE_MODEL=gpt-image-2
```

---

# 8. Quality Strategy

## Why this is expected to improve visual quality
v3 Safe Pythonの問題:
- deterministic layout
- limited typography grammar
- repeated visual templates

v4 Direct Image APIで改善した点:
- text/photo integration

v5の追加価値:
- Codexが制作工程を所有
- benchmarkを見た判断と生成を同じ制作担当が接続
- 完成画像を見てeditできる
- Creative Specと実画像間にPython generation layerを置かない
- 同案件の他画像を見ながら多様性を判断できる

## What v5 does NOT guarantee
Codex runtimeにImageGen capabilityが存在しなければ自動生成はできない。
そのためCapability Gateを明示する。

またImageGenで日本語が常に完全一致する保証はない。
そのためText Integrity Gateを残す。

---

# 9. Validation

Static / CI:
```powershell
python -m compileall scripts services
python scripts/validate_system.py
python scripts/test_premium_contract.py
python scripts/test_codex_imagegen_contract.py
```

Runtime:
```powershell
python scripts/validate_system.py --runtime-config --verify-login
```

実制作時はCCO自身がImageGen capability gateを実行する。
PythonからImageGen capabilityを偽装判定しない。

---

# 10. Final Operating Principle
このプロジェクトの目的は「APIを呼ぶ仕組み」でも「Pythonテンプレを完成させること」でもない。

目的は:

> **求人Factを守りながら、一流デザイナー水準を目指す完成広告をAI制作チームで再現性高く作ること。**

そのためv5では、制作判断とImageGen実行をCodex Integrated Creative Designerへ集約し、Pythonは確実な機械処理へ戻す。
