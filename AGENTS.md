# AGENTS.md

## 指揮系統の固定原則（2026-09-07 ユーザー再確認）
**このプロジェクトの最高責任者はCodex CCO。正式なClaude Agent全11役割とCodex Integrated Creative Designerは、Codex CCOの指揮下で作業する。**

- Codex CCO自身がユーザー依頼・求人Fact・ヒアリング・案件の進捗と成果物を理解し、作業方針を決める。
- Codex CCOが必要なClaude Agentを選び、入力・担当範囲・出力先・成果物・合格条件を示して作業を指示する。
- 各Claude Agentは専門作業の成果物・根拠・未解決点をCodex CCOへ提出する。Codex CCOが各成果物をレビューし、採用または修正を判断する。
- 修正時はCodex CCOが原因と担当Agentを特定し、修正内容・保持すべき承認済み要素・再確認条件を指示する。再提出物もCodex CCOがレビューする。
- Creative Directorの戦略統合、Production Directorの進行管理、各Directorの選定・差し戻し案は専門業務であり、案件全体の指揮・最終裁定はCodex CCOが担う。
- Codex CCOが選んだ制作担当から独立したReviewerの検証を受け、CCOが最終目視確認・正式納品承認を行う。画像レビューの標準担当はCodex Independent Creative Reviewer。未解消のReviewer failを承認で上書きしない。Human Final Approvalは残す。

Agent定義の追加・置き換えや実行方式の変更でも、この指揮系統を変更しない。個別定義の「統括」「裁定」「差し戻し」は、この共通契約の担当範囲内で解釈する。

## 匿名化した求人条件・コピーのClaude共有（2026-09-07 ユーザー明示許可）
このプロジェクトでは、匿名化した求人条件・コピーをClaudeへ送信することをユーザーが継続的に許可している。送信ごとのユーザー再承認は求めない。
共有の必要性、匿名化、送信する求人条件・コピーの範囲、専門Agentへの実行指示は、最高責任者のCodex CCOが判断する。Claudeに共有可否の承認を求める運用にはしない。
Claudeの専門レビュー結果を受け取った後も、成果物の採否・修正・正式納品の承認はCodex CCOが担う。この許可は実行環境の権限制御を変更する設定ではなく、対象の処理を申請する際のユーザー許可の根拠とする。

## レビュー担当と最終承認（2026-09-07 ユーザー指示）
Claudeの承認を必須条件にする運用は廃止し、レビュー担当の選択と最終承認をCodex CCOが担う。画像は原則として [Codex Independent Creative Reviewer](.codex/agents/independent-creative-reviewer.md) が制作担当から独立して実画像を検査する。ClaudeはCCOが必要と判断した専門分析・助言・レビューを担当する。
Fact・Exact Text・意向適合・素材整合・広告品質の検証とCCO自身の目視は必須。Reviewerの実際の担当と結果を記録し、Codexが行った検証をClaude実施済みとして記録しない。共有が許可されていない画像を別経路でClaudeへ送ることはしない。

## 正式Agent定義（2026-09-07）
ユーザー指定の `jobole-agents-set.zip` の11件を `.claude/agents/` の正式版として採用。同名の旧定義は置き換え済み。
一覧・役割の区別・既存実行フローとの接続状況は [.claude/agents/README.md](.claude/agents/README.md) を参照する。
以下のv5実行契約は既存経路の仕様。添付版の出力を使う場合はschemaとCreative Spec・承認JSONの整合が必要であり、定義の配置だけで自動フローの移行済みとは扱わない。

## Goal
求人ファイルだけでも、**Project → Fact → Benchmark → Adobe素材選定 → Creative Spec → Codex ImageGen完成広告 → Review → Formal Delivery**まで進める。

標準は `codex_imagegen`。
画像実制作はCodex Integrated Creative Designerが担う。

## Active Team
以下は既存v5経路の基本構成。正式なClaude Agent全11役割のうち、案件に必要な専門AgentをCodex CCOが選んで指示する。

```text
Codex CCO
├─ Claude Recruitment Analyst
├─ Claude Creative Director
├─ Codex Integrated Creative Designer + ImageGen
└─ Codex Independent Creative Reviewer（CCOが担当を選択）
```

## User Intake
必須:
- 求人ファイル

任意:
- ヒアリングシート
- 補足テキスト

## Source Priority
1. 求人ファイル = Fact正本
2. ヒアリング = 希望/媒体/枚数/NG/テイスト
3. 補足テキスト
4. `ORIGINAL_IMAGE_ROOT` = design benchmark

