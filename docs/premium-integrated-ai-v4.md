# Premium Integrated AI v4 — 実装設計

## 目的
求人広告クリエイティブの最優先KPIを「文字の再現性」から「納品物としての総合デザイン品質」へ戻す。

v3では画像AIとPython Typographyを分離したことで文字精度は高まったが、レイアウト・文字表現・写真との一体感がテンプレート化しやすかった。

v4では標準を次へ変更する。

```text
求人Fact / Hearing / Benchmark
↓
Claude Creative Director
↓
Premium Creative Spec
↓
Codex CCO Approval
↓
Image AI
写真 + 装飾 + 日本語Typographyを一体生成
↓
Text Verification
Local OCR optional + Claude visual readback + Codex visual check
↓
Creative Review
↓
Codex Final QA
↓
Explicit Approval
↓
Formal Delivery Promotion
```

Safe Python Rendererは削除しない。文字誤りがPremium Modeで解消しない場合のfallbackとして残す。

---

# 1. 新方式のシステム設計

## 1.1 Render Modes

### Premium Mode — default
設定:

```env
CREATIVE_RENDER_MODE=premium_ai
PREMIUM_IMAGE_BACKEND=openai
```

画像AIへ完成広告を依頼する。

AIが担当:
- 人物
- 職場
- 背景
- 構図
- 色
- 装飾
- Typography
- 日本語文字
- CTAやFactの視覚統合

Pythonは文字を上書きしない。

### Safe Mode — fallback

```env
CREATIVE_RENDER_MODE=safe_python
SAFE_IMAGE_BACKEND=openvino_ovms
```

使用条件:
- 同一必須文字の生成ミスが繰り返される
- 数値/条件が多くPremiumで安定しない
- 急な条件差し替え
- Codex CCOが正確性優先と判断

画像AIは文字なし背景を生成し、既存Design Spec + Python Rendererで正確に文字を描く。

## 1.2 Candidate First
画像生成直後のファイルは納品物ではない。

```text
03_batches/CR001/v001/candidate.png
```

ここから:
- OCR helper
- Claude Reviewer
- Codex CCO

を通過し、明示Approval JSONを作った後だけ `05_delivery` へ移す。

これにより「生成できた = 納品可能」の誤認を構造的に防ぐ。

## 1.3 Premium Creative Spec
正式契約:

```text
02_direction/CR001-creative-spec.json
```

主項目:
- `benchmark_refs`
- `strategy`
- `text_contract`
- `design_direction`
- `image.prompt`
- `image.negative_prompt`
- `forbidden_extra_text`

### text_contract
画像AIに自由に求人文言を考えさせない。

例:

```json
{
  "id": "T001",
  "role": "headline",
  "text": "スポーツ×福祉",
  "required": true,
  "fact_ids": ["F003"],
  "allow_visual_line_breaks": true,
  "priority": 1
}
```

`required=true` の文字はReviewerとCodexが必ず画像上で照合する。

## 1.4 Source of Truth

1. 求人ファイル = 求人Fact
2. ヒアリング = 希望・媒体・枚数・NG
3. 補足テキスト = 追加希望
4. Recruitment Analyst JSON = Fact ledger / verbatim ledger
5. Creative Spec = 生成時のコピー/Art Direction正本
6. Candidate image = 生成結果
7. Review JSON = 品質判定
8. Final Approval JSON = 05_deliveryへの唯一の昇格許可

---

# 2. Agentファイルの再設計

## 2.1 Recruitment Analyst
役割を「Fact抽出」から「生成AIへ渡しても安全なFact Ledger」へ強化。

追加:
- `verbatim_claims`
- `critical_numeric_facts`

特に画像AIが誤りやすい:
- 職種
- 雇用形態
- 給与
- 時間
- 日数
- 駅名
- 固有名詞

を原文どおり保持する。

Creative Directorはこの表記を勝手に変更しない。

## 2.2 Creative Director
v3の「Python Renderer向けLayout Spec」から、v4では「完成画像生成AI向けArt Direction」へ変更。

必須能力:
- benchmark visual grammar extraction
- ad concept
- copy
- exact text contract
- photo direction
- typography direction
- integrated composition
- high-quality image prompt

重要ルール:
- 文字を後載せする前提で設計しない
- 文字自体が構図の一部
- 写真と文字が相互補強する
- コピー量を抑える
- benchmarkを模倣ではなく品質基準として使う

## 2.3 Creative Reviewer
v4では「画像上の文字を読む」責任を明確化。

`text_readback` を必須化:

```json
{
  "id": "T001",
  "expected": "月給33万750円〜42万8,750円",
  "observed": "月給33万750円〜42万8,750円",
  "exact_match": true,
  "issue": ""
}
```

OCRを鵜呑みにしない。
画像を直接見たvisual readbackを必須とする。

## 2.4 Codex CCO
最高責任者として以下を管理:
- Project Gate
- Context Gate
- Fact Gate
- Benchmark Gate
- Creative Spec Gate
- Candidate Generation
- Text Integrity Gate
- Creative Review Gate
- Final QA
- Safe Mode fallback
- Formal Promotion

最大の変更は `05_delivery` を直接生成させないこと。

---

