# JOBOLE Image Creator Team

JOBOLE向け広告画像を、**VSCode Codex Chief Creative Officer + Claude 3専門家 + Python画像/ファイル処理**で制作するPhase 1構成です。

## Phase 1の目的
まず実求人1件から1〜3枚を作り、AIチームのクリエイティブ品質を人間が評価できる状態にする。

量産・Slack・複雑な状態管理・自動コスト制御より、先に以下を検証する。
- 求人理解
- ターゲット理解
- コピー品質
- ビジュアル品質
- 広告としての訴求力
- 人間制作物との比較

## AI組織
```text
Human
↓
VSCode Codex = Chief Creative Officer / 最高責任者
│
├─ Claude Recruitment Analyst
├─ Claude Creative Director
└─ Claude Creative Reviewer
```

Codexは3専門家を統括し、求人事実確認・クリエイティブ方針承認・差し戻し・最終QAを行う。

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
Codex Direction Approval
↓
Python / Image Tool
画像生成・文字入れ・サイズ調整・保存
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
- Phase 1ではProduction / Copy / Art / Promptの4Agent分割を使わない。Creative Directorへ統合する。
- 大量JSON Schemaや4段階の細かいQuality GateはPhase 1本流から外す。

## 3専門家
### Recruitment Analyst
求人原稿から事実だけを整理し、Fact Sheetを作る。

### Creative Director
Fact Sheetと依頼内容から以下を一体設計する。
- Target
- Key Message
- 訴求優先順位
- Copy Candidates
- Recommended Copy
- Art Direction
- Image Prompt
- Overlay Text

### Creative Reviewer
完成画像を独立レビューし、PASS / REVISION / REDESIGNと具体的な問題をCodexへ返す。

## Pythonの役割
### 使用する
- `scripts/create_project_from_intake.py`: 案件フォルダ作成・素材コピー
- `scripts/input_loader.py`: 入力テキスト整理
- `services/image_generator.py`: 画像生成実行
- `services/overlay_renderer.py`: 日本語文字入れ

### 使用しない
`scripts/run_production.py` は旧AIオーケストレーターとしてdeprecated。Phase 1では実行しない。

## 認証
- Codex CCO: ChatGPTログイン
- Claude 3専門家: Claude Codeログイン
- テキストAI用APIキー: 不要
- OpenAI APIを使う場合: 画像生成だけ

## 画像生成
画像生成方式そのものを目的にしない。

Phase 1では「既に動く方法」を優先し、ローカル画像AIのトラブルが品質検証を止める場合はOpenAI Image APIへ切り替えてよい。

ローカル画像AIは無料テスト用の補助経路として扱う。

## データ管理
```text
GitHub
├─ Codex / Claude役割
├─ 品質ルール
├─ Workflow
└─ 汎用Pythonユーティリティ

Google Drive
└─ projects/
   └─ 実案件・求人原稿・参考画像・生成画像・レビュー・納品物
```

実案件データや顧客素材をGitHubへコミットしない。

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

Claude/Codexログイン確認:
```powershell
python scripts/validate_system.py --verify-login
```

画像バックエンド確認は必要な場合だけ:
```powershell
python scripts/validate_system.py --verify-image
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
