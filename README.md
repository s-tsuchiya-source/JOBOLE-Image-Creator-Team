# JOBOLE Image Creator Team

**Phase 1 Final v1**

JOBOLE向け求人広告画像を、**VSCode Codex Chief Creative Officer + Claude 3専門家 + Python画像/ファイル処理**で制作します。

## 最終ユーザー体験
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

実働Claude Agentは3人だけです。Agent数を増やす前に、active Agentの専門判断基準を調整して品質を上げます。

Agent tuning guide:
- `.claude/agents/README.md`

## 3専門家

### Recruitment Analyst
求人ファイルから以下を整理します。
- Fact
- Evidence
- Advertising Leverage
- Claim Risk
- Job Reality

コピーやデザインは作りません。

### Creative Director
旧 Production / Copy / Art / Prompt Director の専門性を統合したCreative責任者です。

担当:
- Target hypothesis
- Appeal候補比較
- Copy候補比較
- Visual Route候補比較
- Art Direction
- Typography
- Image Prompt
- Overlay Text

単なる求人条件の羅列ではなく、**求人Fact → 求職者にとっての意味 → Key Message → Copy → Visual**を一貫させます。

### Creative Reviewer
完成画像と `*-copy.md` を独立Reviewします。

評価:
- Fact / Claim
- 1-second / 3-second advertising test
- Copy
- Visual / Job Reality
- Typography / Hierarchy
- Image Generation Quality
- Root Cause Routing

読めるだけではPASSしません。

## Codex CCO
`.codex/chief-creative-officer.md`

最高責任者として次を担当します。
- Google Drive案件作成確認
- Fact Gate
- Appeal / Copy / Visual候補選定
- Direction Approval
- Revision Routing
- Final QA
- Human Final Approvalへの引き渡し

ClaudeのRecommendedを自動採用せず、Codex自身が比較・判断します。

## 最初のHard Rule: Google Drive案件作成
画像生成・Claude分析より先に `scripts/create_project_from_intake.py` を実行します。

`.env` の標準 `PROJECTS_ROOT`:
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

案件作成に失敗した場合、Desktop / repo / tmpへ正式画像だけ生成する代替処理は禁止です。

## 標準フロー
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
  Appeal候補比較
  Copy候補比較
  Visual Route候補比較
↓
Codex Direction Approval / Copy確定
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

## 日本語Typography
重要な日本語コピーは画像生成AIへ描かせません。

```text
画像AI
→ 人物・背景・仕事内容・構図・余白

Python
→ Codexが確定した日本語を正確に後載せ
```

標準 `modern_recruit`:
- Headline: 最大視線要素、Bold
- Subcopy: Regularで補助
- Fact: 原則1〜3個のBenefit Chip
- CTA: 独立したアクセント色ボタン
- Bold / Regular / 色 / 余白で情報階層を作る
- 全要素を同じ白角丸Boxにしない

完成時:
```text
05_delivery/
├─ CR001.png
└─ CR001-copy.md
```

`CR001-copy.md` には実際に画像へ載せたheadline/subcopy/fact/CTAを保存します。

## 正式画像保存
`scripts/generate_creative.py` は `--project-id` 必須です。

保存先:
```text
03_batches/CR001/v001/background.png
03_batches/CR001/v001/image-prompt.txt
05_delivery/CR001.png
05_delivery/CR001-copy.md
```

## Pythonの役割
使用:
- `scripts/create_project_from_intake.py`: 案件作成
- `scripts/input_loader.py`: 入力整理
- `scripts/generate_creative.py`: 案件内画像生成 + Typography + copy.md
- `services/image_generator.py`: 画像生成
- `services/overlay_renderer.py`: 日本語Typography

Pythonには次を判断させません。
- Target
- 訴求
- Copy
- Art Direction
- Typography Direction
- Claude承認
- Final QA
- Agent orchestration

## Agent Tuning
品質改善の優先順位:

1. `.claude/agents/creative-director.md`
   - 訴求 / Copy / Visual / Typography / Prompt
2. `.claude/agents/creative-reviewer.md`
   - 低品質PASS防止 / Root Cause
3. `.claude/agents/recruitment-analyst.md`
   - Fact / Evidence / 広告材料
4. `.codex/chief-creative-officer.md`
   - 統括 / 候補選定 / Revision

旧ファイル:
- `production-director.md`
- `copy-director.md`
- `art-director.md`
- `prompt-designer.md`

はHistorical Specialistとして残しますが、Phase 1では直接実行しません。有用な知見はactive Agentへ吸収します。

詳細:
- `.claude/agents/README.md`

## 推測ルール
求人ファイルだけの場合でも、以下は安全なcreative assumptionとして設定できます。
- 人物像
- 求人と矛盾しない一般的服装
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

## 認証
- Codex CCO: ChatGPTログイン
- Claude 3専門家: Claude Codeログイン
- テキストAI用APIキー: 不要
- OpenAI APIを使う場合: 画像生成だけ

## 構造確認
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

## Phase 2以降
Phase 1で実画像品質を確認してから追加します。
- 10〜100枚量産
- 詳細manifest
- 自動修正ループ
- コスト自動管理
- Slack受付
- Cloud常駐処理
- Agent再細分化

**複雑化する前に、Agent tuningで画像品質が上がるかを実画像で検証します。**
