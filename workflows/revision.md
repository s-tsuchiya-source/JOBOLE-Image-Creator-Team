# Revision Workflow

## 目的
レビューNGを単純再生成で処理せず、原因を作った専門工程まで戻して修正する。

## 原因分類
- `fact_error` → Recruitment Analyst / 人間確認
- `strategy_error` → Production Director
- `copy_error` → Copy Director
- `art_error` → Art Director
- `prompt_error` → Prompt Designer
- `generation_error` → 同じ承認済みDirectionで画像再生成
- `format_error` → レイアウト/出力処理を修正
- `brand_error` → Art / Prompt Directionを修正
- `missing_information` → 人間へ最小限の確認

## 流れ
1. Claude Creative Reviewerが問題とroot causeを返す。
2. Codex Final Gateが独立して原因を検証する。
3. Codex CCOが差し戻し先を決定する。
4. 原因Agentへ、承認済み要素を保持したまま修正指示を返す。
5. 修正成果物を再度Schema検証・Codex Gateへ通す。
6. 画像を再生成する。
7. Claude Reviewer + Codex Final Gateを再実行する。
8. 同一Creativeの自動修正は原則最大3回。
9. 上限超過は `needs_human_review`。

## コスト
### local_webui
画像API増分コスト0円。コスト理由では止めないが、無限ループ防止のため3回上限は維持する。

### OpenAI Image API
- 330円以上では次の有料自動修正を開始しない。
- 400円をハード上限とする。

## 禁止
- 原因分類なしに「もう一度生成」を繰り返す
- Copyの問題を画像乱数だけで解決しようとする
- Fact errorをデザイン修正として処理する
- 承認済み要素を修正理由なく変更する
