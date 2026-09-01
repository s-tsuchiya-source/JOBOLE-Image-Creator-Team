# Production Workflow

## 目的
Phase 1では、VSCode Codexを最高責任者として、3人のClaude専門家と画像/ファイル処理だけを使い、求人ファイル1つからでも高品質画像を作る。

## ユーザー入力
通常受付は次の3種類だけ。

- 求人ファイル: **必須**
- ヒアリングシート: 任意
- 補足テキスト: 任意

求人ファイルが正常に読める限り、ヒアリングや補足テキストが無くても制作を止めない。

未指定時のPhase 1既定値:
- 1枚
- 1200x628
- 求人広告画像

## 役割
- Codex CCO: 最高責任者・統括・承認・差し戻し・Final QA
- Recruitment Analyst: 求人事実整理
- Creative Director: 戦略・コピー・Art Direction・Prompt・Overlay Text
- Creative Reviewer: 独立レビュー
- Python: 画像生成・正確な文字入れ・サイズ調整・保存・ファイル整理

## 標準フロー
1. HumanがVSCode Codexへ求人ファイルを渡す。ヒアリング/補足テキストはあれば追加する。
2. Codexが案件名等を自動決定し、入力を整理する。
3. CodexがClaude Recruitment Analystへ求人分析を依頼する。
4. Codexが元求人とFact Sheetを照合し、Fact Checkを行う。
5. CodexがClaude Creative Directorへ承認済み事実と、存在する場合のみヒアリング/補足テキストを渡す。
6. Creative DirectorがTarget / Key Message / Copy / Art / Prompt / Overlay Textを一体設計する。
7. CodexがDirection Approvalを行い、画像内に載せる日本語文言を確定する。
8. Codexが `scripts/generate_creative.py` を使い、文字なし背景生成 → Python文字入れ → サイズ調整 → 保存を行う。
9. Pythonは完成画像と `*-copy.md` を同時出力する。
10. CodexがClaude Creative Reviewerへ完成画像とcopy.mdのレビューを依頼する。
11. CodexがReviewer結果・完成画像・copy.mdを見てFinal QAする。
12. NGなら原因工程だけへ戻す。原則最大3回。
13. PASS後、人間が最終承認する。

## 求人ファイルだけのとき
制作を止めず、以下だけをcreative assumptionとしてCodexが承認してよい。
- 人物像
- 服装
- 背景
- 構図
- 色/トーン
- カメラ距離

以下は推測禁止。
- 給与
- 待遇
- 休日
- 勤務時間
- 資格
- 経験年数
- 数値実績
- No.1/最短/保証等

## 日本語テキスト
重要テキストは画像生成AIに描かせない。

```text
Creative Directorが文言を提案
↓
Codexが文言を確定
↓
画像AIが文字なし背景を生成
↓
Python overlay_rendererが日本語を描画
↓
完成画像 + *-copy.md
```

ReviewerとCodexは、画像とcopy.mdの両方を確認する。

## Claudeの呼び出し
PythonからClaudeを自動オーケストレーションしない。

VSCode CodexがClaude Code CLIを直接利用する。

役割定義:
```text
.claude/agents/recruitment-analyst.md
.claude/agents/creative-director.md
.claude/agents/creative-reviewer.md
```

## 画像生成
画像生成方式は制作組織から独立させる。

ローカル画像AIが不安定な場合、Phase 1のクリエイティブ品質検証を止めず、必要ならOpenAI Image APIへ切り替える。

## Phase 1で使用しないもの
- Production Director
- Copy Director
- Art Director
- Prompt Designer
- Python AI Orchestrator
- 4段階の細分化Quality Gate
- Schema中心のAI連携
- 100枚量産前提の自動状態管理

## 禁止
- Codex CCOの二重化
- ヒアリング不足だけで制作停止
- 求人事実の推測補完
- 日本語重要コピーを画像AI任せにする
- CreatorとReviewerの兼任
- Reviewerの点数だけでFinal PASS
- ローカル画像AIの技術対応を、本来の画像品質検証より優先すること
