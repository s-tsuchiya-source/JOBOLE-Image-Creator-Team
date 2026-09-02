# Agent Tuning Guide

## Architecture
実働は3 Claude Agent + VSCode Codex CCOだけ。

```text
VSCode Codex CCO
├─ Recruitment Analyst
├─ Creative Director
└─ Creative Reviewer
```

最高責任者: `.codex/chief-creative-officer.md`

Agent数を増やす前に、**benchmark / hearing / active Agent定義**を改善する。

## Shared Benchmark Library
正式な制作参考:

```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

`.env`:
```env
ORIGINAL_IMAGE_ROOT=G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
REFERENCE_SHORTLIST_MAX=3
```

Pythonは画像を評価しない。
`scripts/prepare_creative_context.py` が行うのは:
- reference catalog
- contact sheet
- 任意 `_index.csv` metadataによる候補補助

最終benchmark選定はCodex CCO。
Creative Directorへ渡すのは最大3件。

## Token Efficiency
品質を落とさず、次を固定する。

- `creative-context.json` を一次入力にする
- raw CSVはFact疑義の確認時だけ読む
- Agent返答はcompact JSON
- Visual Routeは通常2案
- benchmarkは最大3件
- Fact chipは最大3件
- Revisionはroot cause工程だけ
- 同じCSV全文を3Agentへ繰り返し渡さない

## Recruitment Analyst
ファイル: `recruitment-analyst.md`

担当:
- exact role / employment type
- Fact / Evidence
- Advertising Leverage
- Claim Boundary
- Job Reality
- hearingとFactの分離

ここを直す症状:
- 別職種が勝手に入る
- 正社員求人にアルバイト表現が入る
- 給与/休日/条件がずれる
- 強いFactをCreative Directorへ渡せない

ここにはCopy/Art/Promptを書かない。

## Creative Director
ファイル: `creative-director.md`

**画像品質への最大レバー。**

担当:
- hearing alignment
- benchmark translation
- message strategy
- Copy
- Visual Route
- Art Direction
- Typography Direction
- Image Prompt

ここを直す症状:
- 参考サンプルと全く違う
- 人物写真benchmarkなのに抽象イラストになる
- コピーが機械的
- 条件羅列になる
- タイポがUIのようになる
- 仕事内容が写真から分からない

## Creative Reviewer
ファイル: `creative-reviewer.md`

担当:
- Fact/Hearing/Benchmark blocker
- 1-second / 3-second test
- Copy
- Typography
- Job Reality
- Generation Artifact
- Root Cause Routing

ここを直す症状:
- 納品不可レベルがPASSする
- benchmark乖離を見逃す
- 媒体比率違反を見逃す
- 「読めるだけ」の画像をPASSする

ReviewerはCreatorより厳しくする。

## Codex CCO
ファイル: `.codex/chief-creative-officer.md`

担当:
- Project作成
- compact context gate
- Fact Gate
- benchmark選定
- hearing/media alignment
- Direction Gate
- root-cause revision
- Final QA

ここを直す症状:
- Claude案を鵜呑みにする
- benchmarkを見ずに進める
- raw CSVを毎回渡してトークンを浪費する
- Typography問題で全Agentを再実行する

## Renderer / Backend
Agentだけで解決しない症状:

### 日本語は正しいがデザインが機械的
`services/overlay_renderer.py`
- `benchmark_recruit`
- `modern_recruit`

### 人物/手/背景の生成品質そのものが低い
- Image Prompt
- image backend
- `services/image_generator.py`

## Good Tuning Rule
抽象ルールではなく、観察可能な基準を書く。

悪い:
- プロっぽくする

良い:
- 1秒で主訴求が理解できない場合はREVISION
- hearingの媒体比率と違えばblocker
- benchmarkが人物写真主体なら、理由のない抽象イラスト化はblocker
- 求人1職種に別職種を追加したらblocker
- 全テキスト同一白BoxならREVISION

## Feedback Loop
人間FBは次の順で一般化する。

```text
実画像FB
↓
原因工程を特定
↓
単発案件だけの問題か判定
↓
再発するならAgent/Rendererへ一般ルール化
↓
次案件で再確認
```

1案件固有の内容を全案件の絶対ルールにしない。

## Fixed Workflow
```text
Human
↓
Codex CCO
↓
Project creation
↓
Python compact context + original_image catalog/contact sheet
↓
Recruitment Analyst
↓
Codex Fact Gate
↓
Codex Benchmark Gate
↓
Creative Director
↓
Codex Direction Gate
↓
Image Generation + deterministic Japanese Typography
↓
Creative Reviewer
↓
Codex Final QA
↓
Human Final Approval
```
