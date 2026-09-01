# Production Workflow

## 目的
Phase 1では、VSCode Codexを最高責任者として、3人のClaude専門家と画像/ファイル処理だけを使い、最短で高品質画像を作る。

## 役割
- Codex CCO: 最高責任者・統括・承認・差し戻し・Final QA
- Recruitment Analyst: 求人事実整理
- Creative Director: 戦略・コピー・Art Direction・Prompt
- Creative Reviewer: 独立レビュー
- Python: 画像生成・文字入れ・サイズ調整・保存・ファイル整理

## 標準フロー
1. HumanがVSCode Codexへ求人原稿・ヒアリング・参考画像・補足テキストを渡す。
2. Codexが必要なら案件フォルダを作り、入力を整理する。
3. CodexがClaude Recruitment Analystへ求人分析を依頼する。
4. Codexが元求人とFact Sheetを照合し、Fact Checkを行う。
5. CodexがClaude Creative Directorへ承認済み事実とOriginal Requestを渡す。
6. Creative DirectorがTarget / Key Message / Copy / Art / Prompt / Overlayを一体設計する。
7. CodexがDirection Approvalを行う。
8. CodexがPython画像ユーティリティを使って画像生成・文字入れ・サイズ調整・保存を行う。
9. CodexがClaude Creative Reviewerへ完成画像レビューを依頼する。
10. CodexがReviewer結果と完成画像を見てFinal QAする。
11. NGなら原因工程だけへ戻す。原則最大3回。
12. PASS後、人間が最終承認する。

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

Codexが承認済みPromptをPython画像ユーティリティへ渡す。

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
- 求人事実の推測補完
- CreatorとReviewerの兼任
- Reviewerの点数だけでFinal PASS
- ローカル画像AIの技術対応を、本来の画像品質検証より優先すること
