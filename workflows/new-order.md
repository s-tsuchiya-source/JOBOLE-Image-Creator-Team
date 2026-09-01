# New Order Workflow

## 目的
新規制作依頼は、**人間がVSCodeのCodexへ素材を送るだけ**を標準とする。

人間に `new_project.py` の実行、Google Driveフォルダ作成、ファイル振り分けを要求しない。

## 人間が行うこと

Codexへ次を送る。

```text
この求人で画像を制作してください。
必要なら補足要望を書く。

添付:
- 求人原稿.xlsx      必須
- ヒアリング.docx    任意
- 参考画像.png       任意
```

## Codexが内部で行うこと

1. 添付・会話テキストを整理する。
2. 会話内だけに存在するテキストは `tmp/intake/` へ一時保存する。
3. `scripts/create_project_from_intake.py` を非対話実行する。
4. `PJ-xxxx` を自動採番する。
5. `project.yaml` / `creative-manifest.csv` を作成する。
6. Google Driveへ案件フォルダとInboxを自動作成する。
7. 求人原稿・ヒアリング・参考素材を適切なInboxへコピーする。
8. `scripts/run_production.py PJ-xxxx --dry-run` を実行する。
9. dry-runの問題はCodexが可能な限り自分で解消する。
10. `PRODUCTION_MODE=live` なら `scripts/run_production.py PJ-xxxx` を実行する。
11. Claude Code専門Agent群とCodex Quality Gateを順番に実行する。
12. 選択中の画像バックエンドで画像を制作する。
13. 完成物・コンタクトシート・品質結果を人間へ返す。

## 自動案件作成コマンド
Codexが内部で利用する。

```powershell
python scripts/create_project_from_intake.py `
  --project-name "案件名" `
  --client-name "顧客名" `
  --objective "求人広告画像制作" `
  --quantity 1 `
  --job-posting "C:\path\求人原稿.xlsx" `
  --hearing "C:\path\ヒアリング.docx" `
  --reference "C:\path\参考画像.png" `
  --request-text-file "tmp\intake\request.txt"
```

## Google Drive生成先

```text
projects/
└─ PJ-XXXX_client/
   ├─ project.yaml
   ├─ creative-manifest.csv
   └─ 00_request/
      └─ inbox/
         ├─ job_posting/
         ├─ hearing/
         └─ references/
```

## 最低入力条件
- 求人原稿: 1件以上必須
- ヒアリング: 任意
- 参考素材: 任意
- 補足テキスト: 任意

ヒアリングが存在しないことだけを理由に制作を停止しない。求人原稿から判断できず、品質・事実性のために本当に必要な情報だけ `needs_clarification` とする。

## 認証
- Codex CCO: ChatGPTログイン済みCodex IDE/CLI
- Claude専門Agent: Claudeサブスクリプションへログイン済みClaude Code
- テキストAI用APIキー: 不要

## 画像
初回テスト:

```env
IMAGE_BACKEND=local_webui
```

本番で必要な場合のみ:

```env
IMAGE_BACKEND=openai
```

## 人間工数の目標
通常案件では、人間の操作を以下に限定する。

1. 素材＋要望をCodexへ送る
2. 不可欠な不足情報がある場合だけ回答する
3. 完成画像を確認・承認する
