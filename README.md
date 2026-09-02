# JOBOLE Image Creator Team

**Phase 1 Design Spec Quality v3**

JOBOLE向け求人広告画像を、**VSCode Codex CCO + Claude 3専門家 + Python Design Spec Renderer**で制作します。

## User Intake
必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

求人ファイル1つだけでも制作可能です。

## AI Organization
```text
Human
↓
VSCode Codex = Chief Creative Officer / 最高責任者
├─ Claude Recruitment Analyst
├─ Claude Creative Director
└─ Claude Creative Reviewer
```

## Core Rendering Principle: 方式A
重要な日本語文字を画像AIへ描かせません。

```text
Image AI
→ 人物・仕事内容・背景・構図・光・余白

Claude Creative Director
→ Copy + Layout Family + 意味改行 + 強調語/数字 + Accent + Design Spec

Python
→ 承認済みDesign Specを正確に描画
```

Pythonがデザインを考えるのではありません。
**Creative Directorが人間のArt DirectorのようにDesign Specを作り、PythonはFigma/Rendererのように再現します。**

## Layout Families
`configs/layouts.yaml`

- `numeric_impact`: 給与・時給・徒歩分数・休日数等
- `short_power_word`: ブランクOK・未経験OK・土日休み等
- `concept_message`: スポーツ×福祉等の仕事コンセプト
- `work_scene`: 仕事内容/人物/職場写真を主役にする
- `benefit_stack`: 複数メリットを整理して見せる
- `emotional_message`: やりがい・支援・成長等

複数枚案件で全画像を同じLayout Familyへ流し込みません。訴求の性質に合わせて見せ方を変えます。

## Design Spec
Creative Directorの承認案は、案件内に保存します。

```text
02_direction/CR001-design-spec.json
```

主な項目:
```json
{
  "layout_family": "numeric_impact",
  "accent_color": "#1F95B4",
  "text_zone": "left",
  "headline": {
    "lines": ["月給33万750円〜", "42万8,750円"],
    "emphasis": ["33万750円", "42万8,750円"]
  },
  "subcopy": {"text": "児童発達支援管理責任者"},
  "facts": ["駅徒歩4分"],
  "cta": {"text": "詳しく見る"},
  "image": {
    "prompt": "...",
    "negative_prompt": "..."
  },
  "benchmark_refs": ["R0001"]
}
```

`services/design_spec.py` が事前検証し、`services/overlay_renderer.py` が描画します。

## Why This Avoids Mechanical Design
旧方式:
```text
Headline -> 左上
Subcopy -> その下
Fact -> 同じChip
CTA -> 同じButton
```

v3:
```text
求人Fact / Hearing / Benchmark
↓
Claudeが訴求を判断
↓
Layout Familyを選択
↓
意味単位でHeadline改行
↓
強調語/数字を指定
↓
写真と文字の位置関係を指定
↓
Pythonが正確に描画
```

つまり固定テンプレではなく、**半構造化Design System**です。

## original_image Benchmark
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

`scripts/prepare_creative_context.py` がcatalog/contact sheetを作り、Codex CCOが案件に合う参考を最大3件選びます。

Pythonは参考画像の良し悪しを自動決定しません。

## Project Hard Rule
正式成果物は必ず:
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```
配下の案件フォルダへ保存します。

```text
PROJECT_DIR/
├─ 00_request/
├─ 01_strategy/
├─ 02_direction/
│  └─ CR001-design-spec.json
├─ 03_batches/
│  └─ CR001/v001/
│     ├─ background.png
│     ├─ image-prompt.txt
│     └─ design-spec.json
├─ 04_project_review/
└─ 05_delivery/
   ├─ CR001.png
   └─ CR001-copy.md
```

## Standard Workflow
```text
求人ファイル + optional hearing/text
↓
Codex CCO: Project作成
↓
Python: creative-context + reference catalog/contact sheet
↓
Recruitment Analyst
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Director
  - 最大2 Visual Routes
  - Layout Family選択
  - Copy
  - Semantic Line Breaks
  - Emphasis
  - Image Prompt
  - Design Spec
↓
Codex Design Spec Approval
↓
02_direction/<CR>-design-spec.json
↓
Image AI: 文字なし背景
↓
Python Design Spec Renderer
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

## Hearing Priority
ヒアリングはgeneric defaultより優先します。

例:
```text
JOBOLE（4:3）
→ configs/media.yaml
→ 1200x900 / 4:3
```

## Token Efficiency
- `creative-context.json` を一次入力
- raw sourceはFact疑義だけ
- Agent出力はcompact JSON
- benchmark最大3
- Visual Route最大2
- Fact最大3
- Design SpecをRenderer/Reviewerで再利用
- Revision原則最大2
- 問題工程だけ再実行

## Generate Creative
CodexがDesign Specを保存した後:

```powershell
python scripts/generate_creative.py --project-id PJ-XXXX --creative-id CR001
```

標準では:
```text
02_direction/CR001-design-spec.json
```
を自動使用します。

## Renderer Smoke Test
画像APIを使わず、6 Layout Familyの日本語描画だけテストできます。

```powershell
python scripts/test_design_renderer.py
```

出力:
```text
tmp/layout-smoke/
```

## Validation
```powershell
python -m compileall scripts services
python scripts/validate_system.py
python scripts/validate_system.py --runtime-config
```

## Tuning Priority
1. `.claude/agents/creative-director.md`
2. `.claude/agents/creative-reviewer.md`
3. `configs/layouts.yaml`
4. `services/overlay_renderer.py`
5. `.claude/agents/recruitment-analyst.md`
6. `.codex/chief-creative-officer.md`
7. Image Backend

SVG/CSS Rendererは将来の拡張候補として残しますが、Phase 1 v3では外部ブラウザ依存を増やさず、**Python Design Spec Rendererで品質差を検証**します。
