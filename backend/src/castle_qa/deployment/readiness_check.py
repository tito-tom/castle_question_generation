"""
Deployment Readiness Checker for CASTLE QA Studio.

Performs read-only validation of runtime environment, dependencies, storage paths,
configuration, and GPU availability before deployment or test execution.

Does NOT modify databases, install dependencies, download models, or leak secrets.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def check_python_environment() -> Dict[str, Any]:
    """Check Python version and core runtime libraries."""
    py_ver = sys.version_info
    passed = py_ver >= (3, 10)
    version_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"

    return {
        "check": "Python Runtime",
        "status": "PASS" if passed else "FAIL",
        "details": f"Python {version_str} (requires >= 3.10)",
    }


def check_ffmpeg() -> Dict[str, Any]:
    """Check availability of FFmpeg and FFprobe on PATH."""
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    if not ffmpeg_path or not ffprobe_path:
        missing = []
        if not ffmpeg_path:
            missing.append("ffmpeg")
        if not ffprobe_path:
            missing.append("ffprobe")
        return {
            "check": "FFmpeg / FFprobe Media Tools",
            "status": "FAIL",
            "details": f"Missing from PATH: {', '.join(missing)}",
        }

    try:
        proc = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        first_line = proc.stdout.splitlines()[0] if proc.stdout else "Available"
        return {
            "check": "FFmpeg / FFprobe Media Tools",
            "status": "PASS",
            "details": f"Found ({first_line[:40]}...)",
        }
    except Exception as e:
        return {
            "check": "FFmpeg / FFprobe Media Tools",
            "status": "FAIL",
            "details": f"Execution error: {e}",
        }


def check_castle_dataset(project_root: Path) -> Dict[str, Any]:
    """Check existence and size of golden CASTLE dataset video."""
    video_path = project_root / "data" / "videos" / "kitchen_8_day_1.mp4"
    if not video_path.exists():
        return {
            "check": "CASTLE Golden Video (kitchen_8_day_1.mp4)",
            "status": "FAIL",
            "details": f"Golden video not found at {video_path}",
        }

    size_mb = round(video_path.stat().st_size / (1024 * 1024), 2)
    return {
        "check": "CASTLE Golden Video (kitchen_8_day_1.mp4)",
        "status": "PASS",
        "details": f"Present ({size_mb} MB) at data/videos/kitchen_8_day_1.mp4",
    }


def check_directories_and_storage(project_root: Path) -> List[Dict[str, Any]]:
    """Check required data directories, accessibility, and disk space."""
    results = []
    required_dirs = [
        ("Videos Directory", project_root / "data" / "videos"),
        ("Clips Directory", project_root / "data" / "clips"),
        ("Temporary Uploads Directory", project_root / "data" / "clips" / "temp_uploads"),
        ("Analysis Directory", project_root / "data" / "analysis"),
        ("Questions Directory", project_root / "data" / "questions"),
        ("Reviews Directory", project_root / "data" / "reviews"),
        ("Jobs DB Directory", project_root / "data" / "jobs"),
    ]

    for label, dir_path in required_dirs:
        if dir_path.exists() and dir_path.is_dir():
            status = "PASS"
            details = f"Accessible at {dir_path.name}/"
        else:
            status = "FAIL"
            details = f"Directory not found: {dir_path}"
        results.append({
            "check": f"Storage: {label}",
            "status": status,
            "details": details,
        })

    # Disk space check
    data_dir = project_root / "data"
    try:
        total, used, free = shutil.disk_usage(data_dir)
        free_gb = round(free / (1024 ** 3), 2)
        status = "PASS" if free_gb >= 1.0 else "FAIL"
        results.append({
            "check": "Storage: Free Disk Space",
            "status": status,
            "details": f"{free_gb} GB free on {data_dir.drive or data_dir.root} (min 1.0 GB required)",
        })
    except Exception as e:
        results.append({
            "check": "Storage: Free Disk Space",
            "status": "FAIL",
            "details": f"Could not determine disk usage: {e}",
        })

    return results


def check_configuration_and_security() -> List[Dict[str, Any]]:
    """Validate environment settings and security configurations."""
    results = []
    env_mode = os.environ.get("ENVIRONMENT", "development").lower()
    results.append({
        "check": "Environment Mode",
        "status": "PASS",
        "details": f"ENVIRONMENT={env_mode}",
    })

    # Cleanup Secret Verification
    token = os.environ.get("CASTLE_INTERNAL_CLEANUP_TOKEN", "")
    if env_mode in ("production", "prod"):
        if not token or token == "castle_internal_cleanup_secret":
            results.append({
                "check": "Production Cleanup Secret",
                "status": "FAIL",
                "details": "CASTLE_INTERNAL_CLEANUP_TOKEN is unset or using insecure default secret in production mode",
            })
        else:
            results.append({
                "check": "Production Cleanup Secret",
                "status": "PASS",
                "details": "Configured with secure non-default administrative secret [REDACTED]",
            })
    else:
        results.append({
            "check": "Development Cleanup Secret",
            "status": "PASS",
            "details": "Development mode allows default secret for automated local testing",
        })

    return results


def check_inference_mode_and_gpu() -> List[Dict[str, Any]]:
    """Validate inference mode and check NVIDIA CUDA availability when relevant."""
    results = []
    mode = os.environ.get("VIDEO_UNDERSTANDING_MODE", "mock").lower().strip()

    if mode not in ("real", "mock"):
        results.append({
            "check": "Inference Mode Configuration",
            "status": "FAIL",
            "details": f"Invalid mode '{mode}'. Canonical supported modes are 'real' or 'mock'.",
        })
        return results

    results.append({
        "check": "Inference Mode Configuration",
        "status": "PASS",
        "details": f"VIDEO_UNDERSTANDING_MODE={mode}",
    })

    if mode == "mock":
        results.append({
            "check": "Worker Engine (Mock Mode)",
            "status": "PASS",
            "details": "Deterministic mock simulation selected. No NVIDIA GPU or CUDA runtime required.",
        })
        results.append({
            "check": "GPU Acceleration (CUDA)",
            "status": "NOT REQUIRED",
            "details": "Not required for mock execution (CPU-only development host).",
        })
        results.append({
            "check": "Model Weight Cache",
            "status": "NOT REQUIRED",
            "details": "Not required for mock execution.",
        })
    elif mode == "real":
        # Check Torch
        try:
            import torch
            has_torch = True
            torch_ver = torch.__version__
        except ImportError:
            has_torch = False
            torch_ver = "Not installed"

        if not has_torch:
            results.append({
                "check": "PyTorch Framework",
                "status": "FAIL",
                "details": "PyTorch is not installed. Required for real Qwen2.5-VL inference.",
            })
            results.append({
                "check": "GPU Acceleration (CUDA)",
                "status": "BLOCKED",
                "details": "Blocked: PyTorch is missing.",
            })
            return results

        results.append({
            "check": "PyTorch Framework",
            "status": "PASS",
            "details": f"PyTorch {torch_ver} available.",
        })

        if not torch.cuda.is_available():
            results.append({
                "check": "GPU Acceleration (CUDA)",
                "status": "BLOCKED",
                "details": (
                    "NVIDIA CUDA hardware / runtime not available on this host. "
                    "Genuine Qwen2.5-VL inference is blocked on CPU-only machines. "
                    "Action: Set VIDEO_UNDERSTANDING_MODE=mock on laptop, or run on lab PC with NVIDIA GPU."
                ),
            })
        else:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_count = torch.cuda.device_count()
            total_vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
            results.append({
                "check": "GPU Acceleration (CUDA)",
                "status": "PASS",
                "details": f"CUDA available ({gpu_count} device(s)). Primary: {gpu_name} ({total_vram_gb} GB VRAM)",
            })

        # Model cache presence check (read-only inspection of HF_HOME)
        hf_home = Path(os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface" / "hub"))
        model_name = os.environ.get("VIDEO_MODEL_NAME", "Qwen/Qwen2.5-VL-7B-Instruct")
        model_dir_slug = f"models--{model_name.replace('/', '--')}"
        model_cache_path = hf_home / model_dir_slug

        if model_cache_path.exists():
            results.append({
                "check": "Model Weight Cache",
                "status": "PASS",
                "details": f"Pre-cached weights found at {model_cache_path}",
            })
        else:
            results.append({
                "check": "Model Weight Cache",
                "status": "NOT PRESENT",
                "details": f"Weights not pre-cached at {model_cache_path}. Online download required on initial real run.",
            })

    return results


def run_all_checks(project_root: Path | None = None) -> Tuple[List[Dict[str, Any]], bool, bool]:
    """
    Run all readiness checks and return results, overall pass status, and blocked status.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[4]
        if not (project_root / "compose.yaml").exists():
            project_root = Path.cwd()
    else:
        project_root = Path(project_root).resolve()

    checks = []
    checks.append(check_python_environment())
    checks.append(check_ffmpeg())
    checks.append(check_castle_dataset(project_root))
    checks.extend(check_directories_and_storage(project_root))
    checks.extend(check_configuration_and_security())
    checks.extend(check_inference_mode_and_gpu())

    has_fail = any(c["status"] == "FAIL" for c in checks)
    has_blocked = any(c["status"] == "BLOCKED" for c in checks)

    all_pass = not has_fail and not has_blocked
    return checks, all_pass, has_blocked


