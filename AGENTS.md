# AGENTS.md

## AIチーム構成

### Production Director
案件全体の責任者。
- ヒアリング内容整理
- 必要エージェント選定
- 制作方針決定
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
2. `python scripts/load_project.py <project_id>` を実行する。
3. `tmp/current-project/context.md` と `context.json` を確認する。
4. manifestのstatusから次に処理するCreativeを決める。
5. Google Drive上の対象案件以外を暗黙参照しない。
6. 案件切替時はContextを再生成する。

## Codexの主な役割
- 案件Contextの読み込み
- manifestの状態確認
- 次タスクの特定
- ファイル・フォルダ・スクリプトの管理
- ワークフロー改善
- テスト・検証
- 制作工程の自動化

## 基本ルール
- 1つのAgentが全てを抱え込まない
- Agent間の受け渡しはファイルで明示する
- 出力フォーマットはテンプレート準拠
- 案件データはGoogle Driveに保存する
- GitHubには案件データを保存しない
