# Quality Rules

## 品質の定義
Phase 1の品質は「見た目が良い」だけではない。

```text
求人ファイル
↓
求人事実
↓
Creative Direction / Copy / Typography
↓
案件内の完成画像 + *-copy.md
```

ヒアリングシートや補足テキストがある場合は追加要望として使うが、無いこと自体を品質不足とはしない。

# 保存品質も必須
正式制作では、クリエイティブ品質と同じく保存先も検証対象とする。

必須:
- `.env` の `PROJECTS_ROOT` 配下に案件フォルダがある
- `project.yaml` がある
- 画像生成より前に案件フォルダが作成されている
- 生背景/Promptは `03_batches/` に保存
- 完成画像/copy.mdは `05_delivery/` に保存

案件フォルダが無い状態でDesktop / repo / tmpへ生成した画像は正式成果物としてPASSしない。

# 入力品質ルール
- 求人ファイル: 必須
- ヒアリングシート: 任意
- 補足テキスト: 任意
- 求人ファイルが正常に読める限り、求人ファイルだけでも生成する
- ヒアリング不足だけで制作を停止しない

# 3段階の確認
## 1. Codex Fact Check
Recruitment AnalystのFact Sheetを元求人と照合する。

重大確認項目:
- 給与
- 勤務地
- 雇用形態
- 仕事内容
- 応募条件
- 勤務時間
- 休日
- 福利厚生
- 数値表現

## 2. Codex Direction Approval
Creative Directorの戦略・コピー・Art・Prompt・Overlay Text・Typographyをまとめて確認する。

確認:
- ターゲットに求人内容上の根拠がある
- 1画像1メッセージ
- コピーの主張を求人事実へ遡れる
- Headlineが必ず確定
- Headline / Subcopy / Factの役割が重複していない
- 条件や職種名をただ羅列するだけで終わっていない
- 求職者メリットが一瞬で理解できる
- 日本語重要コピーを画像生成AIへ直接描かせない
- creative assumptionが人物/構図/背景/トーン等の演出に限定されている

## 3. Codex Final QA
Creative Reviewerの診断を参考に、Codex CCOが完成画像と `*-copy.md` を直接確認する。

確認:
- 求人事実との一致
- あればヒアリング/補足テキストとの一致
- 案件フォルダ内に保存されている
- ターゲット適合
- メリット訴求の明確性
- コピー品質
- 日本語テキストの正確性
- 画像内文言と `*-copy.md` の一致
- Typographyの情報階層
- 視認性
- 構図
- ブランド適合
- 画像破綻
- 媒体規格

# Typography品質
重要な求人コピーは画像生成AIに描かせずPythonで後載せする。

標準 `modern_recruit` の情報階層:
- Headline: 最大の視線要素。大きな太字 + アクセント
- Subcopy: Headlineを補強する軽い情報
- Fact: 1〜3個の短いメリットチップ/バッジ
- CTA: Factとは明確に違うアクセント色ボタン

必須:
- 全テキストを同じ白い角丸ボックスへ入れない
- Headline / Fact / CTAのサイズ・太さ・色・形に役割差がある
- Headlineはスマホ縮小でも主メッセージが分かる
- 文字切れなし
- 不自然な改行なし
- 背景と十分なコントラスト
- 文字が多すぎない
- 完成画像と同時に `*-copy.md` 保存

# 重大エラー
以下が1件でもあればPASSしない。
- 給与・手当・時間・休日・勤務地・応募条件の改変
- 求人原稿にない保証表現
- 根拠不明のNo.1・最短・必ず等
- 必須コピーの誤字・文字欠け・判読不能
- `*-copy.md` と画像内コピーの不一致
- 案件フォルダ外への正式成果物保存
- 全テキストが同じ見た目で情報階層が実質ない
- CTAが通常テキストと区別できない
- 禁止表現の使用
- 明確な画像破綻
- 指定サイズ・媒体規格の重大違反

# 求人ファイルだけの案件
安全なcreative assumptionとして許可:
- 人物像
- 服装
- 背景
- 構図
- 色/トーン
- カメラ距離

推測禁止:
- 給与
- 待遇
- 休日
- 勤務時間
- 資格
- 経験年数
- 数値実績
- No.1/最短/保証等

# 修正原則
- 保存先問題 → project/intake処理
- 事実問題 → Recruitment Analystまたは入力確認
- 戦略/コピー/Art/Typography/Prompt問題 → Creative Director
- 生成破綻 → image_generation
- 誤字/文字切れ → text_overlay
- 原則3回で解消しない場合はHuman Review

# Phase 1の候補数
最低限:
- Copy Candidates: 3案
- Art Direction: 最も強い1方向
- Typography: その方向に合う1設計
- 必要な場合だけCodexが追加案を要求

# 認証
- Codex: ChatGPTログイン
- Claude: Claude Codeログイン
- テキストAI用APIキーを要求しない
- OpenAI API使用時は画像生成だけ

# Phase 1でやらないこと
- 4段階以上の細分化Gate
- Schemaを通すこと自体を目的にしたQA
- Reviewer点数だけの自動PASS
- 100枚量産前提の状態管理
- ローカルAI基盤安定化をクリエイティブ品質検証より優先すること
