# New Order Workflow

## 目的
新規受注時に案件フォルダを発行し、求人原稿・ヒアリング資料を置くだけで制作開始できる入力先を用意する。

## 流れ
1. `python scripts/new_project.py` を実行する
2. 案件IDを採番する
3. `project.yaml` を作成する
4. `creative-manifest.csv` の初期データを作成する
5. Google Drive上に案件ディレクトリを生成する
6. 以下のInboxを自動作成する
   - `00_request/inbox/job_posting/`
   - `00_request/inbox/hearing/`
   - `00_request/inbox/references/`
7. 求人原稿・ヒアリング・参考素材をInboxへ配置する
8. `python scripts/start_production.py PJ-XXXX` を実行する
9. 入力を `00_request/normalized/source-bundle.md` に統合する
10. Production Directorへ引き渡す

## 人間が行う最低限の作業
- 案件作成
- 求人原稿を置く
- ヒアリング資料を置く
- 必要なら参考画像を置く

制作方針の整理以降はAIチームへ引き渡す。
