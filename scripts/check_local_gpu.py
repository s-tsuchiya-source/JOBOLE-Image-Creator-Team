from __future__ import annotations

import json
import shutil
import subprocess


def main() -> None:
    command = shutil.which("nvidia-smi")
    if not command:
        print("GPU CHECK: NVIDIA GPU NOT DETECTED")
        print("nvidia-smi が見つかりません。")
        print("ローカル画像AIはCPUでも動作可能な構成がありますが、実用速度は大幅に低下します。")
        print("OpenAI画像APIへの切替は IMAGE_BACKEND=openai で可能です。")
        return

    # Keep the query to fields that are widely supported across NVIDIA drivers.
    query = "name,memory.total,memory.free,driver_version"
    completed = subprocess.run(
        [
            command,
            f"--query-gpu={query}",
            "--format=csv,noheader,nounits",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        print("GPU CHECK: FAIL")
        print((completed.stderr or completed.stdout).strip())
        raise SystemExit(2)

    rows = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            continue
        name, memory_total, memory_free, driver = parts[:4]
        try:
            vram_mb = int(float(memory_total))
        except ValueError:
            vram_mb = 0
        rows.append(
            {
                "name": name,
                "vram_mb": vram_mb,
                "vram_gb": round(vram_mb / 1024, 2) if vram_mb else None,
                "free_mb": memory_free,
                "driver": driver,
            }
        )

    print("GPU CHECK: PASS")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    if rows:
        max_vram = max(int(row.get("vram_mb") or 0) for row in rows)
        if max_vram >= 16384:
            level = "16GB以上: 高品質ローカルモデルの検証に向いています。"
        elif max_vram >= 12288:
            level = "12GB以上: SDXL系のローカル検証を行いやすい構成です。"
        elif max_vram >= 8192:
            level = "8GB以上: 設定を抑えればローカル画像テストが可能です。"
        elif max_vram >= 6144:
            level = "6GB前後: 低VRAM設定が必要になる可能性があります。"
        else:
            level = "6GB未満: 高品質ローカル生成は厳しい可能性があります。"
        print("Recommendation:", level)


if __name__ == "__main__":
    main()
