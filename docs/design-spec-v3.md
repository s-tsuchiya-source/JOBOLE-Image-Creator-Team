# Design Spec v3 — Safe Mode Fallback

> **Current primary architecture is Premium Integrated AI v4.**
> See `docs/premium-integrated-ai-v4.md`.

このv3方式は削除していませんが、現在の標準制作経路ではありません。

## When to use
Codex CCOが次の場合に `safe_python` を選んだときだけ使用します。

- Premium Modeで同じrequired Japanese text errorが繰り返される
- 数値/条件の差し替え頻度が高く、文字の完全再現性が最優先
- 緊急修正
- Premium image backendを利用できない

## Safe Mode Flow
```text
Fact / Hearing / Benchmark
↓
Creative Director Safe Design Spec
↓
Image AI: text-free visual
↓
Python Design Spec Renderer
↓
Creative Reviewer
↓
Codex Final QA
```

## Components kept for fallback
- `services/design_spec.py`
- `services/overlay_renderer.py`
- `configs/layouts.yaml`
- `scripts/preview_design_spec.py`
- `scripts/test_design_renderer.py`

## Important
Safe ModeのPython RendererをPremium Modeの品質上限にしません。
標準は画像AIが写真・装飾・Typography・日本語文字を一体生成するv4です。
