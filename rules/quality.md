# Quality Rules

## 品質の定義
Phase 1の品質は「見た目が良い」だけではない。

以下が一貫していることを重視する。
```text
求人ファイル
↓
求人事実
↓
Creative Direction / Copy
↓
完成画像 + *-copy.md
```

ヒアリングシートや補足テキストがある場合は追加要望として使うが、無いこと自体を品質不足とはしない。

## 入力品質ルール
- 求人ファイル: 必須
- ヒアリングシート: 任意
- 補足テキスト: 任意
- 求人ファイルが正常に読める限り、求人ファイルだけでも生成する
- ヒアリング不足だけで制作を停止しない

## 3段階の確認
### 1. Codex Fact Check
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

### 2. Codex Direction Approval
Creative Directorの戦略・コピー・Art・Prompt・Overlay Textをまとめて確認する。

確認:
- ターゲットに求人内容上の根拠がある
- 1画像1メッセージになっている
- コピーの主張を求人事実へ遡れる
- コピーとビジュアルが同じ訴求を強化する
- headlineが必ず確定している
- 日本語重要コピーを画像生成AIへ直接描かせない
- creative assumptionが人物/構図/背景/トーン等の演出に限定されている

### 3. Codex Final QA
Creative Reviewerの診断を参考に、Codex CCOが完成画像と `*-copy.md` を直接確認する。

確認:
- 求人事実との一致
- あればヒアリング/補足テキストとの一致
- ターゲット適合
- 訴求力
- コピー品質
- 日本語テキストの正確性
- 画像内文言と `*-copy.md` の一致
- 視認性
- 構図
- ブランド適合
- 画像破綻
- 媒体規格

## 日本語テキスト品質
重要な求人コピーは画像生成AIに描かせず、Pythonで後載せする。

必須:
- headlineは必ず画像内に存在
- subcopy/fact/CTAは採用したものだけ表示
- 誤字脱字なし
- 数字・単位・記号を改変しない
- 文字切れなし
- 不自然な改行で意味を変えない
- 背景と十分なコントラストを確保
- 小さすぎて読めない文字をPASSしない
- 完成画像と同時に `*-copy.md` を保存

`*-copy.md` は画像内へ後載せした元文字列をそのまま保持する。

## 重大エラー
以下が1件でもあればPASSしない。
- 給与・手当・時間・休日・勤務地・応募条件の改変
- 求人原稿にない保証表現
- 根拠不明のNo.1・最短・必ず等
- 必須コピーの誤字・文字欠け・判読不能
- `*-copy.md` と画像内コピーの不一致
- 禁止表現の使用
- 明確な画像破綻
- 指定サイズ・媒体規格の重大違反

## 求人ファイルだけの案件
以下は安全なcreative assumptionとして許可する。
- 人物像
- 服装
- 背景
- 構図
- 色/トーン
- カメラ距離

以下は推測禁止。
- 給与
- 待遇
- 休日
- 勤務時間
- 資格
- 経験年数
- 数値実績
- No.1/最短/保証等

## Claude Reviewerの位置づけ
Reviewerは最終承認者ではない。

```text
Creative Reviewer
↓
完成画像 + copy.md の診断
↓
Codex CCO
↓
最終判断
```

ReviewerがPASSでもCodexがNGなら修正する。

## 修正原則
- 原因に最も近い工程だけを修正する。
- 事実問題 → Recruitment Analystまたは入力確認
- 戦略/コピー/Art/Prompt問題 → Creative Director
- 生成破綻 → 画像生成
- 誤字/文字切れ/可読性 → text_overlay
- 原則3回で解消しない場合は人間へ確認する。

## Phase 1の候補数
複雑なAgent競争は行わない。

最低限:
- Copy Candidates: 3案
- Art Direction: Creative Directorが最も強い1方向を提示
- 必要ならCodexが追加案を要求

品質上の理由がある場合だけ候補を増やす。

## 認証
- Codex: ChatGPTログイン
- Claude: Claude Codeログイン
- テキストAI用APIキーを要求しない
- OpenAI APIを使用する場合は画像生成だけ

## コスト
Phase 1ではローカル画像AIの詳細コスト管理やUsage Trackerを品質Gateにしない。

OpenAI Image APIを使用する場合は、人間が定めた1枚あたり予算内で運用する。複雑な自動Budget GuardはPhase 2で再検討する。

## Phase 1でやらないこと
- 4段階以上の細分化Gate
- Schemaを通すこと自体を目的にしたQA
- Reviewer点数だけの自動PASS
- 100枚量産前提の状態管理
- ローカルAI基盤の安定化をクリエイティブ品質検証より優先すること