# 3. Pythonの役割を縮小・再定義

## 3.1 Pythonがやること

### Intake / Context
- project folder creation
- source file copy
- CSV/XLSX/DOCX/PDF extraction
- hearing/media resolution
- compact context
- reference catalog/contact sheet

### Generation Utility
- Creative Spec validation
- image backend invocation
- prompt package creation
- candidate version directory
- metadata

### Quality Helper
- local OCR if available
- normalized string comparison
- critical numeric token comparison
- verification report persistence

### Delivery Control
- explicit approval validation
- candidate -> formal delivery promotion
- copy/approval persistence

## 3.2 Pythonがやらないこと

Premium Modeでは以下を禁止:
- headline layout design
- type scale design
- color design decision
- photo composition decision
- copywriting
- benchmark final selection
- pass/fail creative judgment

これらはClaude/Codexが行う。

## 3.3 Safe Modeだけ残す機能
- `services/design_spec.py`
- `services/overlay_renderer.py`
- Layout Families

削除しないが主方式にしない。

---

# 4. OCR・事実照合

## 4.1 なぜOCRだけにしないか
日本語広告OCRは次を誤認する可能性がある。
- 装飾フォント
- 縁取り
- グラデーション
- 小さい「〜」
- カンマ
- 円/万

そのためLocal OCRの結果だけで納品判定しない。

## 4.2 3層検証

### Layer A — Local OCR optional
`scripts/verify_generated_text.py`

利用可能な場合:
- Tesseract
- `jpn+eng`

比較:
- NFKC正規化
- 空白除去
- required text substring
- numeric token

出力:

```text
04_project_review/CR001-v001-text-verification.json
```

OCR未導入:

```json
{"status":"needs_visual_verification"}
```

これは正常状態。

### Layer B — Claude Visual Readback mandatory
Reviewer自身が画像を読む。
required blockごとにexpected/observed/exact_matchを返す。

### Layer C — Codex Visual Check mandatory
Codexが特に以下を再確認:
- job title
- employment type
- salary
- hours
- holidays
- station/access
- qualification

## 4.3 Text Error Routing

### 文字だけ違う
Premium promptを修正して同じCreative Specで再生成。
Fact分析からやり直さない。

### Copy自体が悪い
Creative Director Copyへ戻す。

### 2回同じ文字が崩れる
CodexがSafe Modeを検討。

## 4.4 OCR Setup
Base requirementsには重いOCRを含めない。

任意:

```powershell
python -m pip install -r requirements-ocr.txt
```

さらにWindowsへTesseract本体とJapanese traineddataが必要。

`.env`:

```env
OCR_LANG=jpn+eng
TESSERACT_CMD=
```

OCR未導入でもClaude/Codexの視覚検証でフローは継続できる。

---

# 5. GitHub修正方針

## 新規
- `configs/render_modes.yaml`
- `services/creative_spec.py`
- `services/text_verifier.py`
- `scripts/verify_generated_text.py`
- `scripts/promote_creative.py`
- `requirements-ocr.txt`
- `docs/premium-integrated-ai-v4.md`

## 更新
- `.claude/agents/recruitment-analyst.md`
- `.claude/agents/creative-director.md`
- `.claude/agents/creative-reviewer.md`
- `.codex/chief-creative-officer.md`
- `scripts/generate_creative.py`
- `scripts/validate_system.py`
- `configs/agents.yaml`
- `configs/workflow.yaml`
- `configs/quality.yaml`
- `.env.example`
- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `.claude/agents/README.md`

## 維持
- `services/design_spec.py`
- `services/overlay_renderer.py`
- `configs/layouts.yaml`

これらはSafe Mode用。

---

# Standard Premium Workflow

```text
Human
求人 + optional Hearing/Text
↓
Codex CCO
Project creation
↓
Python
creative-context + benchmark catalog
↓
Recruitment Analyst
Fact Ledger + Verbatim Ledger
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Director
2 routes max
↓
Codex chooses
↓
02_direction/CR001-creative-spec.json
↓
python scripts/generate_creative.py
↓
03_batches/CR001/v001/candidate.png
↓
Optional local OCR
↓
Claude Reviewer visual readback
↓
Codex Final QA
↓
04_project_review/CR001-v001-final-approval.json
↓
python scripts/promote_creative.py
↓
05_delivery/CR001.png
↓
Human Final Approval
```

---

# Token / Cost Efficiency

品質を落とさず削減する。

- raw CSVを繰り返し送らない
- compact context first
- benchmark最大3
- route最大2
- required text block通常最大5
- Creative Specを全工程で再利用
- OCR全文をAIへ渡さない
- 文字ミスでFact分析を再実行しない
- 画像候補は1routeにつき原則1枚
- revision最大2
- Candidateをレビュー前に05_deliveryへコピーしない

---

# Success Criteria
Premium Modeの成功は「日本語が入った」ではない。

必須:
1. Fact正確
2. Hearing一致
3. required text正確
4. benchmark同等系列の広告品質
5. 写真と文字が一体
6. 一流デザイナーの制作物と比較して明確なテンプレ感がない
7. 1秒/3秒テストPASS
8. Reviewer PASS
9. Codex Final QA PASS
10. Human Final Approval
