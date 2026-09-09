# Adobe素材優先の制作フロー

2026-09-07のユーザー指示により、人物・写真はダウンロード済みAdobe素材を優先する。
利用元は `ADOBE_IMAGE_ROOT`。未設定時も `configs/workflow.yaml` の次の既定値を使う。

`G:\共有ドライブ\ジョブオレチーム\ジョブオレチーム\JOBOLE-Image-Creator-Team\Adobe\_image`

このフォルダの画像はユーザーが制作利用を許可済み。案件ごとの再承認や追加購入・ダウンロードを標準工程にしない。
`ORIGINAL_IMAGE_ROOT` は引き続きデザインbenchmark用。Adobe素材は実際に広告へ使用する写真であり、参照用途を区別する。

## 手順

1. 案件作成、Fact確定、benchmark選定を行う。
2. `scripts/prepare_creative_context.py` がAdobe素材の一覧とcontact sheetを案件の `00_request/normalized/adobe_library/` に作成する。`creative-context.json.production_asset_library` を入口にする。Pythonの役割は一覧・確認用画像の作成だけ。
3. CCO（必要時はImage Director）が各Creativeについてcontact sheetと候補原本を目視する。職種・仕事内容・服装・道具・背景、ヒアリング、構図・文字余白、必要解像度を確認する。ファイル名がIDだけでも目視確認する。フォルダ内に適合素材があるか、トリミング・配置で活用できるかを判断する。
4. 適した素材があれば `asset_source.mode=adobe_stock` とし、使用パスと採用理由を記録。写真に合わせてArt Directionを設計し、生成しやすさだけを理由に適合素材を捨てない。素材原本は上書き・リネームしない。
5. 適した素材がない場合だけ `mode=generated` とし、確認範囲と具体的な不採用理由を記録して従来の人物・背景生成へ進む。人物不要の案では背景・手元・小物・イラスト素材も検討する。
6. Creative Directorの出力をCCOが `02_direction/<creative-id>-creative-spec.json` へ統合し、`asset_source` と `image.prompt` を一致させる。
7. DesignerはAdobe採用時、候補原本を視覚確認してImageGenの実画像入力へ添付する。対応ツールではローカル原本パスを `referenced_image_paths` に渡す。パスの文字列をプロンプトへ書くだけでは素材を使ったことにならない。benchmarkを添える場合は用途を明示する。
8. 顔・髪型・表情・服装・視線・人数・写真の内容を保持し、トリミング・縦横比を保つ拡縮・配置で広告へ組み込む。写真2枚は別領域に置く。写真の人物を生成人物へ置き換えない。文字・装飾・レイアウトを含む完成広告は引き続きImageGenで制作する。
9. Designer self-check、Reviewer、CCOが原本と完成候補を比較する。人物が変わった場合は原本を再入力して修正・再制作し、素材が使えないことにして人物生成へ切り替えない。
10. Candidate登録は選定記録を検証し、Spec snapshotと `generation-metadata.json` に保持する。Review・CCO承認・正式昇格・Human Final Approvalへ進む。

## Creative Specの追加契約

Adobe採用例（パスは採用した実ファイルに置換する）:

```json
{
  "asset_source": {
    "policy": "adobe_first",
    "library_root": "G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/Adobe/_image",
    "search_status": "completed",
    "mode": "adobe_stock",
    "selected_assets": [
      {"path": "G:/共有ドライブ/ジョブオレチーム/ジョブオレチーム/JOBOLE-Image-Creator-Team/Adobe/_image/AdobeStock_123.jpg", "reason": "職種・服装が求人に合い、トリミング後も見出しの余白を確保できる"}
    ],
    "search_summary": "一覧の全ページを確認し、職種が近い候補3点の原本を比較",
    "fallback_reason": ""
  }
}
```

適合素材なしの場合は、同じ契約の `mode` を `generated`、`selected_assets` を空配列にする。
`search_status=completed` と確認範囲の `search_summary` に加えて、`fallback_reason` に「対象業務の服装・道具を満たす写真がなく、配置やトリミングでも解消できない」等の根拠を記載する。
素材の有無はCreativeごとに判断する。複数枚のうち一部だけ生成する場合も各Specへ記録する。

## 未確認・接続不可

未検索は `search_status=pending`。共有ドライブ未接続・権限不足は `unavailable`。
`ADOBE_ASSET_LIBRARY_UNAVAILABLE` として素材選定・画像制作を止め、パス・接続を復旧する。一部に読めないファイルがある一覧は `production_asset_library.status=partial`。その場合でも、読める原本に適合素材があれば採用して制作できる。
確認漏れのある状態から「適合素材なし」として人物生成へは進めない。未対応形式は閲覧・変換して確認可能にしてから再選定する。これらは「適した画像がない」という判定ではない。
Fact分析など独立した作業は続けてよい。

旧Specはレビュー用に読み込み可能だが、`asset_source` 未記録の新規制作・Candidate登録は選定完了まで進めない。既存候補の監査記録を、Adobe使用済みと遡って書き換えない。

ImageGen capability gate、exact text、API fallbackの承認条件、正式納品の承認条件は既存契約に従う。
Adobe素材を入力できない環境では必要な画像入力を解決してから制作し、自動で人物生成やDirect APIに切り替えない。
現在のPython API fallbackは実素材の画像入力に未対応のため、Adobe採用Specでは停止する。

## 適用範囲と検証

Codexの標準制作手順、Claudeの素材関連定義、context前処理、Creative Spec正規化・制作brief、Candidate登録に適用する。
11専門Agent全体のPython自動実行・未配置schemaの接続状況は [.claude/agents/README.md](../.claude/agents/README.md) に従う。

使用 pattern: `job-posting-image-validation-checklist` の事実一致・視認性、`agent-design` の入力共有と詳細手順の分離。
未使用理由: 前者の誤字許容部分は、プロジェクトのexact text必須条件を優先。
Stop Knowledge Check候補: 「既存素材優先では、適合なしと未検索・接続不可を分け、選定記録を制作Specから登録metadataまで保持する」。中央ナレッジは更新しない。
