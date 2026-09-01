# JOBOLE Image Creator Team

JOBOLE向け広告画像を、**VSCode Codex Chief Creative Officer + Claude 3専門家 + Python画像/ファイル処理**で制作するPhase 1構成です。

## 最終ユーザー体験
ユーザーから送るものは原則これだけです。

必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

**求人ファイル1つだけでも画像生成まで進めます。**

求人ファイルが正常に読める限り、ヒアリングや補足テキストが無いことを理由に制作を止めません。

## 未指定時のPhase 1既定値
- 制作枚数: 1枚
- サイズ: 1200x628
- 目的: 求人広告画像

ユーザーに案件ID、manifest、設定JSON、参考画像、Pythonコマンド等を要求しないことを標準とします。

## Phase 1の目的
まず実求人1件から1〜3枚を作り、AIチームのクリエイティブ品質を人間が評価できる状態にする。

量産・Slack・複雑な状態管理・自動コスト制御より、先に以下を検証する。
- 求人理解
- ターゲット理解
- コピー品質
- 日本語テキストの正確性
- ビジュアル品質
- 広告としての訴求力
- 人間制作物との比較

## AI組織
```text
Human
求人ファイル [必須]
+ ヒアリング [任意]
+ 補足テキスト [任意]
↓
VSCode Codex = Chief Creative Officer / 最高責任者
│
├─ Claude Recruitment Analyst
├─ Claude Creative Director
└─ Claude Creative Reviewer
```

Codexは3専門家を統括し、求人事実確認・クリエイティブ方針承認・コピー確定・差し戻し・最終QAを行います。

## 標準フロー
```text
Human
↓
VSCode Codex CCO
↓
Claude Recruitment Analyst
↓
Codex Fact Check
↓
Claude Creative Director
↓
Codex Direction Approval / 日本語コピー確定
↓
Python / Image Tool
文字なし背景生成
↓
Python日本語overlay
↓
完成画像 + *-copy.md
↓
Claude Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

## 重要な設計原則
- 今ユーザーと会話しているVSCode Codex自身が最高責任者。
- PythonからCodexを再度呼び出してCCOを二重化しない。
- ClaudeはPythonオーケストレーターではなく、Codexが直接Claude Codeで呼ぶ。
- Pythonは判断をしない。画像・ファイルの機械処理だけを行う。
- ヒアリング不足だけで制作を止めない。
- 求人事実は推測しないが、人物・背景・構図・トーン等は安全なcreative assumptionを使ってよい。
- Phase 1ではProduction / Copy / Art / Promptの4Agent分割を使わない。Creative Directorへ統合する。
- 大量JSON Schemaや4段階の細かいQuality GateはPhase 1本流から外す。

## 3専門家
### Recruitment Analyst
求人ファイルから事実だけを整理し、Fact Sheetを作る。ヒアリングが無くても処理を完了する。

### Creative Director
Fact Sheetと、存在する場合のみヒアリング/補足テキストから以下を一体設計する。
- Target
- Key Message
- 訴求優先順位
- Copy Candidates
- Recommended Copy
- Art Direction
- Image Prompt
- Overlay Text

求人ファイルだけでも案を完成させる。

### Creative Reviewer
完成画像と `*-copy.md` を独立レビューし、PASS / REVISION / REDESIGNと具体的な問題をCodexへ返す。

## 日本語テキストの扱い
求人広告で重要な日本語コピーは画像生成AIへ描かせません。

```text
画像AI
→ 人物・背景・構図だけ生成

Python
→ Codexが確定した日本語コピーを正確に後載せ
```

これにより、AI画像で起こりやすい文字化け・誤字・崩れを避けます。

完成時は必ず以下をセットで出力します。

```text
creative-01.png
creative-01-copy.md
```

`*-copy.md` には画像へ実際に後載せした元文言をそのまま保存します。

確認対象:
- headline
- subcopy
- fact text
- CTA
- 数字・単位・記号

## Pythonの役割
### 使用する
- `scripts/create_project_from_intake.py`: 求人/任意ヒアリング/任意テキストから案件作成
- `scripts/input_loader.py`: 入力テキスト整理
- `scripts/generate_creative.py`: 文字なし画像生成 → 日本語overlay → copy.md保存
- `services/image_generator.py`: 画像生成実行
- `services/overlay_renderer.py`: 日本語文字入れ・日本語折り返し

### 使用しない
`scripts/run_production.py` は旧AIオーケストレーターとしてdeprecated。Phase 1では実行しません。

## 求人ファイルだけの案件で推測してよいもの
- 人物像
- 服装
- 背景
- 構図
- 色・トーン
- カメラ距離

## 推測してはいけないもの
- 給与
- 待遇
- 休日
- 勤務時間
- 資格
- 経験年数
- 数値実績
- No.1 / 最短 / 保証等

## 認証
- Codex CCO: ChatGPTログイン
- Claude 3専門家: Claude Codeログイン
- テキストAI用APIキー: 不要
- OpenAI APIを使う場合: 画像生成だけ

## 画像生成
画像生成方式そのものを目的にしません。

Phase 1では「既に動く方法」を優先し、ローカル画像AIのトラブルが品質検証を止める場合はOpenAI Image APIへ切り替えてよい設計です。

ローカル画像AIは無料テスト用の補助経路として扱います。

## データ管理
```text
GitHub
├─ Codex / Claude役割
├─ 品質ルール
├─ Workflow
└─ 汎用Pythonユーティリティ

Google Drive
└─ projects/
   └─ 実案件・求人ファイル・ヒアリング・補足テキスト・生成画像・レビュー・納品物
```

実案件データや顧客素材をGitHubへコミットしません。

## 構造確認
```powershell
python -m pip install -r requirements.txt
python -m compileall scripts services
python scripts/validate_system.py
```

期待値:
```text
SYSTEM VALIDATION: PASS
Claude specialists: 3
Codex CCO: VSCode highest authority
Python AI orchestration: DISABLED
Text API keys required: NO
```

## Phase 2以降
Phase 1で品質が確認できてから追加を検討する。
- 10〜100枚量産
- 詳細manifest
- 自動修正ループ
- コスト自動管理
- Contact Sheet自動化
- Slack受付
- Cloud常駐処理
- Agent再細分化

## 開発方針
- `main` は安定版
- 変更はfeature branch + Pull Request
- 人間の最終承認前に外部納品しない
- 複雑化する前に「本当に画像品質を上げるか」を確認する
