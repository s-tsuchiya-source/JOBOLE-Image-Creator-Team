from __future__ import annotations

import json
import platform
import shutil
import subprocess


def _run_nvidia_smi(command: str) -> list[dict]:
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
        return []

    rows: list[dict] = []
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
                "vendor": "NVIDIA",
                "name": name,
                "vram_mb": vram_mb,
                "vram_gb": round(vram_mb / 1024, 2) if vram_mb else None,
                "free_mb": memory_free,
                "driver": driver,
                "detection": "nvidia-smi",
            }
        )
    return rows


def _windows_video_controllers() -> list[dict]:
    if platform.system().lower() != "windows":
        return []
    powershell = shutil.which("powershell") or shutil.which("powershell.exe")
    if not powershell:
        return []

    script = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterRAM,DriverVersion,VideoProcessor,PNPDeviceID | "
        "ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [powershell, "-NoProfile", "-Command", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        timeout=30,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []

    rows: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or "Unknown GPU")
        lowered = name.lower()
        pnp = str(item.get("PNPDeviceID") or "").lower()
        if "nvidia" in lowered or "ven_10de" in pnp:
            vendor = "NVIDIA"
        elif any(value in lowered for value in ("amd", "radeon", "advanced micro devices")) or "ven_1002" in pnp:
            vendor = "AMD"
        elif "intel" in lowered or "ven_8086" in pnp:
            vendor = "Intel"
        else:
            vendor = "Unknown"

        adapter_ram = item.get("AdapterRAM")
        try:
            # Win32_VideoController.AdapterRAM can be inaccurate on some modern GPUs,
            # especially above 4 GB. Use it only as a fallback indicator.
            vram_bytes = int(adapter_ram or 0)
        except (TypeError, ValueError):
            vram_bytes = 0
        rows.append(
            {
                "vendor": vendor,
                "name": name,
                "adapter_ram_reported_gb": round(vram_bytes / (1024**3), 2) if vram_bytes else None,
                "driver": str(item.get("DriverVersion") or ""),
                "video_processor": str(item.get("VideoProcessor") or ""),
                "detection": "Win32_VideoController",
                "note": "AdapterRAM is a fallback value and may be inaccurate on modern GPUs.",
            }
        )
    return rows


def _recommend(rows: list[dict]) -> None:
    vendors = {str(row.get("vendor") or "") for row in rows}
    nvidia_rows = [row for row in rows if row.get("vendor") == "NVIDIA" and row.get("vram_mb")]

    if nvidia_rows:
        max_vram = max(int(row.get("vram_mb") or 0) for row in nvidia_rows)
        if max_vram >= 16384:
            message = "NVIDIA 16GB以上: 高品質ローカルモデルの検証に向いています。"
        elif max_vram >= 12288:
            message = "NVIDIA 12GB以上: SDXL系のローカル検証を行いやすい構成です。"
        elif max_vram >= 8192:
            message = "NVIDIA 8GB以上: 設定を抑えればローカル画像テストが可能です。"
        elif max_vram >= 6144:
            message = "NVIDIA 6GB前後: 低VRAM設定が必要になる可能性があります。"
        else:
            message = "NVIDIA 6GB未満: 高品質ローカル生成は厳しい可能性があります。"
        print("Recommendation:", message)
        return

    if "AMD" in vendors:
        print("Recommendation: AMD GPUを検出しました。WindowsではCUDA版AUTOMATIC1111をそのまま使えないため、DirectML/対応バックエンドを選定します。")
        return
    if "Intel" in vendors:
        print("Recommendation: Intel GPUを検出しました。GPU型番に応じてOpenVINO/DirectML系またはCPUテストを選定します。")
        return

    print("Recommendation: 専用GPUを確認できませんでした。CPUのみの画像生成は可能ですが非常に遅いため、初回疎通用に限定するかOpenAI Image APIを推奨します。")


def main() -> None:
    nvidia_command = shutil.which("nvidia-smi")
    nvidia_rows = _run_nvidia_smi(nvidia_command) if nvidia_command else []

    if nvidia_rows:
        print("GPU CHECK: PASS")
        print(json.dumps(nvidia_rows, ensure_ascii=False, indent=2))
        _recommend(nvidia_rows)
        return

    generic_rows = _windows_video_controllers()
    if generic_rows:
        print("GPU CHECK: PASS (Windows generic detection)")
        print("nvidia-smi: not found")
        print(json.dumps(generic_rows, ensure_ascii=False, indent=2))
        _recommend(generic_rows)
        return

    print("GPU CHECK: NO GPU INFORMATION")
    print("nvidia-smi と Windows VideoController の両方からGPU情報を取得できませんでした。")
    print("ローカル画像AIはCPUでも動作可能ですが、実用速度は大幅に低下します。")
    print("OpenAI画像APIへの切替は IMAGE_BACKEND=openai で可能です。")


if __name__ == "__main__":
    main()
