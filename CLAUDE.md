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
11. 案件作業を開始する前に必ず対象 `project_id` を確定する。
12. 求人原稿・ヒアリング資料が正規化される前に制作方針を作ってはいけない。
13. 案件切替時は前案件のContextを引き継がない。

## 案件開始手順
案件IDが `PJ-0001` の場合は以下の順で実行する。

```bash
python scripts/start_production.py PJ-0001
python scripts/load_project.py PJ-0001
```

`start_production.py` はGoogle Drive上の以下を読み込む。

```text
00_request/inbox/job_posting/
00_request/inbox/hearing/
00_request/inbox/references/
```

そして以下を作成する。

```text
00_request/normalized/source-bundle.md
00_request/normalized/source-index.json

tmp/current-project/production-director-task.md
tmp/current-project/intake-report.json
```

Production Directorは必ず `production-director-task.md` と `source-bundle.md` を読んでから制作戦略を作る。

## 入力不足時
`start_production.py` が `needs_input` を返した場合は制作へ進まない。
不足している求人原稿・ヒアリング情報を明示して人間へ確認する。

## 案件Context
`load_project.py` 実行後、以下を確認する。

```text
tmp/current-project/context.md
tmp/current-project/context.json
```

その後、context内に記載されたGoogle Drive上の対象案件ファイルだけを参照する。

## 基本ワークフロー
1. 新規案件作成
2. 求人原稿・ヒアリング資料・参考素材をGoogle Driveへ配置
3. `start_production.py` で入力正規化
4. `load_project.py` で対象案件Context作成
5. Production Director が `production-brief.md` / `creative-plan.yaml` を作成
6. Text Director が訴求・コピー作成
7. Image Director が構図・トーン・演出を設計
8. Designer が画像生成用プロンプト作成
9. 画像生成AIで制作
10. Reviewer がレビュー
11. 必要に応じて修正・再生成
12. 人間が最終確認
13. Google Driveへ納品

## ファイル参照優先度
1. `CLAUDE.md`
2. `AGENTS.md`
3. `tmp/current-project/production-director-task.md`
4. `tmp/current-project/context.md`
5. `tmp/current-project/context.json`
6. Google Drive案件の `00_request/normalized/source-bundle.md`
7. `rules/`
8. `workflows/`
9. `templates/`
10. `configs/`
