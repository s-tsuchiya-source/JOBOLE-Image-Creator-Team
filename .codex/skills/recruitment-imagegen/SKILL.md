# Recruitment ImageGen Skill

## Purpose
CodexがJOBOLE求人広告をImageGen capabilityで直接制作するためのプロジェクト内Skill定義。

## Use When
- `CREATIVE_RENDER_MODE=codex_imagegen`
- CCOがCreative Specを承認済み
- Integrated Creative Designerが実制作を担当するとき

## Do Not Use For
- 求人Fact分析
- Creative Specの勝手な変更
- OCRだけの確認
- Safe Python fallback

## Required Inputs
- `creative-context.json`
- Recruitment Analyst JSON
- approved `creative-spec.json`
- benchmark refs 最大3
- resolved output size

## ImageGen Instruction Pattern
ImageGenへ渡す指示は、Creative Specの `image.prompt` と `text_contract` を正本にする。

必ず含める:
1. 完成した日本語求人広告であること
2. exact canvas ratio / size
3. 人物・仕事・背景の具体的なリアリティ
4. benchmarkから借りる視覚文法
5. Typographyの役割・大きさ・強弱・配置
6. required text contractの全文
7. 余計な読める文字を追加しないこと
8. fake logo / watermark / random signage禁止
9. 納品可能なpolishを要求

## Exact Text Rule
required textは意味が同じでも言い換え禁止。
数字、通貨、単位、職種、雇用形態、駅名は完全一致を要求する。

改行だけはCreative Specで許可されている場合に限り視覚上変更可。

## Composition Rule
写真と文字を別レイヤーとして考えず、最初から一枚の広告として統合する。

推奨:
- 人物の視線とHeadlineの方向を合わせる
- Headlineを最大視線要素にする
- Supporting textは2段階以下
- Accent colorは原則1色を主役
- 装飾はコピーの意味を補強
- 写真を完全に隠す大面積Boxを乱用しない

禁止:
- 左側テキスト・右側人物の固定テンプレを全案件へ適用
- 全要素角丸Chip
- 均一フォントサイズ
- 余白のない条件羅列
- generic corporate stock poster

## Generation / Edit Loop
最大2回を原則とする。

1回目: 完成広告を生成。
2回目: 明確な文字/局所品質不具合があればeditを優先。editで直せない場合のみ再生成。

同じrequired text誤りが続いたらCCOへ戻す。無限生成しない。

## Saving
ImageGen出力は必ず案件配下へ保存:
`03_batches/<creative-id>/<version>/candidate.png`

ImageGenが一時パスを返した場合はCodexが正式パスへコピーしてから登録する。

## Registration
保存後:
`python scripts/register_codex_candidate.py --project-id <PJ-XXXX> --creative-id <CR001> --version <v001>`

この登録は生成ではなく、サイズ/Spec/OCR/metadataの機械的検品だけを行う。

## Failure
ImageGen capability自体が使えない場合:
- Python APIへ勝手にfallbackしない
- `IMAGEGEN_CAPABILITY_UNAVAILABLE` としてCCOへ返す
- ユーザーが明示許可した場合だけ `api_fallback` を選択可能
