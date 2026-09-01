# JOBOLE Image Creator Team

JOBOLE向け広告画像を、**VSCode Codex Chief Creative Officer + Claude 3専門家 + Python画像/ファイル処理**で制作するPhase 1構成です。

# 最終ユーザー体験
ユーザーから送るものは原則これだけです。

必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

求人ファイル1つだけでも制作します。

未指定時:
- 1枚
- 1200x628
- 求人広告画像

# AI組織
```text
Human
↓
VSCode Codex = Chief Creative Officer / 最高責任者
│
├─ Claude Recruitment Analyst
├─ Claude Creative Director
└─ Claude Creative Reviewer
```

# 必須の最初の処理: Google Drive案件作成
画像生成より先にCodexが `scripts/create_project_from_intake.py` を実行します。

`.env` の `PROJECTS_ROOT` 配下へ、案件ごとのフォルダを作ります。

想定:
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/projects
```

例:
```text
projects/
└─ PJ-0003_求人名/
   ├─ project.yaml
   ├─ 00_request/
   ├─ 01_strategy/
   ├─ 02_direction/
   ├─ 03_batches/
   ├─ 04_project_review/
   └─ 05_delivery/
```

Codexは `PROJECT_DIR` と `project.yaml` を確認するまで制作工程へ進みません。

案件作成に失敗した場合、Desktop / repo / tmpへ画像だけ生成する代替処理は禁止です。

# 標準フロー
```text
求人ファイル [必須]
+ ヒアリング [任意]
+ 補足テキスト [任意]
↓
Codex CCO
↓
Google Drive案件フォルダ作成・確認
↓
Claude Recruitment Analyst
↓
Codex Fact Check
↓
Claude Creative Director
↓
Codex Direction Approval / 日本語コピー確定
↓
Python Image Tool
03_batchesへ文字なし背景生成
↓
Python Typography Overlay
↓
05_deliveryへ完成画像 + copy.md
↓
Claude Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

# 3専門家
## Recruitment Analyst
求人ファイルから事実だけを整理します。ヒアリング無しでも処理を完了します。

## Creative Director
Fact Sheetと、存在する場合のみヒアリング/補足テキストから一体設計します。
- Target
- Key Message
- Appeal Priority
- Copy Candidates
- Recommended Copy
- Art Direction
- Typography / Visual Hierarchy
- Image Prompt
- Overlay Text

単なる求人条件の羅列ではなく、求人事実に基づく**求職者メリットが一目で伝わる情報設計**を優先します。

## Creative Reviewer
完成画像と `*-copy.md` を独立レビューします。

事実だけでなく、次も評価します。
- Headlineが最初に目に入るか
- メリットが1〜2秒で理解できるか
- Headline / Fact / CTAに視覚的な役割差があるか
- 全テキストが同じ白いボックスになっていないか
- スマホ縮小でも主訴求が読めるか

# 日本語Typography
重要な日本語コピーは画像生成AIへ描かせません。

```text
画像AI
→ 人物・背景・構図・余白だけ生成

Python
→ Codexが確定した日本語を正確にデザインして後載せ
```

標準 `modern_recruit` スタイル:
- Headline: 大きな太字 + アクセントライン
- Subcopy: 軽いウェイトで補強
- Fact: 1〜3個のメリットチップ/バッジ
- CTA: アクセント色ボタン
- 左側: 個別白ボックスの反復ではなく一体的な読みやすいTypography領域

完成時:
```text
05_delivery/
├─ CR001.png
└─ CR001-copy.md
```

`CR001-copy.md` には画像へ実際に載せたheadline/subcopy/fact/CTAをそのまま保存します。

# 案件内の画像保存
正式生成スクリプト `scripts/generate_creative.py` は `--project-id` が必須です。

案件が存在しない場合は生成できません。

保存先:
```text
03_batches/CR001/v001/background.png
03_batches/CR001/v001/image-prompt.txt
05_delivery/CR001.png
05_delivery/CR001-copy.md
```

# Pythonの役割
使用:
- `scripts/create_project_from_intake.py`: 案件作成
- `scripts/input_loader.py`: 入力テキスト整理
- `scripts/generate_creative.py`: 案件内画像生成 + Typography + copy.md
- `services/image_generator.py`: 画像生成
- `services/overlay_renderer.py`: 日本語Typography

Pythonにはターゲット・訴求・コピー・Art Direction・最終QAを判断させません。

# 推測ルール
求人ファイルだけの場合でも、以下は安全なcreative assumptionとして設定できます。
- 人物像
- 服装
- 背景
- 構図
- 色・トーン
- カメラ距離

推測禁止:
- 給与
- 待遇
- 休日
- 勤務時間
- 資格
- 経験年数
- 数値実績
- No.1 / 最短 / 保証等

# 認証
- Codex CCO: ChatGPTログイン
- Claude 3専門家: Claude Codeログイン
- テキストAI用APIキー: 不要
- OpenAI APIを使う場合: 画像生成だけ

# 構造確認
```powershell
python -m pip install -r requirements.txt
python -m compileall scripts services
python scripts/validate_system.py
```

期待値には以下が含まれます。
```text
SYSTEM VALIDATION: PASS
Claude specialists: 3
Codex CCO: VSCode highest authority
Python AI orchestration: DISABLED
Text API keys required: NO
Project-scoped generation: REQUIRED before any final image
Final output: PROJECT_DIR/05_delivery + companion copy.md
Typography: modern_recruit hierarchy + deterministic Japanese overlay
```

# Phase 2以降
Phase 1で品質が確認できてから追加を検討します。
- 10〜100枚量産
- 詳細manifest
- 自動修正ループ
- コスト自動管理
- Slack受付
- Cloud常駐処理
- Agent再細分化

複雑化する前に「本当に画像品質を上げるか」を確認します。
