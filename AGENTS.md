# AGENTS.md

## 最上位ゴール
人間がVSCodeのCodexへ求人ファイルを渡すだけでも、案件フォルダ作成から高品質な求人広告画像の保存まで進められる状態を作る。

Phase 1では自動化率よりクリエイティブ品質を優先するが、**案件データの保存先だけは例外なく統一する。**

## ユーザーから受け取るもの
通常受付は次の3種類だけ。

1. 求人ファイル: **必須。最低1ファイル**
2. ヒアリングシート: 任意
3. 補足テキスト: 任意

人間へmanifest、設定JSON、案件ID、Pythonコマンド等を要求しない。

求人ファイルが正常に読める限り、ヒアリングや補足テキストが無くても制作を止めない。

未指定時のPhase 1既定値:
- 制作枚数: 1枚
- サイズ: 1200x628
- 目的: 求人広告クリエイティブ
- CTA: 必要なら「詳しく見る」等の一般表現

求人条件・給与・待遇・資格・数値は推測しない。人物、構図、背景、色、トーン等は求人事実と矛盾しない範囲でcreative assumptionを置いてよい。

# Hard Rule: 案件フォルダを最初に作る
画像制作依頼を受けたら、**Claude分析・画像生成・コピー制作より先に案件フォルダを作る。**

標準保存先はリポジトリ `.env` の `PROJECTS_ROOT`。
想定:
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

## 最初の必須処理
Codexが `scripts/create_project_from_intake.py` を実行する。

求人ファイルだけの場合の概念例:
```powershell
python scripts/create_project_from_intake.py --job-posting "<求人ファイルの実パス>"
```

ヒアリング/補足テキストがあれば同じ案件作成時に追加する。

標準出力から必ず次を取得する。
```text
PROJECT_ID=PJ-xxxx
PROJECT_DIR=G:\...\projects\PJ-xxxx_...
```

その後、Codex自身が `PROJECT_DIR` と `project.yaml` の存在を確認してから次工程へ進む。

### 作成失敗時
- 画像生成を開始しない
- Desktop、repo直下、tmp等へ代替出力しない
- `PROJECTS_ROOT`、Drive接続、権限、パス等の原因を解消する

**案件フォルダの無い画像を正式成果物として扱わない。**

# 案件内の保存ルール
```text
PROJECT_DIR/
├─ project.yaml
├─ creative-manifest.csv
├─ 00_request/
│  └─ inbox/
│     ├─ job_posting/
│     ├─ hearing/
│     └─ request_text/
├─ 01_strategy/
│  └─ recruitment/
├─ 02_direction/
├─ 03_batches/
│  └─ CR001/
│     └─ v001/
│        ├─ background.png
│        └─ image-prompt.txt
├─ 04_project_review/
└─ 05_delivery/
   ├─ CR001.png
   └─ CR001-copy.md
```

Claude/Codexの途中成果物も可能な限りこの案件内へ保存する。

# 最高責任者
## Codex Chief Creative Officer
VSCode上でユーザーと会話しているCodex自身が、このプロジェクトの最高責任者（CCO）。

CodexはClaude 3専門家を統括し、以下に最終責任を持つ。
- 求人ファイルを最上位の事実ソースとして保持
- 案件フォルダ作成と保存先確認
- Claudeへの指示
- 求人事実チェック
- クリエイティブ方針承認
- 画像生成実行判断
- 日本語コピーの最終確定
- 修正差し戻し
- 最終QA

PythonからCodexを再度呼び出してCCOを二重化しない。

詳細: `.codex/chief-creative-officer.md`

# Claude 3専門家
## 1. Recruitment Analyst
求人ファイルから事実だけを整理する。コピー・デザインは作らない。ヒアリングが無くても完了する。

## 2. Creative Director
承認済み求人事実と、存在する場合のみヒアリング/補足テキストを使い、以下を一体設計する。
- Target
- Key Message
- 訴求戦略
- コピー
- Art Direction
- Image Prompt
- Overlay Text
- Typography / Visual Hierarchy

