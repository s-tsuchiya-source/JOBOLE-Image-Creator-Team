# Review Workflow

## 目的と責任者
完成画像を、制作担当から独立したReviewer（標準Codex）とCodex CCOの最終目視で検証する。レビュー担当の選択と最終承認はCCOが担い、Claude承認を必須条件にしない。
Codex CCOがレビューを指示し、レビュー成果物の内容・根拠も確認して、修正指示と正式納品承認を行う。共通契約は [AGENTS.md](../AGENTS.md)。

匿名化した求人条件・コピーをClaudeへ送信する判断は、ユーザーの継続許可に基づきCodex CCOが担う。送信ごとのユーザー再承認は不要。Claudeから受け取るのは検証結果であり、成果物採用・正式納品の最終承認者はCCO。

## 専門役割
- Creative Reviewer: デザイン品質・素材整合・修正用の編集指示案。
- Reviewer: 素材同一性・コピー正確性・クライアント意向適合などの最終QC。
- Codex CCO: 上記の判定根拠と実画像の確認、修正先の決定・指示、再レビュー確認、正式納品承認。

正式定義の出力と既存v5の承認JSONは形式が異なる。[接続状況](../.claude/agents/README.md) を確認し、未接続・未実行の審査をPASSとして扱わない。

## 流れ
1. CCOがCandidate、Creative Spec、expected-copy、compact Fact、ヒアリング要件、benchmark最大3、asset_sourceと採用原本、OCR結果（あれば）を揃え、選定したReviewerへレビュー範囲と出力条件を指示する。標準担当は [Codex Independent Creative Reviewer](../.codex/agents/independent-creative-reviewer.md)。
2. Reviewerは実画像を読み、判定・根拠・文字のreadback・問題の原因・具体的な編集指示案をCCOへ返す。実際のreviewer_providerと担当を記録する。
3. CCOが適用する出力schemaとの整合を確認し、レビューの根拠を実画像・Fact・依頼内容と照合する。
4. NGならCCOが原因工程と担当Agentを決め、修正内容と保持条件を指示する。再提出物をCCOがレビューし、Reviewerへ必要な再レビューを指示する。
5. 独立レビューの合格後も、案件を統括するCodex CCO自身が画像を目視し、Fact・文字・品質・複数案の差別化を最終確認する。
6. CCOが実際のレビュー結果に基づく承認JSONを保存し、`scripts/promote_creative.py` で承認済み画像のみを1枚ずつ案件の `05_delivery` へ昇格する。コピー文・承認JSON・生成記録の納品時点の控えは `04_project_review/delivery_records/<creative-id>/<version>/` へ保存する。
7. Human Final Approvalを残す。解決不能な曖昧性や修正上限への到達時は、CCOが状況を整理して `needs_human_review` とする。

## PASS条件
- CCOが選んだ担当による実際の独立レビューがpass相当で、適用するschema・設定の審査条件を満たす。Codexによる検証をClaude実施済みと記録しない。
- required text / critical numbersの目視readbackが一致し、Fact・ヒアリング・素材選定の整合が確認できる。
- Codex CCO自身の最終目視確認がPASS。
- critical issueと未解消のReviewer failがない。
- 承認JSONと対象Creative・version・Candidateが一致し、納品昇格の検証を通る。

Reviewerの点数だけでPASSにせず、未解消failをCCO承認で上書きしない。
