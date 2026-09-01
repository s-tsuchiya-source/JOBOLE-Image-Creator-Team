# Intake Workflow

## 目的
人間がVSCodeのCodexへ求人原稿・ヒアリング・参考画像・補足テキストを送るだけで、Google Drive案件を作成して制作を開始できる状態にする。

## 標準入口

```text
Human
↓
VSCode Codex
↓
scripts/create_project_from_intake.py
↓
Google Drive project
↓
run_production.py
```

人間にGoogle Driveフォルダ作成やPythonコマンド操作を要求しない。

## 最低入力
- 求人原稿: 必須1件以上
- ヒアリング: 任意
- 参考画像: 任意
- 補足テキスト: 任意

求人原稿だけで制作判断できる場合は進行する。ヒアリングがないことだけを理由に停止しない。

## Google Drive入力先

```text
00_request/
└─ inbox/
   ├─ job_posting/
   ├─ hearing/
   └─ references/
```

補足テキストは `hearing/request-text.md` として保存する。

## Codexの非対話受付

```powershell
python scripts/create_project_from_intake.py `
  --project-name "案件名" `
  --quantity 1 `
  --job-posting "C:\path\求人原稿.xlsx" `
  --hearing "C:\path\ヒアリング.docx" `
  --reference "C:\path\参考.png" `
  --request-text-file "tmp\intake\request.txt"
```

戻り値例:

```text
PROJECT_ID=PJ-0003
PROJECT_DIR=G:\...\PJ-0003_xxx
```

CodexはこのPROJECT_IDを使って以降を実行する。

## 対応テキスト抽出形式
- txt
- md
- csv
- json
- yaml / yml
- docx
- xlsx
- PDF（テキスト埋め込み型）

画像PDF・スキャンPDFは現時点ではテキスト抽出対象外。参考素材として保存可能。

## 正規化

```powershell
python scripts/run_production.py PJ-XXXX --dry-run
```

内部で `input_loader.py` が以下を作る。

```text
00_request/
└─ normalized/
   ├─ source-bundle.md
   └─ source-index.json
```

## 入力ゲート
`input_ready` の最低条件:
- 求人原稿が1件以上読み込める
- 読み込みエラーがない

ヒアリング・参考素材・補足テキストは任意。

制作に不可欠な情報が実際に不足しているかは、Recruitment Analyst / Production Director / Codex Gateが判断する。

## 次工程

```text
source-bundle
↓
Claude Recruitment Analyst
↓
Codex Fact Gate
↓
Production Director
```
