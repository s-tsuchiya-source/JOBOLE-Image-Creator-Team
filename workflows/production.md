# Production Workflow

## 目的
VSCode Codexを入口に、Codex CCO・Claude Code専門Agent・画像生成バックエンドを標準化された順序で実行する。

## 認証
- Codex: ChatGPTログイン済みCodex IDE/CLI
- Claude: Claudeサブスクリプションへログイン済みClaude Code CLI
- テキストAI用APIキー: 使用しない
- 画像: `IMAGE_BACKEND=local_webui` または `openai`

## 流れ
1. Codex Intake が入力素材をGoogle Drive案件へ配置
2. Claude Recruitment Analyst が求人事実抽出
3. Codex Fact Gate
4. Claude Production Director がStrategy候補を作成
5. Codex Strategy Gate
6. Claude Copy Director がCopy候補を作成
7. Claude Art Director がArt候補を作成
8. Claude Prompt Designer が画像生成仕様を作成
9. Codex Direction Gate
10. 選択中の画像バックエンドで生成
11. 日本語重要テキストを正確に後載せ
12. Claude Creative Reviewer
13. Codex Final Traceability Gate
14. 必要なら原因Agentまで差し戻し、最大3回再制作
15. PASS画像を `05_delivery/` へ保存
16. コンタクトシートを生成
17. Human Final Approval

## 画像バックエンド

### 初回テスト
```env
IMAGE_BACKEND=local_webui
```
AUTOMATIC1111 / SD-WebUI-Forge互換ローカルAI。増分画像API費0円。

### 本番
```env
IMAGE_BACKEND=openai
```
OpenAI Image API。テキスト工程は引き続きCLIログインを使う。

## 禁止
- Quality Gate省略
- 求人事実の推測補完
- Claude/Codexテキスト工程でAPIキーを使う
- 原因を特定せず同じ生成を繰り返す
