# Creative Benchmark System

最高品質を「AIが綺麗だと思う画像」ではなく、人間の優秀なクリエイティブ責任者が承認する品質へ近づけるための評価基盤。

## 実画像の保存場所
実案件や社内クリエイティブはGitHubへ置かない。`.env` の `KNOWLEDGE_ROOT` で指定するGoogle Drive等の共有領域へ保存する。

推奨構造:

```text
KNOWLEDGE_ROOT/
├─ golden_creatives/
│  ├─ GC-0001/
│  │  ├─ image.png
│  │  └─ benchmark.json
├─ rejected_creatives/
│  ├─ RC-0001/
│  │  ├─ image.png
│  │  └─ benchmark.json
├─ brand_rules/
└─ media_rules/
```

`benchmark.json` は `schemas/benchmark-entry.schema.json` に準拠する。

## Goldenにする条件
- 人間が明確に良いと判断したもの
- 可能なら実績データ（CTR/CVR/応募等）があるもの
- なぜ良いかを文章化できるもの
- 他案件にも再利用可能な原則を抽出できるもの

## Rejectedにする条件
- 見た目は良いが訴求が弱い
- 原稿事実と矛盾した
- 読みにくい
- ターゲットがズレた
- 情報過多
- ブランド不一致
- AIらしい破綻がある

単に「好きではない」だけの画像はBenchmarkにしない。

## 将来利用
Recruitment/Strategy/Copy/Art/Reviewer/Codex Gateへ案件条件に近いBenchmarkだけを検索して渡す。全画像を毎回コンテキストへ入れない。
