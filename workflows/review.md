# Review Workflow

## 目的
完成画像を制作担当から独立したClaude Creative ReviewerとCodex CCOの二重QAで検証する。

## 認証
- Claude Reviewer: Claude Codeサブスクリプションログイン
- Codex Final Gate: Codex CLI / ChatGPTログイン
- テキストAI用APIキーは使用しない

## 流れ
1. 生成画像＋全上流成果物をClaude Creative Reviewerへ渡す。
2. Claudeが100点評価し、問題ごとにroot causeと修正指示を返す。
3. Reviewer出力をJSON Schema検証する。
4. 画像・Original Request・求人事実・Strategy・Copy・Art・Prompt・Claude ReviewをCodex Final Traceability Gateへ渡す。
5. Codexが最終判定する。
6. PASSなら `05_delivery/` へ保存する。
7. REVISEなら原因工程へ差し戻す。
8. 重大な事実差異、修正上限、解決不能な曖昧性は `needs_human_review` とする。

## PASS条件
- Claude Reviewer decision = pass相当
- Claude score >= 設定値
- Codex Final Gate = PASS
- Codex score >= 設定値
- critical issue = 0

Reviewerの点数だけではPASSにしない。

## 画像バックエンド非依存
ローカル画像AIでもOpenAI Image APIでも、Reviewer/Final Gateの品質基準は変更しない。
