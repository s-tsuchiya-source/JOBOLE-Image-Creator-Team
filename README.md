# JOBOLE Image Creator Team

JOBOLE向け画像制作を、**Codex Chief Creative Officer + Claude Code専門Agent + 切替可能な画像生成AI**で標準化するAI制作チームです。

## 最終ユーザー体験

人間はVSCodeのCodexへ、求人原稿・ヒアリング・参考画像・必要に応じた補足テキストを送ります。

```text
Human
  ↓
VSCode Codexへ素材を送る
  ↓
Codexが案件作成・Drive格納・制作開始
  ↓
Claude Code専門Agent群
  ↓
Codex 4段階Quality Gate
  ↓
画像生成AI
  ↓
Claude Reviewer
  ↓
Codex Final QA
  ↓
Google Drive / 05_delivery
  ↓
Human 最終承認
```

人間がPythonコマンド・APIキー・案件フォルダを操作することを通常運用にしません。

## 認証・費用設計

### テキストAI
- Codex CCO → Codex IDE/CLIへChatGPTアカウントでログイン
- Claude専門Agent → Claude CodeへClaudeサブスクリプションでログイン
- **テキストAI用APIキーは不要**
- Codex/Claudeの契約利用枠は消費するが、テキストAPIの従量課金は発生させない設計

### 画像生成
`.env` の `IMAGE_BACKEND` だけで切り替えます。

```env
IMAGE_BACKEND=local_webui
```

初回・開発テスト。AUTOMATIC1111 / SD-WebUI-Forge互換のローカル画像AIを使用し、画像APIの増分費用は0円。

```env
IMAGE_BACKEND=openai
```

本番最高品質でOpenAI Image APIを使う場合。OpenAI APIキーはこの画像工程だけに使用します。

## AI組織

```text
Codex Chief Creative Officer
│
├─ Claude Recruitment Analyst
├─ Claude Production Director
├─ Claude Copy Director
├─ Claude Art Director
├─ Claude Prompt Designer
└─ Claude Creative Reviewer
```

Codexは制作内容を無条件で作り直すのではなく、各専門Agentの成果物を承認・差し戻し・統合する最高責任者です。

## 4段階Quality Gate

```text
Recruitment Analyst
↓
Codex Fact Gate
↓
Production Director
↓
Codex Strategy Gate
↓
Copy + Art + Prompt
↓
Codex Direction Gate
↓
Image Generation
↓
Claude Creative Reviewer
↓
Codex Final Traceability Gate
```

## 品質モード
- Strategy候補: 5案以上
- Copy候補: 3案以上
- Art候補: 2案以上
- 自動修正: 原則最大3回
- 重大な求人事実エラー: 点数に関係なくREJECT
- Original Request → 最終画像までTraceabilityを維持

## コスト設計
- Claude Code / Codex CLIテキスト工程: 増分APIコスト0円として記録
- local_webui画像: 増分画像APIコスト0円
- OpenAI画像API: 400円/最終画像をハード上限
- OpenAI画像API時、未承認Creativeが推定330円以上なら次の有料再生成を開始しない

## データ配置

```text
GitHub
├─ AI Agent定義
├─ Codex CCO定義
├─ Schema
├─ Quality Rule
├─ Workflow
├─ Script
└─ Provider実装

Google Drive
└─ projects/
   ├─ PJ-0001_.../
   ├─ PJ-0002_.../
   └─ ...
```

GitHubには実案件データ・顧客素材・生成画像を保存しません。

## Google Drive案件構造

```text
PJ-0001_client/
├─ project.yaml
├─ creative-manifest.csv
├─ 00_request/
│  ├─ inbox/
│  │  ├─ job_posting/
│  │  ├─ hearing/
│  │  └─ references/
│  └─ normalized/
├─ 01_strategy/
├─ 02_direction/
├─ 03_batches/
├─ 04_project_review/
└─ 05_delivery/
```

## セットアップ確認

```powershell
python -m pip install -r requirements.txt
python -m compileall scripts services
python scripts/validate_system.py
```

Claude/Codex CLIと画像設定:

```powershell
python scripts/validate_system.py --runtime-config
```

ログイン確認:

```powershell
python scripts/validate_system.py --verify-login
```

ローカル画像AI接続確認:

```powershell
python scripts/check_local_image.py
```

## 手動dry-run

```powershell
python scripts/run_production.py PJ-0001 --dry-run
```

本実行:

```powershell
python scripts/run_production.py PJ-0001
```

通常の利用者はこれらを直接操作せず、VSCodeのCodexが `AGENTS.md` に従って内部実行します。

## Codexからの自動受付

Codexは `scripts/create_project_from_intake.py` を使用します。

```powershell
python scripts/create_project_from_intake.py `
  --project-name "案件名" `
  --quantity 1 `
  --job-posting "C:\path\求人原稿.xlsx" `
  --hearing "C:\path\ヒアリング.docx" `
  --reference "C:\path\参考画像.png"
```

補足テキストも追加できます。

## 詳細手順

`docs/live-setup.md` を参照してください。

## 開発方針
- `main` は安定版
- 変更はfeature branch + Pull Request
- APIキーや認証情報はGitHubへコミットしない
- 案件画像や顧客データはGitHubへ保存しない
- AI判断ルールはMarkdown/Schema/Configで検証可能にする
- 人間の最終承認前に外部納品しない
