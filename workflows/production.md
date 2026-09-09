# Production Workflow

## 目的と指揮系統
Codex CCOを最高責任者とし、求人ファイルから案件作成・専門分析・画像制作・レビュー・正式納品まで進める。
Codex CCO自身が内容を理解して各Claude Agentへ指示し、各成果物のレビュー・修正指示・再レビューを行う。共通契約は [AGENTS.md](../AGENTS.md)、詳細は [CCO定義](../.codex/chief-creative-officer.md)。

匿名化した求人条件・コピーのClaudeへの送信は、ユーザーが継続許可している。Codex CCOが匿名化・共有範囲・実行の必要性を判断し、送信ごとのユーザー再承認を工程に追加しない。

## ユーザー入力
- 求人ファイル: 必須。求人Factの正本。
- ヒアリングシート: 任意。希望・媒体・枚数・NG・テイスト。
- 補足テキスト: 任意。

ヒアリングがなくても制作できる。未指定時の既定値は `configs/workflow.yaml` の1枚・1200×628を使い、指定があれば `resolved_output_spec` を優先する。給与・待遇・休日・勤務時間・資格・経験年数・数値実績などの求人事実を推測で補わない。

## 役割
- Codex CCO: 案件理解、全体方針、各Agentへの指示、成果物レビュー、修正指示、統合・承認、最終目視確認、正式納品承認。
- Claude専門Agent: CCOから割り当てられた分析・戦略・コピー・デザイン仕様・素材選定・進行管理・独立レビューを担当し、成果物と根拠をCCOへ返す。
- Codex Integrated Creative Designer: CCO承認済みCreative Specに基づき、ImageGenで写真・装飾・日本語コピー・Typography・レイアウトを一体制作する。
- Python: 案件作成、前処理、素材一覧、候補登録、サイズ検査、OCR補助、承認済み画像の納品昇格。

正式なClaude Agentは [一覧の11役割](../.claude/agents/README.md)。CCOが案件に必要なAgentを選ぶ。Creative Directorは戦略統合、Production Directorは進行管理の専門担当であり、案件全体の指揮と最終裁定はCCOが行う。

## 標準フロー
1. Codex CCOが依頼・求人・ヒアリングを理解し、案件を作成する。`PROJECT_ID` / `PROJECT_DIR` / 入力保存を確認する。
2. CCOが `scripts/prepare_creative_context.py` でcompact contextを準備し、媒体・枚数・サイズ・禁止事項を確認する。
3. CCOがClaude Recruitment Analystへ入力・担当範囲・成果物・合格条件を示して分析を指示する。
4. CCOが分析結果を求人Factと照合する。誤りや不足があれば具体的に修正を指示し、再提出物をレビューする。
5. CCOがbenchmarkを最大3件選び、[Adobe素材優先フロー](../docs/adobe-material-first.md) に従って素材を選定する。必要ならImage Directorへ調査を指示し、結果をCCOが目視確認・承認する。
6. CCOがCreative Directorと必要なCopy / Art / Text / Designer等へ専門作業を指示する。各成果物をCCOがレビューし、根拠・依頼適合・品質を確認して採用または修正を判断する。
7. CCOが採用成果物を `02_direction/<creative-id>-creative-spec.json` へ統合し、exact `text_contract`、`asset_source`、benchmark、制作方針、出力条件を承認する。Prompt Designerを使う場合も、その依頼文をCCOがレビューする。
8. CCOがImageGen capabilityを確認し、Codex Integrated Creative Designerへ制作を指示する。Adobe採用時は原本を実画像入力に使う。人物からの生成は適合素材なしを確認した案だけ。
9. Codex DesignerがImageGenで完成広告を制作し、文字・数値・人物・業務・品質を自己確認する。各画像を個別に `03_batches/<creative-id>/<version>/candidate.png` へ保存する。
10. 保存後に `scripts/register_codex_candidate.py` を実行する。DesignerはCandidateと自己確認結果をCCOへ返す。
11. CCOが独立Reviewer（標準Codex）を選び、デザイン品質・最終QC・文字readbackを指示する。実際の担当と結果を記録し、Claudeの承認を必須条件にしない。[Review Workflow](review.md) に従う。
12. CCOがレビュー結果・根拠・実画像を確認する。NGはCCOが原因工程を特定して修正を指示し、再提出物と再レビュー結果を確認する。
13. 独立Reviewerの検証結果をCCOが評価し、CCOの正式納品承認JSONを保存した画像を `scripts/promote_creative.py` で案件の `05_delivery` へ昇格する。正式納品の承認者はCCO。画像は1枚ずつ独立したファイルで保存する。
14. Human Final Approvalを受ける。

## 専門Agentの呼び出しと接続状況
Claude Agentの選択・作業指示・成果物の採否・修正指示はCodex CCOが行う。CLIやPythonは呼び出し・検証の実行手段であり、指揮系統を変更しない。
一次入力は `creative-context.json` と承認済みのcompact成果物にする。raw sourceはFact疑義の確認に限定する。

既存v5のPython実行設定はClaude 3役割。正式11役割の定義配置と自動実行の接続完了は別であり、未接続のschemaや承認JSON形式は [接続状況](../.claude/agents/README.md) を確認する。未実行の専門作業・レビューを完了扱いにしない。

## 文字確認と修正
文字・数値はCreative Specで固定し、Codex Designerの目視、任意のlocal OCR、独立Reviewerのvisual readback、Codex CCOの最終目視で照合する。
明確な文字・Fact誤りや未解消のReviewer failは正式納品を止める。CCOが原因と修正先を決め、局所不具合はImageGen editを優先する。詳細は [Revision Workflow](revision.md)。

## ImageGenが使えない場合
`IMAGEGEN_CAPABILITY_UNAVAILABLE` としてCCOへ報告する。Safe PythonはCCOが条件を確認して判断し、Direct API fallbackはユーザー明示承認がある場合だけ使う。標準制作の責任者はCodex Integrated Creative Designer。

## 保存先
正式な案件の `PROJECT_DIR` を使用する。候補は `03_batches`、レビュー記録は `04_project_review`、承認後の個別画像のみを `05_delivery` へ保存する。コピー文・承認JSON・生成記録は `04_project_review/delivery_records/<creative-id>/<version>/`、説明文やステータスは `04_project_review` 配下へ保存する。一覧画像は確認補助であり、個別画像の納品に代えない。
