# Revision Workflow

## 目的
レビューNGを単純再生成で処理せず、原因を作った専門工程まで戻して修正する。

## 原因分類
- `fact_error` → Recruitment Analyst / 人間確認
- `strategy_error` → Creative Director
- `copy_error` → Copy Director
- `art_error` → Art Director
- `prompt_error` → Prompt Designer
- `generation_error` → Codex Integrated Creative Designerによる編集または再生成
- `format_error` → レイアウト/出力処理を修正
- `brand_error` → Art / Prompt Directionを修正
- `missing_information` → 人間へ最小限の確認

## 流れ
1. Claude Creative Reviewer等が問題・根拠・root cause・修正案をCodex CCOへ返す。
2. 案件を統括するCodex CCOが実画像と成果物を確認し、原因を検証する。
3. Codex CCOが差し戻し先を決定する。
4. Codex CCOが原因Agentへ、具体的な修正内容・保持する承認済み要素・再確認条件を指示する。Production Directorは進行管理と修正先の提案で補佐する。
5. Codex CCOが再提出物をレビューし、必要なSchema検証も行う。
6. 実画像の修正が必要なら、CCOがCodex Designerへ編集または再生成を指示する。局所不具合は編集を優先する。
7. CCOがClaudeへ再レビューを指示し、結果と実画像を最終確認する。
8. 同一Creativeの修正上限は `configs/workflow.yaml` の `revision.max_count` / 実行時の `REVISION_MAX` に従う（既定2回）。
9. 上限超過は `needs_human_review`。

## コスト
### local_webui
旧ローカル経路のコスト条件。現在の標準は `codex_imagegen`。使用する場合もCCOが上記の修正上限を管理する。

### OpenAI Image API
- 330円以上では次の有料自動修正を開始しない。
- 400円をハード上限とする。

## 禁止
- 原因分類なしに「もう一度生成」を繰り返す
- Copyの問題を画像乱数だけで解決しようとする
- Fact errorをデザイン修正として処理する
- 承認済み要素を修正理由なく変更する
