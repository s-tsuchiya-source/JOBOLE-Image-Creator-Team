# Agent Tuning Guide — Codex Native ImageGen v5

## Architecture
```text
VSCode Codex CCO
├─ Claude Recruitment Analyst
├─ Claude Creative Director
├─ Codex Integrated Creative Designer + ImageGen
└─ Claude Creative Reviewer

Python
→ context / candidate registration / OCR helper / delivery control / Safe fallback
```

## Tuning Priority
品質改善は次の順で行う。

1. `.codex/agents/integrated-creative-designer.md`
2. `original_image` benchmark quality
3. `.claude/agents/creative-director.md`
4. `.claude/agents/creative-reviewer.md`
5. `services/creative_spec.py`
6. `.claude/agents/recruitment-analyst.md`
7. `.codex/chief-creative-officer.md`
8. OCR helper
9. Safe Python renderer

PythonのLayout Templateへ戻して品質問題を解決しない。

## Benchmark
```text
G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/original_image
```

CCOが最大3件を視覚選定する。
Agentへ大量のreferenceを渡さない。

## Recruitment Analyst Tuning
改善対象:
- exact role/employment
- critical numeric facts
- verbatim claims
- claim boundaries
- visual job reality

画像品質問題のためにFact Agentを複雑化しない。

## Creative Director Tuning
改善対象:
- message axis
- copy strength
- benchmark translation
- exact text contract
- photo/Typography integration direction
- multi-creative diversity
- Designerが迷わないbrief

禁止:
- ただのPrompt長文化
- route増殖
- required text過多
- Python overlay前提

## Codex Integrated Creative Designer Tuning
最優先。

見る:
- 1枚の完成広告として統合されているか
- 人物/背景/コピー/Typographyが互いに補強しているか
- headline rhythm
- whitespace tension
- accent language
- job realism
- Japanese glyph quality
- 同案件の他画像との差

局所不具合はImageGen edit優先。
全再生成ガチャを繰り返さない。

## Reviewer Tuning
Reviewerは厳しく独立させる。

Block例:
- exact text error
- critical number error
- generic AI poster
- stock-photo-plus-caption
- mechanical repeated template
- poor photo/Typography integration
- wrong work scene
- benchmark品質不足

## ImageGen Capability
Standard routeはCodex ImageGen。
Capability unavailableなら自動API fallback禁止。

`IMAGEGEN_CAPABILITY_UNAVAILABLE` をCCOへ返す。

## Token Efficiency
- compact context first
- benchmark max 3
- route max 2
- Creative Spec reuse
- OCR summary only
- root cause revision only
- edit before regenerate
- raw source only for factual ambiguity

## Fallback
### Safe Python
文字の完全再現が優先される例外時のみ。

### Direct API
ユーザー明示承認時だけ。
Agentが勝手に選ばない。