求人ファイルしか無い場合でも、安全なcreative assumptionを使って完成案まで作る。

## 3. Creative Reviewer
制作に参加しない独立レビュー担当。完成画像と実際に後載せされた日本語テキストを確認し、Codex CCOへ報告する。

# Phase 1 標準フロー
```text
Human
求人ファイル [必須]
+ ヒアリング [任意]
+ 補足テキスト [任意]
↓
VSCode Codex = CCO
↓
案件フォルダ作成・PROJECT_DIR確認  ← 必ず最初
↓
Recruitment Analyst
↓
Codex Fact Check
↓
Creative Director
↓
Codex Direction Approval / Copy確定
↓
Python / Image Tool
案件内03_batchesへ背景生成
↓
Python Typography Overlay
↓
案件内05_deliveryへ完成画像 + copy.md
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

# 画像生成の保存制約
Phase 1正式生成は `scripts/generate_creative.py` を使う。

このスクリプトは `--project-id` を必須とし、案件が存在しなければ生成できない。

出力先:
- 生背景: `03_batches/<creative-id>/v001/background.png`
- Prompt: `03_batches/<creative-id>/v001/image-prompt.txt`
- 完成画像: `05_delivery/<creative-id>.png`
- 使用コピー: `05_delivery/<creative-id>-copy.md`

Codexは正式制作で任意の `--output C:\...` のような案件外保存を行わない。

# 日本語テキスト / デザインの必須仕様
重要な日本語コピーを画像生成AIに描かせない。

```text
Creative Director
↓
Codexが文言と情報階層を承認
↓
画像AIは文字なし背景/人物/構図を生成
↓
Python overlay_renderer
↓
正確な日本語 + デザイン済みTypography
```

## 標準の視覚階層
同じ白い角丸ボックスを全テキストへ繰り返さない。

- Headline: 最大の視線獲得要素。太字・大きなサイズ・アクセント要素
- Subcopy: Headlineを補強する軽い情報
- Fact: 1〜3個のメリットチップ/バッジとして整理
- CTA: アクセント色の明確なボタン
- 背景: テキスト側に意図的な余白を確保

条件をただ並べるのではなく、**求職者にとって何が嬉しいかが一目で分かるコピー階層**を優先する。ただし求人事実にない便益を断定しない。

必須確認:
- 誤字脱字なし
- 数字・単位・記号が求人ファイルと一致
- 文字切れなし
- Headlineが一瞬で読める
- 文字サイズに明確な強弱がある
- CTAとFactとHeadlineが同じ見た目になっていない
- copy.md と完成画像の文言が一致

# Pythonの責務
Pythonは機械作業だけを担当する。

やってよい:
- 案件フォルダ作成
- 求人/ヒアリングファイルのコピー・整理
- 補足テキスト保存
- docx/xlsx/pdf等からのテキスト抽出
- 画像生成実行
- 日本語Typography overlay
- 使用コピーMarkdown保存
- リサイズ・クロップ
- ファイル名・保存先管理

やってはいけない:
- Claude/Codexの自動組織運営
- ターゲット決定
- 訴求戦略決定
- コピー選定
- Art Direction決定
- Codex Final QAの代行

# 品質原則
- 求人事実一致を最優先
- 求人ファイル1つだけでも制作可能
- 案件フォルダ無しで正式生成しない
- 条件の羅列より求職者メリットの伝達を優先
- 日本語は正確さと広告としての魅力を両立
- 根拠のないNo.1、最短、必ず、保証、数値を作らない
- CreatorとReviewerを分離
- Reviewer PASSだけで最終承認しない
- Codex CCOが必ず最終QA
- Human Final Approvalを残す

# Phase 1成功条件
実求人1件から1〜3枚を案件フォルダ内に作り、人間が以下を評価できること。
- 求人理解
- ターゲット理解
- コピー品質
- 日本語文字の正確性
- Typography / 情報階層
- ビジュアル品質
- 広告としての訴求力
- 人間制作物との比較

この品質が確認できてから量産・自動化へ進む。
