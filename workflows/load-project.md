# Load Project Workflow

## 目的
Claude / Codex がGoogle Drive上の対象案件だけを安全に読み込むための標準手順。

## 実行方法

```bash
python scripts/load_project.py PJ-0001
```

案件フォルダ名を直接指定してもよい。

```bash
python scripts/load_project.py PJ-0001_test
```

## 実行結果

リポジトリ内の一時領域に以下を生成する。

```text
tmp/current-project/
├─ context.json
└─ context.md
```

`tmp/` はGit管理対象外とし、案件データをGitHubへ保存しない。

## Claude / Codex の参照順
1. `CLAUDE.md` / `AGENTS.md`
2. `tmp/current-project/context.md`
3. `tmp/current-project/context.json`
4. context内に記載されたGoogle Drive上の案件ファイル

## 重要ルール
- 案件作業前に必ず対象 `project_id` を確定する。
- 複数案件を同時に暗黙参照しない。
- `PROJECTS_ROOT` 全体を無差別に読み込まない。
- 実案件データをGitHub管理対象へコピーしない。
- contextは案件切替のたびに再生成する。
