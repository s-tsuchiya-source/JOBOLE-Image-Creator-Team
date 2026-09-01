# JOBOLE Image Creator Team

JOBOLE向けの画像制作を、Claude・Codex・画像生成AIを組み合わせて効率化・標準化するためのAI制作チーム用リポジトリです。

## 目的

このリポジトリでは、画像制作に必要な以下の仕組みを管理します。

- AIエージェントの役割定義
- 制作ワークフロー
- 品質チェックルール
- 各種テンプレート
- Google Drive上の案件フォルダを扱うスクリプト
- Claude / Codex が参照する共通ルール

実際の案件データや生成画像は、原則としてGitHubには保存せず、Google Drive側で管理します。

## 基本設計

```text
GitHub
├─ AIエージェント定義
├─ 制作ルール
├─ Workflow
├─ Template
├─ Config
└─ Script

Google Drive
└─ projects/
   ├─ PJ-0001/
   ├─ PJ-0002/
   └─ ...
```

GitHubは「AI制作チームそのもの」を管理し、Google Driveは「各案件の制作データ」を管理する役割分担です。

## 想定する制作フロー

```text
Human
  ↓
受注・ヒアリング
  ↓
Production Director
  ↓
Text Director
  ↓
Image Director
  ↓
Designer
  ↓
画像生成AI
  ↓
Reviewer
  ↓
NG → 修正・再生成
  ↓
PASS
  ↓
Human 最終確認
  ↓
納品
```

## 想定ディレクトリ

```text
JOBOLE-Image-Creator-Team/
│
├─ README.md
├─ CLAUDE.md
├─ AGENTS.md
├─ .gitignore
├─ .env.example
│
├─ .claude/
│   └─ agents/
│       ├─ production-director.md
│       ├─ text-director.md
│       ├─ image-director.md
│       ├─ designer.md
│       └─ reviewer.md
│
├─ workflows/
│   ├─ new-order.md
│   ├─ production.md
│   ├─ review.md
│   └─ revision.md
│
├─ rules/
│   ├─ quality.md
│   ├─ naming.md
│   └─ production.md
│
├─ templates/
│   ├─ project.yaml
│   ├─ creative.yaml
│   ├─ creative-manifest.csv
│   └─ review.md
│
├─ configs/
│   ├─ storage.yaml
│   ├─ workflow.yaml
│   └─ agents.yaml
│
├─ scripts/
│   ├─ new_project.py
│   └─ project_manager.py
│
└─ projects/
    └─ README.md
```

## 案件データの保存方針

案件ごとの実データはGoogle Driveに保存します。

想定例：

```text
Google Drive/
└─ JOBOLE-Image-Creator-Team/
    └─ projects/
        ├─ PJ-0001/
        ├─ PJ-0002/
        └─ PJ-0003/
```

将来的には `.env` または `configs/storage.yaml` にGoogle Drive上の保存先を設定し、案件作成スクリプトから自動生成できるようにします。

## 今後の構築予定

1. GitHubリポジトリ初期化
2. AIエージェント定義作成
3. 制作Workflow作成
4. 品質・命名ルール作成
5. 各種テンプレート作成
6. Google Drive保存先設定
7. 新規案件自動生成スクリプト作成
8. Claude / Codex連携
9. 画像生成AI連携
10. レビュー・修正ループの自動化

## 開発方針

- `main` は安定版として使用する
- 変更は原則feature branchで行う
- Pull Requestで内容を確認してからmainへ反映する
- APIキーや認証情報はGitHubへ直接コミットしない
- 案件画像や顧客データはGitHubへ保存しない
- AIの判断ルールは可能な限りMarkdownまたは設定ファイルとして明示する

## Status

初期構築中。
