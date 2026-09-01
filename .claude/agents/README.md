# Agent Tuning Guide

## このフォルダの目的
このプロジェクトでは、画像品質を上げるためにAgent数を増やすのではなく、**active Agentの判断基準を継続的に改善する**。

実働は3Agentだけ。

```text
VSCode Codex CCO
├─ Recruitment Analyst
├─ Creative Director
└─ Creative Reviewer
```

最高責任者は `.codex/chief-creative-officer.md`。

## Active Agents

### `recruitment-analyst.md`
担当:
- 求人Fact抽出
- Evidence
- Advertising Leverage
- Claim Risk
- Job Reality

ここを調整すると改善しやすいもの:
- 求人理解の正確性
- 強い訴求材料の発見
- 誇張/誤認の防止
- Creative Directorへ渡す材料品質

ここには書かないもの:
- Headline案
- デザイン案
- Image Prompt

### `creative-director.md`
担当:
- Target hypothesis
- 訴求戦略
- Copy
- Art Direction
- Typography
- Image Prompt

**画像品質への影響が最も大きいAgent。**

ここを調整すると改善しやすいもの:
- コピーが機械的
- 条件羅列になる
- 写真が求人内容と噛み合わない
- 人物が不自然
- 構図が弱い
- 文字デザインが単調
- Promptの再現性が低い

品質改善では原則ここを最初に見る。

### `creative-reviewer.md`
担当:
- Fact Review
- Advertising Impact
- Copy Review
- Job Reality Review
- Typography Review
- Image Generation Artifact Review
- Root Cause Routing

ここを調整すると改善しやすいもの:
- 微妙な画像がPASSしてしまう
- 同じ失敗が繰り返される
- Typographyの弱さを見逃す
- 生成破綻を見逃す
- 差し戻し先が曖昧

ReviewerはCreatorより厳しく設定する。

## CCO
### `.codex/chief-creative-officer.md`
担当:
- Agent統括
- 案件保存
- Fact Gate
- 候補比較
- Creative Direction Approval
- Revision Routing
- Final QA

ここを調整すると改善しやすいもの:
- ClaudeのRecommendedをそのまま採用してしまう
- 候補比較が弱い
- 修正ループが雑
- 保存先がずれる
- Agent間の責任範囲が崩れる

## Historical Specialist Files
以下は過去の分業構成の専門ファイル。

- `production-director.md`
- `copy-director.md`
- `art-director.md`
- `prompt-designer.md`
- その他旧agentファイル

Phase 1では直接実行しない。

有用な知見はactive `creative-director.md` へ吸収済み。今後も旧ファイルを直接active化するより、必要な判断基準をCreative Directorへ統合することを優先する。

## Tuning Priority
画像が弱かった場合、次の順で原因を切り分ける。

### 1. 求人Factが間違っている/弱いFactしか出ていない
→ `recruitment-analyst.md`

### 2. 訴求・コピー・写真・Typographyが弱い
→ `creative-director.md`

### 3. 低品質なのにPASSした
→ `creative-reviewer.md`

### 4. 正しい差し戻しができない/Agent出力を鵜呑みにする
→ `.codex/chief-creative-officer.md`

### 5. 日本語の描画そのものが崩れる
→ `services/overlay_renderer.py`

### 6. 人物・手・背景の生成そのものが弱い
→ Image backend / Image Prompt / `services/image_generator.py`

## Good Tuning Rule
Agentファイルへ新ルールを追加するときは、抽象的な「高品質にする」ではなく、**観察可能な判断基準**を書く。

悪い例:
- 魅力的な画像にする
- プロっぽくする

良い例:
- Headlineは1〜2秒で主訴求が理解できる
- Fact badgeは原則1〜3個
- 全テキストを同じ白角丸Boxへ入れない
- 3秒で仕事内容と主メリットの両方が理解できない場合はREVISION
- 倉庫求人では仕事内容が視覚的に分かる作業物を最低1つ含める

## Tuning by Feedback
人間から画像FBを受けたら、単発の画像だけ直さず、再発する問題ならAgent定義へ一般化する。

例:
```text
FB:
テキストが機械的

単発修正:
フォントを変更

Agent改善:
- Headline/Subcopy/Fact/CTAの情報階層ルール追加
- Mechanical Design SignsをReviewerへ追加
- Creative DirectorにTypography Playbook追加
```

## Do Not Overfit
1案件だけの固有事情を全案件の絶対ルールへしない。

分類:
- 全案件に効く → Agent定義
- 特定ブランドに効く → brand rule / knowledge
- 特定案件だけ → project direction

## Phase 1 Fixed Architecture
```text
Human
↓
VSCode Codex CCO
↓
Recruitment Analyst
↓
Codex Fact Check
↓
Creative Director
↓
Codex Direction Approval
↓
Python / Image Generation / Typography
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```

Agent数を増やす前に、この構成で実画像の品質改善を回す。
