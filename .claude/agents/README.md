# Agent Tuning Guide — Premium Integrated AI v4

## Architecture
```text
VSCode Codex CCO
├─ Recruitment Analyst
├─ Creative Director
└─ Creative Reviewer

Premium Image AI
→ completed banner including Japanese typography

Python
→ context / generation / OCR helper / delivery control
```

Agent数を増やす前に、active 3Agent・benchmark・Premium Promptを改善する。

## Benchmark
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

Creative Directorへ渡すのはCodexが選んだ最大3件。

## Recruitment Analyst
ファイル: `recruitment-analyst.md`

改善対象:
- wrong role
- wrong employment type
- wrong salary/time/holiday
- 画像AIへ渡す正確な表記が曖昧

主要Output:
- Fact/Evidence
- `verbatim_claims`
- `critical_numeric_facts`
- Claim Boundary
- Job Reality

ここにCopy/Artを入れない。

## Creative Director
ファイル: `creative-director.md`

**最も大きい品質レバー。**

改善対象:
- サンプルより安っぽい
- TypographyがAI任せで雑
- 写真と文字が分離
- コピーが弱い
- ワンパターン
- 余計な文字が入る

見るポイント:
- benchmark translation
- Copy量
- Exact Text Contract
- Photo Direction
- Typography Direction
- Composition
- Color/Decoration
- Promptの完成広告指示

PremiumではPython Layout Familyへ逃げず、一体広告として設計する。

## Creative Reviewer
ファイル: `creative-reviewer.md`

改善対象:
- 誤字をPASS
- 数字違いをPASS
- デザインが弱いのにPASS
- OCRだけ見て画像を見ない

必須:
- visual text readback
- expected/observed exact match
- 1-second / 3-second test
- benchmark polish comparison
- job realism

ReviewerはCreatorより厳しくする。

## Codex CCO
ファイル: `.codex/chief-creative-officer.md`

改善対象:
- Claude案を鵜呑み
- unreviewed candidateを納品
- 文字エラーで全工程再実行
- OCRを絶対視
- Safe Modeへ早く逃げすぎる

CCOは:
- Fact Gate
- Benchmark Gate
- Creative Spec Gate
- Layered Text Integrity Gate
- Final QA
- Safe fallback decision
- Formal Promotion approval

を管理。

## Premium Image Prompt
Agentだけでなく実際の画像モデル出力品質も重要。

症状:
- Typographyが崩れる
- 余計な文字
- 写真が汎用的
- 求人広告ではなくポスター/チラシ風

改善先:
1. Creative Director `image.prompt`
2. `services/creative_spec.py` の統合Prompt Contract
3. Premium image model/backend

## OCR Helper
`services/text_verifier.py`

OCRは補助。

改善対象:
- 日本語文字の機械検査
- 数字の取りこぼし
- required block照合

ただし装飾文字で誤読するため、Reviewer/Codex visual checkを削らない。

## Safe Mode Renderer
次の場合だけ調整:
- Premiumで文字精度が安定しない
- 数字差し替えが頻繁
- 緊急修正

対象:
- `services/design_spec.py`
- `services/overlay_renderer.py`
- `configs/layouts.yaml`

Safe Rendererの見た目をPremium品質の上限にしない。

## Token Efficiency
- compact context first
- raw source fallback only
- benchmark max 3
- route max 2
- required text typical max 5
- Creative Spec reuse
- OCR全文をAIへ渡さない
- root cause revision only

## Feedback Loop
```text
実画像FB
↓
Fact / Copy / Art / Typography / Text Generation / Image Artifact のどこかを特定
↓
案件固有か再発性か判定
↓
再発する場合だけAgent/Prompt/Verifierへ一般化
↓
次案件で再検証
```

## Tuning Priority
1. Creative Director
2. Creative Reviewer
3. original_image benchmark
4. Premium image prompt/model
5. Recruitment Analyst
6. Codex CCO
7. OCR helper
8. Safe Python renderer
