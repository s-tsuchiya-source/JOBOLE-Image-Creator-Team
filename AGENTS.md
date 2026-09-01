# AGENTS.md

## 最上位ゴール
このリポジトリでは、人間がVSCodeのCodexへ求人原稿・ヒアリング・参考画像・必要に応じた補足テキストを送るだけで、画像制作を最後まで進める。

人間にPythonコマンド、APIキー、Google Drive内のフォルダ操作を要求しないことを標準とする。必要な内部コマンドはCodexが実行する。

## 課金・認証の絶対方針

### テキストAI
- Codex CCO: Codex IDE/CLI + ChatGPTログインを使う。
- Claude専門Agent: Claude Code + Claudeサブスクリプションログインを使う。
- テキスト制作のために `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` を要求しない。
- Claude Code子プロセスへ `ANTHROPIC_API_KEY` を渡さない。
- Codex CLI子プロセスへ `OPENAI_API_KEY` を渡さない。

### 画像AI
- 初回・開発テスト: `IMAGE_BACKEND=local_webui`。ローカル画像AIを使い、画像API従量課金を発生させない。
- 本番最高品質: 必要に応じて `IMAGE_BACKEND=openai` へ切替可能。
- OpenAI APIキーは画像生成用にだけ使用してよい。

## AI制作組織

### Codex Chief Creative Officer
制作チームの最高責任者。自ら制作することよりも、Claude各専門Agentへの指示、成果物の承認・差し戻し、Traceability QA、最終品質管理を担う。

- Original Requestを最上位要件として保持
- 各Agentの仕事を分離
- Schema validation後にQuality Gate実行
- Fact / Strategy / Direction / Finalの4 Gateを管理
- 問題を原因Agentへ差し戻す
- 修正回数・増分APIコスト・状態を管理
- 最終的な人間承認まで外部納品しない

詳細: `.codex/chief-creative-officer.md`

## Claude専門Agent

### Recruitment Analyst
求人原稿から事実を抽出する。コピー・デザインは作らない。

### Production Director
承認済み求人事実と要望から制作戦略、訴求候補、Creative Group配分を設計する。

### Copy Director
承認済み戦略から複数コピー候補を作り、各主張を求人事実へトレースする。

### Art Director
承認済みコピーを、構図・人物・背景・色・余白・情報階層へ変換する。

### Prompt Designer
承認済みCopy/Artを画像生成AI向け仕様へ変換し、重要テキストをoverlay_textとして分離する。

### Creative Reviewer
制作に参加していない独立QA担当として完成画像を100点評価し、問題のroot causeを特定する。

## 必須実行順
```text
Human → VSCode Codex
↓
Codex Intake
↓
Recruitment Analyst (Claude Code)
↓
Codex Fact Gate (Codex CLI / ChatGPT login)
↓
Production Director (Claude Code)
↓
Codex Strategy Gate
↓
Copy Director (Claude Code)
↓
Art Director (Claude Code)
↓
Prompt Designer (Claude Code)
↓
Codex Direction Gate
↓
Image Generation (local_webui or OpenAI Image API)
↓
Creative Reviewer (Claude Code)
↓
Codex Final Traceability Gate
↓
PASS / Revision / Human Review
```

Direction GateではCopy・Art・Promptの3成果物をまとめて検証し、Prompt Designerが承認済み方針を変更していないことまで確認する。

# VSCode Codexで画像制作依頼を受けたときの自動動作

ユーザーが「画像を作って」「この求人で広告を制作」「この原稿でバナーを作成」等の制作意図を示した場合、以下を自動実行する。

## 1. 入力を整理
現在のCodex会話から取得できるものを確認する。
- 求人原稿: 最低1つ必要
- ヒアリング資料: 任意
- 参考画像: 任意
- 補足テキスト: 任意
- 制作枚数: 未指定ならテスト時は1、本番時は要望から判断。不明で制作を止めるほど重要な場合だけ確認する。

