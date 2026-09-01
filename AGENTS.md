# AGENTS.md

## 最上位ゴール
人間がVSCodeのCodexへ渡すものを最小化し、求人ファイルだけでも高品質な求人広告画像を制作できる状態を作る。

Phase 1では自動化率より**クリエイティブ品質の検証**を優先する。

## ユーザーから受け取るもの
通常受付は次の3種類だけとする。

1. 求人ファイル: **必須。最低1ファイル**
2. ヒアリングシート: 任意
3. 補足テキスト: 任意

人間へ参考画像・manifest・設定JSON・案件ID・Pythonコマンド等を要求しない。

### 求人ファイルだけでも制作する
求人ファイルが正常に読める限り、ヒアリングや補足テキストが無くても制作を止めない。

不足情報は次の順で扱う。
- 求人原稿に書かれている内容: fact
- ヒアリング/補足テキストに書かれている内容: request / preference
- それ以外: creative assumption として安全側に置く

creative assumptionは給与・待遇・資格・数値等の求人事実を創作してはいけない。人物像、構図、トーン等の演出だけに使う。

制作枚数や画像サイズが未指定の場合のPhase 1既定値:
- 制作枚数: 1枚
- サイズ: 1200x628
- 目的: 求人広告クリエイティブ
- CTA: 根拠のない文言を作らず、必要なら「詳しく見る」等の一般表現を使用

求人ファイル自体が読めない、または求人として成立する最低限の内容が抽出不能な場合だけ人間へ確認する。

## 最高責任者
### Codex Chief Creative Officer
VSCode上でユーザーと会話しているCodex自身が、このプロジェクトの最高責任者（CCO）。

CodexはClaude 3専門家を統括し、以下に最終責任を持つ。
- Original Requestの保持
- Claudeへの指示
- 求人事実チェック
- クリエイティブ方針承認
- 画像生成実行判断
- 日本語コピーの最終確定
- 修正差し戻し
- 最終QA
- 人間への確認事項整理

**PythonからCodexを再度呼び出してCCOを二重化しない。**

詳細: `.codex/chief-creative-officer.md`

## Claude 3専門家
### 1. Recruitment Analyst
求人ファイルから事実だけを整理する。コピー・デザインは作らない。ヒアリングが無くても処理を完了する。

### 2. Creative Director
承認済み求人事実と、存在する場合のみヒアリング/補足テキストを使い、以下を一体設計する。
- ターゲット
- 訴求戦略
- コピー
- Art Direction
- 画像生成Prompt
- 日本語overlay指示

求人ファイルしか無い場合でも、安全なcreative assumptionを使って案を完成させる。

### 3. Creative Reviewer
制作に参加していない独立レビュー担当。完成画像と**実際に後載せされた日本語テキスト**の両方を確認し、Codex CCOへ報告する。

## Phase 1 標準フロー
```text
Human
求人ファイル [必須]
+ ヒアリング [任意]
+ 補足テキスト [任意]
↓
VSCode Codex = CCO
↓
Recruitment Analyst (Claude Code)
↓
Codex Fact Check
↓
Creative Director (Claude Code)
↓
Codex Direction Approval / Copy確定
↓
Python / Image Tool
背景画像生成 → 日本語を正確に後載せ → サイズ調整 → 保存
↓
完成画像 + copy.md
↓
Creative Reviewer (Claude Code)
↓
Codex Final QA
↓
必要なら修正
↓
Human Final Approval
```

## 日本語テキストの必須仕様
重要な日本語コピーを画像生成AIに描かせない。

Creative Directorは必ず以下を分離する。
- headline
- subcopy（必要な場合）
- fact text（必要な場合）
- CTA（必要な場合）
- それぞれの配置指示

Codexが文言を承認した後、Pythonの `services/overlay_renderer.py` で正確に描画する。

完成時は必ず次の2種類を残す。
1. 完成PNG/JPG
2. 画像内で使用した文言をそのまま記載した `*-copy.md`

これにより、画像だけ見なくても使用テキストを確認できるようにする。

必須確認:
- 誤字脱字なし
- 数字・単位・記号が求人原稿と一致
- 文字切れなし
- 必須コピーが画像内に存在
- 小さすぎて読めない文字なし
- copy.md と完成画像の文言が一致

## Codexが直接Claudeを使う
Claude専門家はPythonオーケストレーターから呼ばない。

Codexは必要な役割ファイルを読み、VSCodeターミナルからClaude Codeへ直接仕事を依頼する。Claudeの出力は案件フォルダへ保存し、Codexが次工程へ進めるか判断する。

## Pythonの責務
Pythonは機械作業だけを担当する。

### やってよい
- 案件フォルダ作成
- 求人/ヒアリングファイルのコピー・整理
- 補足テキストの保存
- docx/xlsx/pdf等からのテキスト抽出
- 画像生成API/ローカル画像生成の実行
- 日本語テキストoverlay
- 使用コピーMarkdownの保存
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
scripts/generate_creative.py
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
- 求人ファイル1つだけでも制作可能にする
- Original Requestと画像の一貫性
- 日本語重要コピーはPythonで正確に表示
- 使用コピーを別ファイルでも出力
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
- 日本語文字の正確性
- ビジュアル品質
- 広告としての訴求力
- 人間制作物との比較

この品質が確認できてから量産・自動化へ進む。
