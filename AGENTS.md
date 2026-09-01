# AGENTS.md

## AIチーム構成

### Production Director
案件全体の責任者。
- 求人原稿・ヒアリング内容の整理
- 必要エージェント選定
- 制作方針決定
- 訴求配分決定
- レビュー結果を踏まえた再実行判断

### Text Director
テキスト訴求の責任者。
- ターゲット整理
- メインコピー
- サブコピー
- CTA
- 文字量最適化

### Image Director
ビジュアル設計の責任者。
- 構図
- 色
- 背景
- 人物有無
- 視線誘導
- ブランドトーン

### Designer
画像生成用Prompt作成担当。
- Text Director と Image Director の成果物を統合
- 画像生成AIへ渡す実制作指示を作成

### Reviewer
品質管理担当。
- 要件一致
- 視認性
- 誤字脱字
- ブランド適合
- 画像破綻
- 入稿観点確認

## 案件作業開始ルール
1. 対象 `project_id` を必ず確定する。
2. `python scripts/start_production.py <project_id>` を実行して入力資料を正規化する。
3. `input_ready` になったことを確認する。
4. `python scripts/load_project.py <project_id>` を実行する。
5. `tmp/current-project/production-director-task.md` を確認する。
6. `tmp/current-project/context.md` と `context.json` を確認する。
7. Google Driveの `00_request/normalized/source-bundle.md` をProduction Directorへ渡す。
8. 案件切替時はContextを再生成する。

## Codexの主な役割
Codexは制作内容そのものより、AI制作チームのオーケストレーションを担当する。

- 対象案件の特定
- `start_production.py` / `load_project.py` の実行
- 入力不足チェック
- manifestの状態確認
- 次タスクの特定
- Claude Agentへ渡す作業ファイルの準備
- ファイル・フォルダ・スクリプト管理
- ワークフロー改善
- テスト・検証
- 制作工程の自動化

Codexは求人原稿の内容を独自解釈して広告コピーを確定しない。クリエイティブ判断はClaude側の各Directorに委ねる。

## Claudeの主な役割
Claudeは制作判断を担当する。

- Production Directorによる案件理解・制作戦略
- Text Directorによる訴求・コピー設計
- Image Directorによるビジュアル設計
- Designerによる画像生成Prompt設計
- Reviewerによる品質判定

## 基本ルール
- 1つのAgentが全てを抱え込まない
- Agent間の受け渡しはファイルで明示する
- 出力フォーマットはテンプレート準拠
- 案件データはGoogle Driveに保存する
- GitHubには案件データを保存しない
- 求人原稿に存在しない事実を創作しない
