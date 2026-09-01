# Maximum Quality Live Setup

このドキュメントは `Codex CCO + Claude specialist agents + GPT Image` の最高品質モードを、最初の1枚だけ安全にlive実行するための手順です。

## 原則

- APIキーはGitHubへコミットしない。
- `.env` はローカルPCだけに置く。
- 最初のliveテストは必ず1案件・1画像にする。
- `python scripts/validate_system.py --live-config` がPASSするまで本番実行しない。
- 最終画像1枚の予算上限は400円。
- 330円以上では次の有料再生成へ進まない。
- 400円以上は `needs_human_review` で停止する。

## 推奨モデル（最高品質モード）

2026-09-01時点の推奨値。モデル・料金は将来変わるため、本番切替前に各Providerの公式料金を再確認する。

```env
ANTHROPIC_MODEL=claude-opus-5
OPENAI_CCO_MODEL=gpt-5.6-sol
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=high
```

## 料金トラッキング

以下は2026-09-01時点のテキストAPI価格を使う場合の設定例。

```env
ANTHROPIC_INPUT_USD_PER_M=5
ANTHROPIC_OUTPUT_USD_PER_M=25
OPENAI_CCO_INPUT_USD_PER_M=4
OPENAI_CCO_OUTPUT_USD_PER_M=20
```

画像生成はGPT Image 2がtoken課金のため、初期テストでは `OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION` に保守的な予算値を設定する。初回liveの実請求を確認した後に調整する。

予算管理では実勢為替そのものではなく、円安方向へ余裕を持たせた管理レートを `USDJPY_RATE` に入れてもよい。

例:

```env
USDJPY_RATE=165
OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION=0.25
```

上記 `165` と `0.25` は料金表ではなく、400円上限を守るための保守的な初期予算設定値。

## .env 例

```env
PROJECTS_ROOT=G:/共有ドライブ/.../JOBOLE-Image-Creator-Team/projects
LOCAL_TEMP_ROOT=./tmp

ANTHROPIC_API_KEY=<local secret>
ANTHROPIC_MODEL=claude-opus-5

OPENAI_API_KEY=<local secret>
OPENAI_CCO_MODEL=gpt-5.6-sol
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=high

JAPANESE_FONT_PATH=C:/Windows/Fonts/YuGothB.ttc

USDJPY_RATE=165
ANTHROPIC_INPUT_USD_PER_M=5
ANTHROPIC_OUTPUT_USD_PER_M=25
OPENAI_CCO_INPUT_USD_PER_M=4
OPENAI_CCO_OUTPUT_USD_PER_M=20
OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION=0.25

PRODUCTION_MODE=live
```

## API呼び出しなしの最終確認

```powershell
python scripts/validate_system.py --live-config
```

このコマンドは設定値を確認するだけで、Claude/OpenAI APIは呼ばない。

期待値:

```text
SYSTEM VALIDATION: PASS
Agents: 6 Claude specialists
Codex CCO: configured
Quality Gates: 4
Revision limit: 3
Target max cost: 400 JPY/final image
Runtime pipeline: configured
Live configuration: PASS (no API calls were made)
```

## 初回liveテスト

テスト専用案件を制作枚数1で作り、求人原稿を1件だけ配置する。

```powershell
python scripts/run_production.py PJ-XXXX
```

正常完了時は以下を確認する。

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

## 初回テストで確認する指標

- 求人事実の誤り: 0件
- Codex Gateが実際に厳しく機能しているか
- Claude Reviewer / Codex Final Gateの点数妥当性
- 日本語文字の正確性
- クリエイティブとしての訴求力
- 修正ループの原因分類が正しいか
- 1枚あたり実測コスト
- 人間による最終評価

初回実測をもとに、400円以内で品質が最大化するようモデル、候補数、出力token、再生成回数を調整する。
