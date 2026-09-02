# Agent Tuning Guide

## Architecture
実働は3 Claude Agent + VSCode Codex CCO。

```text
VSCode Codex CCO
├─ Recruitment Analyst
├─ Creative Director
└─ Creative Reviewer
```

Phase 1 v3では、**Agent数を増やさずDesign SpecとLayout Familyを強くする。**

## Quality Stack
```text
Fact / Hearing / Benchmark
↓
Creative Director
↓
Design Spec
↓
Python Renderer
↓
Creative Reviewer
↓
Codex Final QA
```

## Shared Benchmark Library
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

Codex CCOが最大3件を選ぶ。Pythonはcatalog/contact sheetだけ作る。

## Design Spec
Creative Directorが決める:
- `layout_family`
- `headline.lines`
- `headline.emphasis`
- `text_zone`
- `accent_color`
- `facts`
- `cta`
- `image.prompt`
- `benchmark_refs`

Pythonはこれを正確に描画するだけ。

## Layout Families
`configs/layouts.yaml`

- `numeric_impact`: 数字訴求
- `short_power_word`: 短語訴求
- `concept_message`: コンセプト訴求
- `work_scene`: 仕事内容/写真主体
- `benefit_stack`: 複数メリット
- `emotional_message`: 感情/ミッション訴求

同じ案件の全画像を同じFamilyへ流し込まない。

## Recruitment Analyst
直す症状:
- 別職種/別雇用形態が混入
- 給与/休日/条件がずれる
- 強いFactが見つからない

Copy/Art/Promptは担当しない。

## Creative Director
**最大の品質レバー。**

直す症状:
- コピーが機械的
- 参考サンプルと遠い
- 同じレイアウトばかり
- Headline改行が不自然
- 数字/強調語が目立たない
- 写真と文字が競合
- 仕事内容が伝わらない

## Creative Reviewer
直す症状:
- 読めるだけの画像がPASS
- Design Specと完成画像の差を見逃す
- テンプレ流し込みを見逃す
- benchmark乖離を見逃す

## Codex CCO
直す症状:
- Claude案を鵜呑みにする
- Design Specを承認せず生成へ進む
- 複数画像のLayout Familyが全部同じ
- 局所問題で全Agentを再実行する

## Renderer
`services/overlay_renderer.py`

直す症状:
- Design Specは良いのに描画が弱い
- 文字サイズ/余白/Fact配置が崩れる
- Layout Family間の見た目差が弱い

## Tuning Priority
1. `creative-director.md`
2. `creative-reviewer.md`
3. `configs/layouts.yaml`
4. `services/overlay_renderer.py`
5. `recruitment-analyst.md`
6. `.codex/chief-creative-officer.md`
7. Image Backend

## Token Efficiency
- `creative-context.json` を一次入力
- raw sourceはFact疑義だけ
- Agent返答はcompact JSON
- benchmark最大3
- route最大2
- Fact最大3
- Design SpecをRenderer/Reviewerで再利用
- Revisionはroot cause工程だけ

## Good Tuning Rule
悪い:
- プロっぽくする

良い:
- Headlineは意味単位の改行をDesign Specで指定する
- `numeric_impact` では数字が最初の視線要素になる
- 3秒で仕事内容が分からなければREVISION
- 同案件4枚が全て同じLayout Familyなら意図を再確認する
- Design Spec通り描画されない場合はAgentではなくPython Rendererへ戻す

## Feedback Loop
```text
実画像FB
↓
Fact / Strategy / Design Spec / Renderer / Image Backend のどこが原因か特定
↓
局所修正
↓
再発するなら一般ルール化
```

1案件固有の事情を全案件の絶対ルールにしない。
