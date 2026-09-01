# Quality Rules

## 品質の定義
Phase 1の品質は「見た目が良い」だけではない。

以下が一貫していることを重視する。
```text
Original Request
↓
求人事実
↓
Creative Direction
↓
完成画像
```

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
Creative Directorの戦略・コピー・Art・Promptをまとめて確認する。

確認:
- ターゲットに根拠がある
- 1画像1メッセージになっている
- コピーの主張を求人事実へ遡れる
- コピーとビジュアルが同じ訴求を強化する
- 重要な日本語コピーを画像生成AI任せにしていない
- ブランド・参考方向性と矛盾しない

### 3. Codex Final QA
Creative Reviewerの診断を参考に、Codex CCOが最終画像を直接確認する。

確認:
- Original Requestとの一致
- 求人事実との一致
- ターゲット適合
- 訴求力
- コピー品質
- 視認性
- 構図
- ブランド適合
- 画像破綻
- 媒体規格

## 重大エラー
以下が1件でもあればPASSしない。
- 給与・手当・時間・休日・勤務地・応募条件の改変
- 求人原稿にない保証表現
- 根拠不明のNo.1・最短・必ず等
- 必須コピーの誤字・文字欠け・判読不能
- 禁止表現の使用
- 明確な画像破綻
- 指定サイズ・媒体規格の重大違反

## Claude Reviewerの位置づけ
Reviewerは最終承認者ではない。

```text
Creative Reviewer
↓
診断・問題抽出
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
- 生成破綻/技術問題 → 画像生成
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
