# Local Image AI Setup for First Test

初回E2Eテストでは画像生成APIを使わず、PC上のローカル画像AIを使用する。

本システムは3つの画像バックエンドを切り替えられる。

```text
IMAGE_BACKEND=openvino_ovms   Intel Windows推奨 / ローカル / 追加API費0円
IMAGE_BACKEND=local_webui     AUTOMATIC1111 / Forge / ローカル / 追加API費0円
IMAGE_BACKEND=openai          OpenAI Image API / 本番高品質
```

## Intel Iris Xe の初回推奨

Intel Iris Xeを搭載したWindows PCでは `openvino_ovms` を第一候補とする。

OpenVINOはIntel Iris Xe Graphicsをサポートし、OpenVINO Model ServerはローカルにOpenAI互換の画像生成endpointを公開できる。

初回テストでは負荷を抑えるため以下を使用する。

```text
Model: OpenVINO/stable-diffusion-v1-5-int8-ov
Device: GPU
Generation size: 512x512
Steps: 10
```

SDXLより品質は低いが、まず「Codex + Claude + ローカル画像 + Review」のE2E動作確認を追加API費0円で行うことを優先する。

---

# A. Intel OpenVINOセットアップ

## 1. GPU確認

```powershell
python scripts/check_local_gpu.py
```

Intel Iris Xeが表示されればOpenVINO GPU候補として進む。

## 2. OpenVINO Model Serverを導入

リポジトリ直下から:

```powershell
.\scripts\setup_openvino_image.ps1
```

このスクリプトはOpenVINO公式Windows packageをユーザーローカル領域へ展開する。

既定インストール先:

```text
%LOCALAPPDATA%\JOBOLE-Image-Creator-Team\openvino-model-server
```

モデル本体はGitHubリポジトリへ保存しない。

Windows版OVMSはMicrosoft Visual C++ Redistributableを必要とする。起動時にruntime DLL不足が出る場合はMicrosoft Visual C++ Redistributableを導入/更新する。

## 3. `.env` をIntelローカルモードへ

```env
IMAGE_BACKEND=openvino_ovms
OPENVINO_IMAGE_API_URL=http://127.0.0.1:8000
OPENVINO_IMAGE_MODEL=OpenVINO/stable-diffusion-v1-5-int8-ov
OPENVINO_IMAGE_STEPS=10
OPENVINO_IMAGE_GENERATION_SIZE=512x512
OPENVINO_IMAGE_TIMEOUT_SEC=1200
```

テキストAIはAPIキー不要。

```env
CLAUDE_CLI_COMMAND=claude
CLAUDE_CLI_MODEL=opus
CODEX_CLI_COMMAND=codex
```

初回ローカル画像テストでは以下は空欄でよい。

```env
OPENAI_API_KEY=
OPENAI_IMAGE_MODEL=
```

## 4. Claude / Codexログイン確認

画像サーバー未導入でも先に確認可能。

```powershell
python scripts/validate_system.py --verify-login
```

`--verify-login` は画像backend設定を検査しない。
Claude Code / Codex CLIの契約ログインだけを確認する。

## 5. OpenVINO画像サーバー起動

新しいPowerShellを1つ開き、リポジトリで:

```powershell
.\scripts\start_openvino_image.ps1
```

既定ではIntel GPUを使用する。

```text
Device: GPU
Model: OpenVINO/stable-diffusion-v1-5-int8-ov
Endpoint: http://127.0.0.1:8000/v3/images/generations
```

初回はモデルのダウンロードが発生するため時間がかかる。
このPowerShellは画像生成中ずっと開いておく。

GPU初期化・メモリ不足等で起動できない場合はCPUフォールバック:

```powershell
.\scripts\start_openvino_image.ps1 -Device CPU
```

CPUは遅いが、E2E疎通テスト用途には使用できる。

## 6. 接続確認（画像生成なし）

画像サーバーを起動したまま別PowerShellで:

```powershell
python scripts/check_local_image.py
```

または:

```powershell
python scripts/validate_system.py --verify-image
```

成功時は `backend: openvino_ovms` とローカルモデル情報が表示される。
この確認では画像は生成しない。

## 7. ローカル画像を1枚だけ生成

```powershell
python scripts/test_local_image_generation.py
```

成功時:

```text
LOCAL IMAGE GENERATION: PASS
Output: ...\tmp\local-image-test.png
Incremental cloud image API cost: 0 JPY
```

## 8. 初回E2Eテスト

求人原稿が入った制作枚数1の案件で:

```powershell
python scripts/run_production.py PJ-XXXX --dry-run
```

PASS後:

```powershell
python scripts/run_production.py PJ-XXXX
```

使用するもの:
- Claude Code契約利用枠
- Codex/ChatGPT契約利用枠
- Intel GPU/CPUのローカル計算
- 電力

追加のテキストAPI費・画像API費は0円。

---

# B. AUTOMATIC1111 / Forgeを使う場合

主にNVIDIA GPU等で既存WebUI環境を使う場合の代替backend。

`.env`:

```env
IMAGE_BACKEND=local_webui
LOCAL_IMAGE_API_URL=http://127.0.0.1:7860
LOCAL_IMAGE_MODEL=local-loaded-checkpoint
LOCAL_IMAGE_STEPS=28
LOCAL_IMAGE_CFG_SCALE=6.5
LOCAL_IMAGE_SAMPLER=DPM++ 2M
LOCAL_IMAGE_MAX_SIDE=1024
LOCAL_IMAGE_TIMEOUT_SEC=600
```

WebUIはREST APIを有効にして起動する。

```text
GET  /sdapi/v1/options
GET  /sdapi/v1/sd-models
POST /sdapi/v1/txt2img
```

---

# C. 本番をOpenAI Image APIへ切り替える

ローカル画像品質・速度が本番基準に届かない場合でも、AI制作組織は変更しない。

`.env` の画像backendだけ変更する。

```env
IMAGE_BACKEND=openai
OPENAI_API_KEY=<image API only>
OPENAI_IMAGE_MODEL=<current image model>
OPENAI_IMAGE_QUALITY=high
USDJPY_RATE=<budget rate>
OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION=<budget estimate>
```

Recruitment / Strategy / Copy / Art / Prompt / Claude Review / Codex Quality Gateは引き続き契約ログインで動作する。

---

# セキュリティ

ローカル画像サーバーは `127.0.0.1` のみで使用する。
外部インターネットへ画像生成endpointを公開しない。

実案件データ・生成画像・モデル本体をGitHubへコミットしない。
