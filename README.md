# JOBOLE Image Creator Team

**Phase 1 Premium Integrated AI v4**

JOBOLE向け求人広告画像を、**VSCode Codex CCO + Claude 3専門家 + Premium Image AI + Python品質管理**で制作します。

## 最重要方針
標準は `Premium Mode`。

```text
Image AI
→ 人物・背景・装飾・日本語Typographyまで一体で完成広告を生成

Claude / Codex
→ Fact・Hearing・Benchmark・文字・デザイン品質を審査

Python
→ Project / Context / Generation / OCR補助 / Candidate管理 / Delivery promotion
```

Pythonが広告デザインを作るのではありません。
旧Python Typographyは `Safe Mode` fallbackとして残します。

詳細設計: `docs/premium-integrated-ai-v4.md`

## User Intake
必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

求人ファイル1つだけでも制作できます。

## AI Organization
```text
Human
↓
VSCode Codex = Chief Creative Officer / 最高責任者
├─ Claude Recruitment Analyst
├─ Claude Creative Director
└─ Claude Creative Reviewer
```

## Benchmark Library
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

制作前にPythonがcatalog/contact sheetを作り、Codex CCOが案件に合う参考を最大3件選びます。

## Project Storage
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

正式成果物をDesktop/repo/tmpへ代替保存しません。

## Render Modes
### Premium Mode — default
```env
CREATIVE_RENDER_MODE=premium_ai
PREMIUM_IMAGE_BACKEND=openai
```

画像AIが完成バナーを一体生成します。
- photography
- composition
- decoration
- Japanese typography
- exact required copy

Creative Directorが `02_direction/CR001-creative-spec.json` を作ります。

### Safe Mode — fallback
```env
CREATIVE_RENDER_MODE=safe_python
SAFE_IMAGE_BACKEND=openvino_ovms
```

Premiumで文字誤りが解消しない、数値変更が頻繁等の場合のみCodex CCOが選択します。

## Premium Creative Spec
`services/creative_spec.py`

```json
{
  "version": "4.0",
  "mode": "premium_integrated",
  "benchmark_refs": ["R0001"],
  "text_contract": [
    {
      "id": "T001",
      "role": "headline",
      "text": "スポーツ×福祉",
      "required": true,
      "fact_ids": ["F003"],
      "allow_visual_line_breaks": true,
      "priority": 1
    }
  ],
  "design_direction": {
    "visual_style": "",
    "typography_style": "",
    "composition": "",
    "text_zone": "left",
    "accent_color": "#E85A3D",
    "color_system": "",
    "decoration": "",
    "photo_direction": ""
  },
  "image": {
    "prompt": "",
    "negative_prompt": ""
  },
  "forbidden_extra_text": []
}
```

画像AIへコピーを自由創作させず、`text_contract` を正本にします。

## Standard Workflow
```text
求人 + optional Hearing/Text
↓
Codex Project Gate
↓
Python creative-context / benchmark catalog
↓
Recruitment Analyst
Fact + Evidence + verbatim strings
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Director
最大2route → Premium Creative Spec
↓
Codex Creative Spec Gate
↓
python scripts/generate_creative.py
↓
Candidate only
↓
Optional Local OCR
↓
Claude Reviewer visual text readback + creative review
↓
Codex Final QA
↓
Final Approval JSON
↓
python scripts/promote_creative.py
↓
05_delivery
↓
Human Final Approval
```

## Candidate First
`generate_creative.py` は未審査画像を `05_delivery` へ入れません。

```text
03_batches/CR001/v001/
├─ candidate.png
├─ creative-spec.json
├─ expected-copy.md
├─ image-prompt.txt
└─ generation-metadata.json

04_project_review/
└─ CR001-v001-text-verification.json
```

Reviewer + Codex PASS後だけpromotionします。

## Generate Premium Candidate
```powershell
python scripts/generate_creative.py --project-id PJ-XXXX --creative-id CR001
```

明示Safe Mode:
```powershell
python scripts/generate_creative.py --project-id PJ-XXXX --creative-id CR001 --mode safe_python
```

## Text Verification
文字精度は3層です。

1. Local OCR — optional
2. Claude visual readback — mandatory
3. Codex final visual check — mandatory

Local OCR:
```powershell
python -m pip install -r requirements-ocr.txt
python scripts/verify_generated_text.py --project-id PJ-XXXX --creative-id CR001 --version v001
```

Tesseract本体/Japanese traineddataが無い場合は `needs_visual_verification` になり、制作は止まりません。

## Final Approval / Promotion
Codexが以下を満たしたApproval JSONを作成:

```json
{
  "creative_id": "CR001",
  "version": "v001",
  "creative_reviewer_pass": true,
  "codex_final_qa_pass": true,
  "fact_integrity_pass": true,
  "text_integrity_pass": true
}
```

Promotion:
```powershell
python scripts/promote_creative.py --project-id PJ-XXXX --creative-id CR001 --version v001 --approval-file "<approval.json>"
```

初めて:
```text
05_delivery/CR001.png
05_delivery/CR001-copy.md
05_delivery/CR001-approval.json
```
へ入ります。

## Token / Cost Efficiency
- `creative-context.json` を一次入力
- raw CSVはFact疑義だけ
- benchmark最大3
- route最大2
- required text block通常最大5、hard max 6
- Creative Specを生成/OCR/Reviewerで再利用
- OCR全文をAIへ送らない
- 文字ミスでFact分析からやり直さない
- Revision原則最大2

## Python Responsibilities
### Pythonが行う
- Project作成
- input extraction
- compact context
- benchmark catalog/contact sheet
- media size resolution
- Creative Spec validation
- image backend invocation
- optional OCR
- deterministic text comparison
- candidate/version management
- final promotion
- Safe Mode typography

### Premium ModeでPythonが行わない
- Copywriting
- Art Direction
- Typography design
- Benchmark final selection
- Creative pass/fail judgment

## Validation
```powershell
python -m compileall scripts services
python scripts/validate_system.py
```

Premium本番設定まで確認:
```powershell
python scripts/validate_system.py --runtime-config
python scripts/validate_system.py --verify-image
```

期待:
```text
SYSTEM VALIDATION: PASS
Claude specialists: 3
Codex CCO: VSCode highest authority
Primary render mode: PREMIUM INTEGRATED AI
Safe Python typography: FALLBACK ONLY
```

## Tuning Priority
1. `.claude/agents/creative-director.md`
2. `.claude/agents/creative-reviewer.md`
3. `original_image` benchmark quality
4. Premium image model / prompt
5. `.claude/agents/recruitment-analyst.md`
6. `.codex/chief-creative-officer.md`
7. OCR helper
8. Safe Python renderer
