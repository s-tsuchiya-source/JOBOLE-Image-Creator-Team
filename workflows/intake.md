# Intake Workflow

## 目的
求人原稿とヒアリング資料をGoogle Driveへ置くだけで、AI制作チームが読める入力状態へ正規化する。

## Google Drive入力先

```text
00_request/
└─ inbox/
   ├─ job_posting/
   ├─ hearing/
   └─ references/
```

- `job_posting/`: 元求人原稿
- `hearing/`: 制作要望・ヒアリング結果
- `references/`: 参考画像、ロゴ、ブランド資料等

## 対応するテキスト抽出形式
- txt
- md
- csv
- json
- yaml / yml
- docx
- xlsx
- PDF（テキスト埋め込み型）

画像PDF・スキャンPDFは現時点では自動テキスト抽出対象外。参考素材としては保存可能。

## 実行

```bash
python scripts/start_production.py PJ-0001
```

## 実行後

```text
00_request/
└─ normalized/
   ├─ source-bundle.md
   └─ source-index.json
```

が作成される。

`source-bundle.md` はProduction Directorが最初に読む統合入力データ。

## 入力ゲート
以下を満たす場合のみ `input_ready` とする。

- 求人原稿が1件以上読み込める
- ヒアリング資料が1件以上読み込める
- 読み込みエラーがない

不足時は `needs_input` とし、制作へ進まない。

## 次工程
Production Directorは `tmp/current-project/production-director-task.md` を参照し、

- `01_strategy/production-brief.md`
- `01_strategy/creative-plan.yaml`

を作成する。
