# AGENTS.md

## 最上位ゴール
人間がVSCodeのCodexへ、求人原稿・ヒアリング・参考画像・補足テキストを渡すだけで、少数の高品質広告画像を制作できる状態を作る。

Phase 1では自動化率より**クリエイティブ品質の検証**を優先する。

## 最高責任者
### Codex Chief Creative Officer
VSCode上でユーザーと会話しているCodex自身が、このプロジェクトの最高責任者（CCO）。

CodexはClaude 3専門家を統括し、以下に最終責任を持つ。
- Original Requestの保持
- Claudeへの指示
- 求人事実チェック
- クリエイティブ方針承認
- 画像生成実行判断
- 修正差し戻し
- 最終QA
- 人間への確認事項整理

**PythonからCodexを再度呼び出してCCOを二重化しない。**

詳細: `.codex/chief-creative-officer.md`

## Claude 3専門家
### 1. Recruitment Analyst
求人原稿から事実だけを整理する。コピー・デザインは作らない。

### 2. Creative Director
承認済み求人事実と依頼内容から、以下を一体設計する。
- ターゲット
- 訴求戦略
- コピー
- Art Direction
- 画像生成Prompt
- 日本語overlay指示

### 3. Creative Reviewer
制作に参加していない独立レビュー担当。完成画像の問題を診断し、Codex CCOへ報告する。

## Phase 1 標準フロー
```text
Human
↓
VSCode Codex = CCO
↓
Recruitment Analyst (Claude Code)
↓
Codex Fact Check
↓
Creative Director (Claude Code)
↓
Codex Direction Approval
↓
Python / Image Tool
画像生成・文字入れ・サイズ調整・保存
↓
Creative Reviewer (Claude Code)
↓
Codex Final QA
↓
必要なら修正
↓
Human Final Approval
```

## Codexが直接Claudeを使う
Claude専門家はPythonオーケストレーターから呼ばない。

Codexは必要な役割ファイルを読み、VSCodeターミナルからClaude Codeへ直接仕事を依頼する。

概念例:
```powershell
Get-Content .claude/agents/recruitment-analyst.md -Raw | claude -p
```

実案件では、役割定義に加えて対象求人・依頼内容・前工程の承認済み成果物を渡す。

Claudeの出力は案件フォルダへ保存し、Codexが次工程へ進めるか判断する。

## Pythonの責務
Pythonは機械作業だけを担当する。

### やってよい
- 案件フォルダ作成
- 入力ファイルコピー・整理
- docx/xlsx/pdf等からのテキスト抽出
- 画像生成API/ローカル画像生成の実行
- 日本語テキストoverlay
- リサイズ・クロップ
- ファイル名・保存先管理
- 最低限の技術チェック

### やってはいけない
- Claude/Codexの自動組織運営
- ターゲット決定
- 訴求戦略決定
- コピー選定
- Art Direction決定
- Quality Gateの最終判断
- Codexの代わりの最終QA

## 入力
最低限必要なのは求人原稿。
- 求人原稿: 必須
- ヒアリング: 任意
- 参考画像: 任意
- 補足テキスト: 任意

不足が制作を止める場合だけ、人間へ最小限の確認を返す。

## Phase 1で使う主なファイル
```text
.codex/chief-creative-officer.md
.claude/agents/recruitment-analyst.md
.claude/agents/creative-director.md
.claude/agents/creative-reviewer.md
configs/agents.yaml
configs/workflow.yaml
rules/quality.md
scripts/create_project_from_intake.py
scripts/input_loader.py
services/image_generator.py
services/overlay_renderer.py
```

## Phase 1では本流から外すもの
以下は将来Phase 2以降で必要になったら再評価する。
- Production Director / Copy Director / Art Director / Prompt Designerの4分割
- PythonからCodex/Claudeを多段実行するAIオーケストレーション
- 4段階の細かいQuality Gate
- 詳細JSON Schema連携
- 詳細Usage Tracker
- 100枚前提の状態管理
- Slack受付
- サーバー常駐型自動化
- 複数ローカル画像基盤の作り込み

## 画像生成方針
Phase 1では画像生成方式そのものを目的にしない。

優先順位:
1. 既に動く画像生成方法
2. OpenAI Image API（本番品質検証時）
3. ローカル画像AIは無料テスト用の補助経路

ローカル画像AIのトラブル解決がクリエイティブ品質検証を長期間止める場合は、本流から外してよい。

## 品質原則
- 求人事実一致を最優先
- Original Requestと画像の一貫性
- 日本語重要コピーは正確に表示
- 根拠のないNo.1、最短、必ず、保証、数値を作らない
- CreatorとReviewerを分離する
- Reviewer PASSだけで最終承認しない
- Codex CCOが必ず最終QAする
- 人間の最終承認を残す

## Phase 1成功条件
実求人1件から1〜3枚を作り、人間が以下を評価できること。
- 求人理解
- ターゲット理解
- コピー品質
- ビジュアル品質
- 広告としての訴求力
- 人間制作物との比較

この品質が確認できてから量産・自動化へ進む。
