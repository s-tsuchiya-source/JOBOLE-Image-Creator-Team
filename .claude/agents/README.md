# 正式Agent定義 — jobole-agents-set

2026-09-07、ユーザー指定の `jobole-agents-set.zip` に含まれる11件を、このディレクトリの正式版として採用した。同名の旧定義は置き換え、別名の旧版やバックアップ定義は残していない。その後、同日のユーザー追加指示により素材関連Agentへ [Adobe素材優先フロー](../../docs/adobe-material-first.md) を反映した。

## 共通の指揮系統

**最高責任者はCodex CCO。ここにある正式11役割すべてがCodex CCOの指揮下で作業する。**
共通契約は [AGENTS.md](../../AGENTS.md)。Codex CCO自身が案件内容を理解し、必要なAgentへ入力・担当範囲・成果物・合格条件を示して指示する。
各Agentは成果物・根拠・未解決点をCCOへ返す。CCOがレビューして採否と修正先を決め、修正指示と再提出物のレビューまで担当する。
各Directorの「統括」「選定」「裁定」「差し戻し」は専門範囲の提案・整理を指す。案件全体の指揮と最終裁定はCCOが行う。独立レビューの未解消failは納品を止め、CCOの最終目視確認・正式納品承認とHuman Final Approvalを残す。

## 正式版一覧

匿名化した求人条件・コピーのClaudeへの送信は、ユーザーの継続許可に基づきCodex CCOが判断する。送信ごとのユーザー再承認は求めない。共通契約は [AGENTS.md](../../AGENTS.md)。各Agentは専門成果物を提出し、採否・修正・正式納品の判断はCCOが行う。

| Agent | 正本 | 担当 |
|---|---|---|
| Recruitment Analyst | [recruitment-analyst.md](recruitment-analyst.md) | ヒアリング・求人原稿の分析、根拠と禁止事項の構造化 |
| Creative Director | [creative-director.md](creative-director.md) | Creative Plan、制作戦略と各案の統合・採否提案 |
| Production Director | [production-director.md](production-director.md) | CCOの進行管理補佐、枚数・修正先提案・成果物台帳 |
| Copy Director | [copy-director.md](copy-director.md) | コピー候補の比較・選定と注記 |
| Art Director | [art-director.md](art-director.md) | ビジュアル候補の比較・選定 |
| Image Director | [image-director.md](image-director.md) | 素材要件・検索語・選定基準 |
| Text Director | [text-director.md](text-director.md) | 確定コピーの文字組み・可読性 |
| Designer | [designer.md](designer.md) | 各方向指定をDesign Specへ統合 |
| Prompt Designer | [prompt-designer.md](prompt-designer.md) | Codex Designer向け生成依頼文・添付案内・編集指示案 |
| Creative Reviewer | [creative-reviewer.md](creative-reviewer.md) | デザイン品質と編集指示 |
| Reviewer | [reviewer.md](reviewer.md) | 素材同一性・コピー・意向適合の最終QC |

`Creative Reviewer` と `Reviewer` は審査対象が異なるため、両方を正式版として残す。`Designer` は仕様を作る担当であり、画像を実制作する `.codex/agents/integrated-creative-designer.md` とは別の役割。Codex CCOとCodexの画像制作Agentも継続して配置する。

## 既存実行フローとの接続状況

正式版の採用は定義ファイルの置き換え。既存のPython実行フローを11段階へ移行したことや、画像制作・レビュー・納品の動作確認が済んだことを意味しない。

- `configs/agents.yaml` の `agents` は既存3役割の実行設定。残る8役割の正式定義は `additional_specialist_files` に登録している。後者はPython実行登録ではない。
- 添付版のCreative Directorは `Creative Plan`、Designerは `Design Spec` を出力する。既存v5が要求する `creative_spec` / `text_contract` へは変換が必要。
- 添付版のCreative Reviewerはデザイン審査、Reviewerは最終QCを担う。既存v5の承認JSONへはそのまま渡せない。
- 次の参照先schemaは未配置：`creative-plan`、`design-spec`、`image-direction`、`production-status`、`final-review`、`text-direction`（すべて `schemas/<名称>.schema.json`）。既存の同名schemaについても、添付定義の項目との整合確認が必要。
- 既存の `services/agent_runner.py` は `agent['schema']` を要求するが、既存3役割の設定にはそのキーがない。自動実行の接続時に対応が必要。
- Adobe素材はユーザー指定の `ADOBE_IMAGE_ROOT` を先に確認し、各案の選定結果を `creative_spec.asset_source` に保存する。既存v5のcontext・Spec・Candidate登録もこの契約に対応する。ChatGPTの固定ルールは自動登録していない。

既存v5経路の説明は [docs/codex-native-imagegen-v5.md](../../docs/codex-native-imagegen-v5.md) を参照。正式Agentの役割・出力は上記11件の各定義を正本とする。