## Adobe Material First（2026-09-07）
制作素材は `ADOBE_IMAGE_ROOT` を優先する。既定値は
`G:\共有ドライブ\ジョブオレチーム\ジョブオレチーム\JOBOLE-Image-Creator-Team\Adobe\_image`。
ユーザーがAdobeからダウンロードした制作利用可能な画像であり、案件ごとの利用許可の再確認は不要。
各Creativeで一覧と候補原本を目視し、職種・服装・業務・構図・解像度・ヒアリングに合う画像があれば実素材として使用する。
適した画像がない場合だけ、理由を残して従来の人物からのImageGen生成へ進む。
未検索・ファイル名の検索不一致・共有ドライブ接続不可を「使える画像なし」と扱わない。
`creative_spec.asset_source` に選定結果を保持する。詳細・形式は [Adobe素材優先フロー](docs/adobe-material-first.md)。

## Project First
最初に案件を作る。
正式成果物をrepo/tmp/Desktopへ代替保存しない。

## Compact Context First
`creative-context.json` をAgent間の一次入力とし、raw sourceはFact疑義だけ読む。

## Codex ImageGen Production Rule
標準実制作:
`.codex/agents/integrated-creative-designer.md`

Skill:
`.codex/skills/recruitment-imagegen/SKILL.md`

制作対象:
- 人物
- 背景
- 装飾
- 日本語コピー
- Typography
- レイアウト

Adobe素材採用時は原本をImageGenへ入力し、人物・写真を保持してこれらを一体の完成広告として制作する。
人物からの新規生成はAdobe素材の適合なしを確認した場合のみ。

### 禁止
- Pythonを標準画像生成者にする
- Python後載せ前提でPremiumデザインを作る
- ImageGen unavailable時に自動でDirect APIへ切り替える
- Creative Specの文字を勝手に変更
- benchmark無視
- 同案件の全画像を同一テンプレへ流し込む

## ImageGen Capability Gate
CCOが制作直前に利用可否を確認。

利用不可なら:
`IMAGEGEN_CAPABILITY_UNAVAILABLE`

その時点で停止。
Safe Pythonまたは明示API fallbackはCCO/ユーザー判断。

## Creative Spec
正本:
`02_direction/<creative-id>-creative-spec.json`

必須:
- mode `codex_integrated`
- `text_contract`
- `asset_source`（Adobe選定結果・使用パス、または適合素材なしの理由）
- benchmark refs
- integrated design direction
- `execution.generation_owner=codex_integrated_creative_designer`
- `execution.generation_capability=codex_imagegen`

## Candidate
Integrated Creative DesignerがImageGenで:

`03_batches/<creative-id>/<version>/candidate.png`

へ保存。

その後のみ:

```powershell
python scripts/register_codex_candidate.py --project-id <PJ-XXXX> --creative-id <CR001> --version <v001>
```

Python registrationは生成/再デザイン禁止。

## Text Integrity
4層:
1. Codex Designer self-check
2. Local OCR optional
3. Independent Reviewer visual readback（標準Codex、担当はCCOが選択）
4. Codex CCO final visual check

required text / critical numbersの確認エラーはBlock。

## Review Standard
- Fact
- Hearing
- Benchmark
- Exact text
- Ad impact
- Typography
- Job reality
- Adobe原本との人物・写真の一致、または生成へ進んだ理由
- Generation artifact
- Multi-creative diversity

「読める」だけではPASSしない。
一流求人広告benchmarkと並べて納品可能かで判断。

## Revision
以下は修正先の基本分類。Codex CCOが原因を判断し、必要に応じて正式な専門Agentへ具体的な修正指示を出す。

- Fact -> Recruitment Analyst
- Strategy/Copy/Art concept -> Creative Director
- 画像局所不具合 -> Codex Designer edit
- 画像全体弱い -> Codex Designer regenerate
- 文字誤り -> Codex Designer text fix
- Safe renderer defect -> Python Safe renderer

局所問題では全Agentをやり直さない。

## Fallback
### safe_python
exact text安定性が必要な場合だけ。

### api_fallback
標準では無効。
ユーザー明示承認が必要。
`API_FALLBACK_ENABLED=false` のまま勝手に使わない。

## Formal Delivery
Candidateは正式納品ではない。
独立Reviewerの検証結果をCodex CCOが確認し、CCOの正式納品承認JSONを保存した後に `scripts/promote_creative.py` で `05_delivery` へ昇格。`creative_reviewer_pass` は実際の担当（CodexまたはClaude）による品質検証結果であり、Claude承認の必須条件ではない。承認JSONには `reviewer_provider` と `reviewer_report` も記録する。
Codex CCOが案件の `05_delivery` への保存まで確認する。画像は1枚ずつ独立したファイルとし、一覧画像だけで納品完了にしない。
`05_delivery` は完成画像のみ。コピー文・承認JSON・生成記録は `04_project_review/delivery_records/<creative-id>/<version>/` に保存し、説明文・ステータス等の管理ファイルも `04_project_review` 配下へ置く。

Human Final Approvalは常に残す。
