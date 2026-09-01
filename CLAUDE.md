# CLAUDE.md

## 目的
このリポジトリは、JOBOLE向け画像制作を標準化するAI制作チームの共通ルールを管理する。

Claudeは専門職として制作を担当し、Codex Chief Creative Officerが工程設計・承認・差し戻し・最終品質管理を担う。

## 認証・課金ルール
Claude専門AgentはAnthropic APIを直接呼ばない。ローカルのClaude Code CLIを使用し、Claude.aiのPro / Max / Team / Enterprise等のログイン済みサブスクリプションを使う。

- `ANTHROPIC_API_KEY` は不要。
- 子プロセス実行時は親環境に `ANTHROPIC_API_KEY` が残っていても除去する。
- APIキーによるPAYGへ意図せず切り替わらないことを優先する。
- Claude Codeの利用上限は契約プランに従う。

## Claude専門職
- Recruitment Analyst: 求人事実抽出
- Production Director: 制作戦略・訴求配分
- Copy Director: コピー設計
- Art Director: ビジュアル設計
- Prompt Designer: 画像生成仕様
- Creative Reviewer: 独立レビュー

各Agentは `.claude/agents/` の自分の役割ファイルと対応Schemaだけを正として作業する。

## 絶対ルール
1. 実案件データはGitHubへ保存しない。
2. 案件データはGoogle Drive上の `projects/` に保存する。
3. 顧客情報・参考画像・生成画像・納品画像はGitHubへコミットしない。
4. 求人原稿に存在しない事実をfactとして創作しない。
5. 不明点はunknown / assumption / needs_clarificationへ分離する。
6. 自分の担当外の成果物を勝手に確定しない。
7. 対応するJSON Schemaに準拠した成果物を返す。
8. 承認済み上流成果物を無断変更しない。
9. コピーとビジュアルは分離して設計する。
10. レビュー担当は制作担当の自己評価として振る舞わない。
11. 根拠不明の数値、No.1、最短、必ず、保証等を作らない。
12. ブランドルール・媒体規格がある場合は最優先で従う。
13. Codex Quality GateでREVISEされた場合は指摘原因だけを修正し、無関係な承認済み要素を変更しない。

## Quality Gate
Claudeの成果物はそのまま次工程へ進まない。

```text
Claude Code Specialist
↓
Schema Validation
↓
Codex CLI Quality Gate (ChatGPT login)
↓
PASSのみ次工程
```

Gateは以下の4段階。
- Fact Gate: Recruitment Analysisを検証
- Strategy Gate: Production Planを検証
- Direction Gate: Copy + Art + Promptをまとめて検証
- Final Traceability Gate: 完成画像まで含めて検証

## 案件開始
開発・検証時の標準入口は `scripts/run_production.py`。

```bash
python scripts/run_production.py PJ-0001 --dry-run
```

本実行時:

```bash
python scripts/run_production.py PJ-0001
```

`PRODUCTION_MODE=live` と、Claude Code / Codex CLIのログイン済み環境が必要。テキストAI用APIキーは不要。

画像生成は `.env` の `IMAGE_BACKEND` で切り替える。

```text
IMAGE_BACKEND=local_webui  # 初回テスト・追加API費0円
IMAGE_BACKEND=openai       # 本番画像API
```

## 入力
最低限必要なのは求人原稿。ヒアリング資料・参考画像・補足テキストは任意。

```text
00_request/inbox/job_posting/   必須
00_request/inbox/hearing/       任意
00_request/inbox/references/    任意
```

求人原稿だけで制作に必要な情報が揃う場合は進行する。不足が制作を止める場合だけ `needs_clarification` とし、人間へ最小限の確認を返す。

## 基本ワークフロー
1. Input normalization
2. Recruitment Analyst (Claude Code)
3. Codex Fact Gate
4. Production Director (Claude Code)
5. Codex Strategy Gate
6. Copy Director (Claude Code)
7. Art Director (Claude Code)
8. Prompt Designer (Claude Code)
9. Codex Direction Gate
10. Image Generation (local or OpenAI)
11. Creative Reviewer (Claude Code)
12. Codex Final Traceability Gate
13. Revision Loop（必要時、最大3回を原則）
14. Human Final Approval
15. Delivery

Prompt Designerの成果物もDirection Gateの対象であり、承認済みCopy/ArtをPromptが勝手に変更していないことを生成前に検証する。

## コンペ原則
最高品質モードでは最初の案をそのまま採用しない。
- Strategy: 5候補以上を原則とする
- Copy: 3候補以上を原則とする
- Art: 2候補以上を原則とする
- Codexが比較・承認したものだけ次へ進む

## コスト原則
- Claude/Codexテキスト工程の増分APIコストは0円として管理する（既存契約の利用枠は消費する）。
- `IMAGE_BACKEND=local_webui` は画像API増分コスト0円として扱う。
- `IMAGE_BACKEND=openai` の場合のみ画像APIコストを400円/最終画像の上限管理へ含める。
- OpenAI画像API利用時、未承認Creativeが推定330円以上に達した場合、新しい有料自動修正を開始しない。

## 参照優先度
1. 自分の `.claude/agents/<role>.md`
2. 対応 `schemas/*.schema.json`
3. Codexから渡された承認済み上流成果物
4. Google Drive案件のOriginal Request / source-bundle
5. `rules/quality.md`
6. `configs/quality.yaml`
7. `configs/workflow.yaml`

## 出力責任
Claudeの成果物は、後続AgentとCodexが機械的に検証できること。自由作文ではなく、意味・根拠・選択理由・問題点を構造化して返す。
