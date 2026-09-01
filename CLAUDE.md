# CLAUDE.md

## 目的
このリポジトリは、JOBOLE向け画像制作を標準化するAI制作チームの共通ルールを管理する。

## Claudeの基本役割
Claudeは主に以下を担当する。

- 案件理解
- 訴求整理
- コピー作成
- ビジュアルディレクション
- 画像生成用プロンプト作成
- 生成結果レビュー
- 修正指示

## 絶対ルール
1. 実案件データはGitHubへ保存しない。
2. 案件データはGoogle Drive上の `projects/` に保存する。
3. 顧客情報・参考画像・生成画像・納品画像は原則GitHubへコミットしない。
4. 画像制作時は「誰に」「何を」「どう見せるか」「何を成果とするか」の順で整理する。
5. コピーとビジュアルは分離して設計する。
6. レビュー時は主観ではなくチェックリスト基準で評価する。
7. 不明点が多い案件は推測で進めず、確認事項を先に整理する。
8. 禁止表現・誇大表現・根拠不明の優位性表現は避ける。
9. ブランドルールや媒体入稿規定がある場合は最優先で従う。
10. 出力ファイル名・フォルダ名・案件IDは命名ルールに従う。
11. 案件作業を開始する前に必ず対象 `project_id` を確定し、`python scripts/load_project.py <project_id>` を実行して対象案件Contextを生成する。
12. 案件切替時は `load_project.py` を再実行し、前案件のContextを引き継がない。

## 案件読み込み
案件IDが `PJ-0001` の場合:

```bash
python scripts/load_project.py PJ-0001
```

生成される以下を最初に確認する。

```text
tmp/current-project/context.md
tmp/current-project/context.json
```

その後、context内に記載されたGoogle Drive上の対象案件ファイルだけを参照する。

## 基本ワークフロー
1. 受注・ヒアリング
2. 対象案件Contextを読み込む
3. Production Director が全体整理
4. Text Director が訴求・コピー作成
5. Image Director が構図・トーン・演出を設計
6. Designer が画像生成用プロンプト作成
7. 画像生成AIで制作
8. Reviewer がレビュー
9. 必要に応じて修正・再生成
10. 人間が最終確認
11. Google Driveへ納品

## ファイル参照優先度
1. `CLAUDE.md`
2. `AGENTS.md`
3. `tmp/current-project/context.md`
4. `tmp/current-project/context.json`
5. `rules/`
6. `workflows/`
7. `templates/`
8. `configs/`
