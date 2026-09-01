# Maximum Quality Runtime Setup

このドキュメントは、次の構成でJOBOLE画像制作チームを動かすための手順です。

```text
VSCode Codex / Codex CLI
  └─ ChatGPTログイン（テキストAPIキー不要）

Claude Code
  └─ Claudeサブスクリプションログイン（テキストAPIキー不要）

画像生成
  ├─ 初回: local_webui（API従量課金0円）
  └─ 本番: OpenAI Image API（必要時のみ）
```

## 重要
- `ANTHROPIC_API_KEY` は本システムのテキスト制作には使用しない。
- OpenAIの `OPENAI_API_KEY` は `IMAGE_BACKEND=openai` の画像生成だけに使用する。
- Codex子プロセスには `OPENAI_API_KEY` を渡さない。
- Claude Code子プロセスには `ANTHROPIC_API_KEY` を渡さない。
- Codex/Claudeの契約プラン利用枠は消費する。API従量課金と「利用量ゼロ」は同義ではない。
- 初回テストは必ず1案件・1画像にする。

# 1. Claude Code

Windows PowerShellでインストールする場合、Anthropic公式の例:

```powershell
irm https://claude.ai/install.ps1 | iex
```

またはNode.jsがある場合:

```powershell
npm install -g @anthropic-ai/claude-code
```

確認:

```powershell
claude --version
claude
```

Claude Code内で:

```text
/login
```

Claude.aiのPro / Max / Team / Enterprise等、利用するサブスクリプションへログインする。

確認後 `/exit`。

# 2. Codex CLI

VSCodeのCodex拡張に加えて、PythonからQuality Gateを自動実行するためCodex CLIも使用する。

```powershell
npm install -g @openai/codex
codex --version
codex
```

表示される手順に従いChatGPTアカウントでサインインする。

Codex IDE/CLIはChatGPTログインを使用する。テキスト品質管理のための手動 `OPENAI_API_KEY` は不要。

# 3. 初回画像AI: local_webui

本システムはAUTOMATIC1111 / SD-WebUI-Forge互換のローカルREST APIに対応する。

ローカル画像AI側で以下が動作している状態にする。

```text
http://127.0.0.1:7860
POST /sdapi/v1/txt2img
GET  /sdapi/v1/options
GET  /sdapi/v1/sd-models
```

WebUIをAPI有効で起動し、使用したいcheckpointをロードする。

使用モデルはシステム側に固定しない。PCのGPU/VRAMに応じてWebUI側で選択できる。

## .env 初回テスト例

```env
PROJECTS_ROOT=G:/共有ドライブ/.../JOBOLE-Image-Creator-Team/projects
KNOWLEDGE_ROOT=G:/共有ドライブ/.../JOBOLE-Image-Creator-Team/knowledge
LOCAL_TEMP_ROOT=./tmp

CLAUDE_CLI_COMMAND=claude
CLAUDE_CLI_MODEL=opus
CLAUDE_CLI_MAX_TURNS=4
CLAUDE_CLI_TIMEOUT_SEC=600

CODEX_CLI_COMMAND=codex
CODEX_CLI_MODEL=
CODEX_CLI_SANDBOX=read-only
CODEX_CLI_TIMEOUT_SEC=900

IMAGE_BACKEND=local_webui
LOCAL_IMAGE_API_URL=http://127.0.0.1:7860
LOCAL_IMAGE_MODEL=local-loaded-checkpoint
LOCAL_IMAGE_STEPS=28
LOCAL_IMAGE_CFG_SCALE=6.5
LOCAL_IMAGE_SAMPLER=DPM++ 2M
LOCAL_IMAGE_TIMEOUT_SEC=600

JAPANESE_FONT_PATH=C:/Windows/Fonts/YuGothB.ttc

PRODUCTION_MODE=live
```

初回localモードでは以下は不要:

```text
ANTHROPIC_API_KEY
OPENAI_API_KEY
OPENAI_IMAGE_MODEL
USDJPY_RATE
OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION
```

# 4. 無料/非画像生成チェック

構造:

```powershell
python scripts/validate_system.py
```

ローカルCLI設定:

```powershell
python scripts/validate_system.py --runtime-config
```

Codex/Claudeログイン確認:

```powershell
python scripts/validate_system.py --verify-login
```

この確認は画像API料金を発生させない。ただしCodex/Claudeの契約プラン利用枠を少量消費する。

ローカル画像AI接続:

```powershell
python scripts/check_local_image.py
```

または:

```powershell
python scripts/validate_system.py --verify-image
```

どちらも画像は生成しない。

# 5. VSCode Codexからの標準受付

人間は原則コマンドを操作しない。

VSCodeのCodexへ例えば次だけ送る。

```text
この求人で画像を1枚制作してください。
20代向けで、未経験歓迎を最優先にしてください。

添付:
- 求人原稿.xlsx
- ヒアリング.docx
- 参考画像.png
```

Codexは `AGENTS.md` に従って、内部的に `scripts/create_project_from_intake.py` を実行し、Google Drive案件を作成する。

その後:

```text
create_project_from_intake.py
↓
run_production.py --dry-run
↓
run_production.py
↓
Claude Code specialists
↓
Codex Quality Gates
↓
local_webui
↓
Claude Reviewer
↓
Codex Final Gate
↓
05_delivery
```

# 6. 手動で1枚テストする場合

案件を作成し求人原稿を配置した後:

```powershell
python scripts/run_production.py PJ-XXXX --dry-run
```

PASS後:

```powershell
python scripts/run_production.py PJ-XXXX
```

local_webuiなら画像API従量課金は0円。

# 7. 本番でOpenAI画像APIへ切り替える

テキストAIの設定は変更しない。

`.env` の画像部分だけ変更する。

```env
IMAGE_BACKEND=openai
OPENAI_API_KEY=<画像生成専用のローカルsecret>
OPENAI_IMAGE_MODEL=<利用するImage API model>
OPENAI_IMAGE_QUALITY=high
USDJPY_RATE=<予算管理レート>
OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION=<保守的な1生成予算USD>
```

Codex CLI起動時、プログラムは `OPENAI_API_KEY` を子環境から削除する。そのためこのキーはCodex CCOのテキスト処理には使われない。

## OpenAI画像API時の予算ガード
- 400円/最終画像をハード上限
- 330円以上では未承認Creativeの次の有料再生成を開始しない
- Claude/Codexテキスト工程は増分API原価0円として記録

# 8. 正常完了時に確認するもの

- `01_strategy/recruitment/recruitment-analysis.json`
- `01_strategy/production-plan.json`
- `01_strategy/quality_gates/`
- `02_direction/copy/`
- `02_direction/art/`
- `02_direction/prompts/`
- `03_batches/`
- `04_project_review/provider-usage.jsonl`
- `04_project_review/production-summary.json`
- `04_project_review/contact-sheet.jpg`
- `05_delivery/CR001.png`

# 9. 初回テストの評価
- 求人事実の誤り: 0件
- Claude専門Agentの成果物品質
- Codex Gateの厳しさ
- 日本語文字の正確性
- ローカル画像AIの人物・構図品質
- 修正ループが原因工程へ戻っているか
- 人間の最終評価

ローカル画像品質が十分でない場合でも、Text/Strategy/QA設計はそのまま保持し、画像バックエンドだけOpenAIへ切り替える。
