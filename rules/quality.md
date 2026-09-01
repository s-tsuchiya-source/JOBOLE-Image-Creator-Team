# Quality Rules

## 品質の定義
本システムにおける品質は「見た目が良いこと」だけではない。Original Request、求人事実、ヒアリング要望、制作戦略、コピー、Art Direction、完成画像が一貫していることを最重要とする。

## Quality Gate原則
1. Recruitment Analysis後にCodex Fact Gateを通す。
2. Production Strategy後にCodex Strategy Gateを通す。
3. Copy / Art Direction後にCodex Direction Gateを通す。
4. Creative Reviewer後にCodex Final Traceability Gateを通す。
5. Gate未通過の成果物を次工程へ渡さない。

## Traceability QA
最終画像の各主張は上流へ遡れる必要がある。

```text
Generated Image
  ↓
Approved Copy / Art Direction
  ↓
Creative Strategy
  ↓
Recruitment Analysis
  ↓
Original Job Posting / Hearing
```

### 重大エラー
- 給与・手当・勤務時間・休日・勤務地・応募条件の改変
- 求人原稿にない保証表現
- 根拠不明のNo.1・最短・必ず等の表現
- 必須コピーの誤字・文字欠け・判読不能
- 指定サイズ・媒体規格違反
- ヒアリングで禁止された表現の使用

重大エラーが1件でもあれば点数に関係なくPASSしない。

## 必須確認項目
- 伝えたい内容が一目で分かる
- ターゲットに適した訴求になっている
- コピーが読みやすい
- コピーの根拠を求人事実へトレースできる
- ブランドカラーやトーンが崩れていない
- 誤字脱字がない
- 画像の破綻がない
- 媒体規格に沿っている
- CopyとArtが同じ訴求を強化している
- Original Requestと最終画像が一致している

## コンペ原則
最高品質モードでは1案を直接採用しない。
- Strategy: 原則5候補以上
- Copy: 原則3候補以上
- Art: 原則2候補以上
- Codexが比較・選抜した後に次工程へ進む

## 修正原則
- 問題を `fact_error / strategy_error / copy_error / art_error / prompt_error / generation_error / review_error / format_error / brand_error / missing_information` に分類する。
- 原因を作ったAgentまで差し戻す。
- 同一Creativeの自動修正は原則3回まで。
- 3回で解決しない場合は `needs_human_review` とする。

## コストガード
- 最終画像1枚あたりの目標上限: 400円
- 350円到達でwarning
- 450円見込みで自動継続せず人間へエスカレーション

## NG例
- 根拠不明のNo.1表現
- 確証のない数値訴求
- 競合他社ロゴや名称の無断使用
- 読めないほど小さい文字
- AIが勝手に補った給与・待遇
- Reviewerの点数だけを根拠にCodex Gateを省略すること