def print_readiness_report():
    """Print formatted terminal report."""
    print("=" * 80)
    print("CASTLE QA Studio — Deployment & Lab PC Readiness Checker")
    print("=" * 80)

    checks, all_pass, is_blocked = run_all_checks()

    col_w_check = 34
    col_w_status = 14

    print(f"{'CHECK':<{col_w_check}} | {'STATUS':<{col_w_status}} | DETAILS")
    print("-" * 80)

    for item in checks:
        status = item["status"]
        if status == "PASS":
            badge = "[PASS]"
        elif status == "FAIL":
            badge = "[FAIL]"
        elif status == "BLOCKED":
            badge = "[BLOCKED]"
        else:
            badge = f"[{status}]"

        print(f"{item['check']:<{col_w_check}} | {badge:<{col_w_status}} | {item['details']}")

    mode = os.environ.get("VIDEO_UNDERSTANDING_MODE", "mock").lower().strip()
    print("-" * 80)
    if all_pass:
        if mode == "mock":
            print("OVERALL READINESS: READY FOR DEVELOPMENT (CPU mock environment ready, zero GPU required)")
        else:
            print("OVERALL READINESS: READY FOR LAB GPU INFERENCE (All GPU prerequisites met)")
        return 0
    elif is_blocked:
        print("OVERALL READINESS: BLOCKED (Genuine Qwen GPU acceleration blocked on this host)")
        print("Action: Use VIDEO_UNDERSTANDING_MODE=mock for laptop development, or deploy on NVIDIA GPU Lab PC.")
        return 2
    else:
        print("OVERALL READINESS: NOT READY (One or more critical failures detected)")
        return 1


if __name__ == "__main__":
    sys.exit(print_readiness_report())
