# AGENTS.md

## Goal
求人ファイルだけでも、**Project → Fact → Benchmark → Creative Spec → Codex ImageGen完成広告 → Review → Formal Delivery**まで進める。

標準は `codex_imagegen`。
画像実制作はCodex Integrated Creative Designerが担う。

## Active Team
```text
Codex CCO
├─ Claude Recruitment Analyst
├─ Claude Creative Director
├─ Codex Integrated Creative Designer + ImageGen
└─ Claude Creative Reviewer
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

これらを一体の完成広告としてImageGenで制作する。

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
3. Claude Reviewer visual readback
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
- Generation artifact
- Multi-creative diversity

「読める」だけではPASSしない。
一流求人広告benchmarkと並べて納品可能かで判断。

## Revision
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
Reviewer + CCO Approval JSONが揃った後だけ `scripts/promote_creative.py` で `05_delivery` へ昇格。

Human Final Approvalは常に残す。