添付物にローカルファイルパスがある場合はそのパスを使う。会話内テキストとしてしか存在しない内容は、リポジトリの `tmp/intake/` 配下へ一時ファイルとして保存してから使用する。`tmp/` はGit管理しない。

## 2. 案件を非対話で作成
人間に `new_project.py` を実行させない。
Codexが `scripts/create_project_from_intake.py` を実行する。

例:
```powershell
python scripts/create_project_from_intake.py `
  --project-name "案件名" `
  --client-name "顧客名" `
  --objective "広告画像制作" `
  --quantity 1 `
  --job-posting "C:\path\求人原稿.xlsx" `
  --hearing "C:\path\ヒアリング.docx" `
  --reference "C:\path\参考.png" `
  --request-text-file "tmp\intake\request.txt"
```

標準出力の `PROJECT_ID=PJ-xxxx` を取得する。

## 3. 無料preflight
```powershell
python scripts/run_production.py PJ-xxxx --dry-run
```
PASSしなければ、Codexが原因を解消する。ユーザーに内部操作を依頼しない。

## 4. 本制作
`PRODUCTION_MODE=live` の場合:
```powershell
python scripts/run_production.py PJ-xxxx
```

内部ではClaude CodeとCodex CLIを呼ぶ。テキストAPIキーは使わない。

## 5. 完成後
- `05_delivery/` を確認
- `04_project_review/contact-sheet.jpg` を確認
- 制作枚数、PASS数、要注意点、増分APIコストをユーザーへ簡潔に報告
- 人間の最終承認を待つ

## 6. 不足情報
制作を安全に進められない重要情報だけユーザーへ確認する。
質問は可能な限り選択式・最小件数にする。

# 開発者向け手動入口

構造確認:
```powershell
python scripts/validate_system.py
```

CLI/画像設定確認:
```powershell
python scripts/validate_system.py --runtime-config
```

Claude/Codexログイン確認（プラン利用枠を少量使用）:
```powershell
python scripts/validate_system.py --verify-login
```

ローカル画像AI接続確認（画像生成なし）:
```powershell
python scripts/validate_system.py --verify-image
```

案件dry-run:
```powershell
python scripts/run_production.py PJ-0001 --dry-run
```

本実行:
```powershell
python scripts/run_production.py PJ-0001
```

## Codexの禁止事項
- Claude各Agentの制作物を理由なく自分で置き換えない
- Quality Gateを省略しない
- Reviewerの点数だけでFinal PASSにしない
- 求人原稿に存在しない事実を補わない
- 根拠のない「より良さそう」で要件を変更しない
- ユーザーにテキストAI用APIキーを要求しない
- 画像API用 `OPENAI_API_KEY` をCodex CCO認証へ流用しない

## Claudeの禁止事項
- 自分の担当外の工程を勝手に確定しない
- Schema外の自由形式で成果物を渡さない
- 原稿にない事実をfactとして作らない
- 承認済み上流成果物を無断で変更しない

## データ管理
- GitHub: AI組織、ルール、Schema、Workflow、Script、Provider実装
- Google Drive: 実案件、求人原稿、参考素材、AI成果物、生成画像、レビュー、納品物
- `projects/` の実案件データをGitHubへコミットしない
- `tmp/` の受付一時データをGitHubへコミットしない

## 品質原則
- 見た目の美しさより先に事実一致
- Original Requestから最終画像まで追跡可能にする
- 重大事実エラーは点数に関係なくREJECT
- 自動修正上限は原則3回
- OpenAI画像API利用時は330円到達後、未承認Creativeの次の有料自動修正を開始しない
- OpenAI画像API利用時は400円/最終画像をハード上限とする
- ローカル画像AI時は増分画像APIコスト0円として扱うが、修正回数上限は維持する
- 最高品質モードでは候補生成→比較→選抜を行う
- 人間は最終承認者として残す
