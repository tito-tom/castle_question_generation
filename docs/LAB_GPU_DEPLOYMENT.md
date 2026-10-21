# CASTLE QA Studio — Lab PC GPU Deployment Guide

This guide describes how to deploy CASTLE QA Studio to a dedicated NVIDIA GPU lab PC for genuine Qwen2.5-VL-7B-Instruct video understanding and question generation.

> [!IMPORTANT]
> **GPU Milestone Notice**: All instructions in this guide involving actual NVIDIA GPU execution, CUDA compilation, and model weight downloading are prepared for the upcoming Lab GPU milestone (Task 8). Commands that require physical GPU hardware are explicitly marked with `[PREPARED - PENDING GPU HARDWARE]`.

---

## 1. System Requirements

### Hardware Prerequisites
- **Target GPU**: NVIDIA GPU with >= 16 GB VRAM (Recommended: RTX 4090 24GB, RTX 5090 32GB, or A100/A5000/A6000).
- **CPU**: x86_64 multi-core processor (>= 8 cores).
- **RAM**: >= 32 GB system memory.
- **Storage**: >= 50 GB free NVMe/SSD space for model weights, cache, and temporary clips.

### Software Prerequisites
- **Operating System**: Ubuntu 22.04 LTS / 24.04 LTS (or Windows 11 Pro with WSL2).
- **NVIDIA Driver**: Version >= 535.x (Recommended: >= 550.x).
- **Docker Engine**: Docker CE >= 24.0.
- **NVIDIA Container Toolkit**: `nvidia-container-toolkit` configured for Docker.

---

## 2. Host Provisioning (Phase 1)

### 2.1 Verify NVIDIA GPU and Drivers
Run in the lab PC terminal:
```bash
nvidia-smi
```
Verify that the GPU model, driver version, and CUDA version are displayed.

### 2.2 Install NVIDIA Container Toolkit (Ubuntu)
```bash
# Add NVIDIA package repositories
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker daemon and restart
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2.3 Verify Containerized GPU Access `[PREPARED - PENDING GPU HARDWARE]`
```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```
Ensure the GPU is visible inside a Docker container.

---

## 3. Secure Production Secrets Configuration

Production mode enforces that administrative endpoints (such as `POST /api/v1/videos/cleanup-temporary`) cannot be invoked without a cryptographically secure token.

### 3.1 Generate a Production Secret
Generate a high-entropy 256-bit hexadecimal string in a trusted shell:
```bash
# Using OpenSSL in Linux/macOS
openssl rand -hex 32

# Or using Python in Windows/Linux
python3 -c "import secrets; print(secrets.token_hex(32))"
```
*Example output*: `c3b84f29107d89ea2bf4801e9124ad5f7823b49e10fa674b892301fae4892c01`

### 3.2 Create `.env` on the Lab PC
Create a `.env` file in the repository root on the lab PC. **Never commit `.env` into source control.**
```ini
# Environment mode
ENVIRONMENT=production

# Paste the actual generated hexadecimal string (do not use shell command substitution)
CASTLE_INTERNAL_CLEANUP_TOKEN=c3b84f29107d89ea2bf4801e9124ad5f7823b49e10fa674b892301fae4892c01

# Inference Mode
VIDEO_UNDERSTANDING_MODE=real
VIDEO_MODEL_NAME=Qwen/Qwen2.5-VL-7B-Instruct
VIDEO_FPS=1.0
MAX_NEW_TOKENS=1024

# Model Cache Directories (inside container worker, maps to named volume castle_qa_model_cache)
HF_HOME=/root/.cache/huggingface
HF_HUB_CACHE=/root/.cache/huggingface/hub
```

### 3.3 Rotating Production Secrets
To rotate the administrative cleanup secret:
1. Generate a new token using `openssl rand -hex 32`.
2. Update `CASTLE_INTERNAL_CLEANUP_TOKEN` in `.env`.
3. Restart the API container: `docker compose restart api`.

---

## 4. Qwen2.5-VL Model Cache Setup (Phase 2)

To guarantee reproducible, offline-capable deployments and prevent repeated ~15 GB downloads:

### Correct Step-by-Step Order:
1. **Validate Hardware & Space**: Ensure at least 30 GB free space on the cache partition.
2. **Obtain Download Authorization**: Confirm lab network and Hugging Face access before downloading.
3. **Download Model Weights Once**:
   ```bash
   [PREPARED - PENDING GPU HARDWARE]
   python3 -c "
   from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
   model_id = 'Qwen/Qwen2.5-VL-7B-Instruct'
   print('Downloading processor...')
   AutoProcessor.from_pretrained(model_id)
   print('Downloading model weights...')
   Qwen2_5_VLForConditionalGeneration.from_pretrained(model_id)
   print('Model cache complete.')
   "
   ```
4. **Verify Cache Completeness**:
   Check that snapshot directories exist in `$HF_HOME/hub/models--Qwen--Qwen2.5-VL-7B-Instruct/snapshots/`.
5. **Enable Offline Execution**:
   Once weights are confirmed locally, set offline environment variables in `.env`:
   ```ini
   HF_HUB_OFFLINE=1
   TRANSFORMERS_OFFLINE=1
   ```

---

## 5. Docker Orchestration Architecture

The application uses Docker Compose with an override file to decouple CPU laptop development from GPU lab execution:

| File | Purpose | Key Settings |
| :--- | :--- | :--- |
| [compose.yaml](file:///d:/DCU-Internship/castle-question-generation/compose.yaml) | Base orchestration (CPU-compatible) | Starts `api`, `worker` (mode=mock), `frontend`. No GPU hardware requirements. |
| [compose.gpu.yaml](file:///d:/DCU-Internship/castle-question-generation/compose.gpu.yaml) | Lab PC GPU Override | Sets `VIDEO_UNDERSTANDING_MODE: real`, mounts `data/videos:ro`, mounts `model_cache` volume, reserves NVIDIA GPUs. |

### Starting the Lab Stack `[PREPARED - PENDING GPU HARDWARE]`
```bash
# Validate merged Compose configuration
docker compose -f compose.yaml -f compose.gpu.yaml config

# Launch all services in background
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build
```

### Checking Services
```bash
# View active container status
docker compose ps

# Follow GPU worker inference logs
docker compose logs -f worker

# Follow FastAPI backend logs
docker compose logs -f api
```

---

## 6. Pre-Flight Readiness Diagnostic

Before starting full inference jobs on the lab PC, run the diagnostic checker:
```bash
# Run inside container or on host:
python3 -m castle_qa.deployment.readiness_check
```
When `VIDEO_UNDERSTANDING_MODE=real`, the checker verifies:
- Python >= 3.10
- FFmpeg and FFprobe
- Storage directories and >= 1 GB free space
- PyTorch and CUDA availability (`torch.cuda.is_available() == True`)
- Pre-cached Qwen model weights in `HF_HOME`
- Production cleanup token security

---

## 7. Rollback and Safe Shutdown Procedures

### Stopping the Stack
```bash
docker compose -f compose.yaml -f compose.gpu.yaml down
```

### Emergency Rollback to Mock Mode
If GPU inference encounters hardware errors (e.g. CUDA Out of Memory or driver crashes), immediately revert the worker to deterministic mock mode without downtime:
```bash
# In .env:
VIDEO_UNDERSTANDING_MODE=mock

# Restart worker in mock mode:
docker compose -f compose.yaml up -d --no-deps worker
```
The application will immediately resume servicing requests using CPU mock inference while the GPU issue is diagnosed.

---

## 8. Deployment Security Boundaries & Trust Architecture

CASTLE QA Studio is engineered as an **intranet-only annotation assistance tool** for laboratory and research environments. It is not architected for direct, untrusted public Internet exposure.

### 8.1 Network Isolation Boundary
- **No Public Port Exposure**: Services (FastAPI backend on port 8000, Vite/Nginx frontend on port 3000) **must never be bound to a public IP address or internet-facing router without a reverse-proxy TLS termination layer and authenticating reverse-proxy**.
- **Private Lab Network or Tailscale/VPN**: Deploy the stack exclusively within a trusted lab LAN, or accessible via private overlay networks (e.g., Tailscale, WireGuard).
- **CORS Configuration**: By default in development, permissive CORS origins are allowed for rapid localhost debugging. In production, restrict `ALLOW_ORIGINS` to the exact intranet origin of the lab frontend.

### 8.2 Secret Management Invariants
- **No Committed Secrets**: The `.env` file containing `CASTLE_INTERNAL_CLEANUP_TOKEN` and operational secrets is strictly excluded by `.gitignore`.
- **Per-Host Token Generation**: The administrative cleanup token must be generated with high entropy (`openssl rand -hex 32`) on the target lab PC. Never copy default or development tokens to production.
- **Fail-Fast Security Invariant**: If `ENVIRONMENT=production` is set and `CASTLE_INTERNAL_CLEANUP_TOKEN` is missing or matches the default development token, the FastAPI application fails startup immediately with a fatal `ValueError`.

### 8.3 Media Streaming & URL Token Disclosure Risk
- **HTML5 Video Player Restriction**: Native browser `<video>` elements cannot attach custom HTTP Authorization headers when requesting video streams. Therefore, stream authorization uses query parameters (`?token=...`).
- **Log Exposure Risk**: Because query parameters appear in HTTP server access logs and browser histories, temporary access tokens may be visible in proxy logs.
- **Mitigation**: This risk is acceptable strictly within a trusted, single-tenant private lab environment. For multi-tenant or enterprise deployments, short-lived signed URLs (HMAC with 60-second validity) or Cookie-based session tokens should be introduced.

### 8.4 Read-Only Dataset Protection
- **Dataset Preservation**: The primary CASTLE dataset volume `./data/videos` is mounted read-only (`:ro`) in both `compose.yaml` and `compose.gpu.yaml`.
- **Integrity Guarantee**: Neither the FastAPI backend nor the inference worker containers possess write or delete permissions on source recordings. Original files such as `data/videos/kitchen_8_day_1.mp4` cannot be overwritten, modified, or removed by application errors or malicious requests.

### 8.5 Real GPU Inference Validation Status
- **Physical GPU Milestone**: Real Qwen2.5-VL inference has **not yet executed** on physical NVIDIA hardware. On the Windows laptop development host, CUDA hardware is absent and real inference is explicitly blocked and labeled as `[PREPARED - PENDING GPU HARDWARE]`.
- **Execution Target**: Genuine GPU execution, CUDA memory profiling, and 1.0 FPS Qwen2.5-VL-7B-Instruct inference will occur as the primary objective of Task 8 on the physical lab PC.

---

## 9. Reproducible Lab Handover & Git Transfer Procedures

Because development on the laptop included untracked files and local modifications that are not yet committed or pushed to the remote repository, a bare `git clone` on the lab PC will **not** contain the Tasks 1–7D.1 implementation.

### 9.1 Transfer Options

#### Option A: Commit and Push (Recommended Standard Flow)
From the repository root on the laptop:
```powershell
# 1. Review status and stage files
git status
git add -A

# 2. Commit with descriptive handover message
git commit -m "feat(handover): complete laptop development tasks 1-7d.1 with provenance and gpu compose"

# 3. Push to remote feature branch
git push origin feature/fastapi-backend
```
Then on the Lab PC:
```bash
git clone -b feature/fastapi-backend https://github.com/tito-tom/castle_question_generation.git
cd castle_question_generation
```

#### Option B: Offline Git Bundle Transfer (Air-Gapped or Pre-Commit Verification)
If uncommitted local changes cannot be pushed to GitHub immediately:
```powershell
# On Laptop: Create a complete git bundle
git bundle create castle_qa_studio_handover.bundle HEAD feature/fastapi-backend

# Copy the bundle and untracked files (e.g. data/videos/kitchen_8_day_1.mp4) via USB drive or SCP:
# scp castle_qa_studio_handover.bundle user@lab-pc:/path/to/work/
```
On Lab PC:
```bash
git clone castle_qa_studio_handover.bundle castle_question_generation
cd castle_question_generation
```

### 9.2 Lab PC Clean Installation Verification
From the repository root on the lab PC:
```bash
# 1. Install backend with GPU dependencies from repository root:
python3 -m pip install -e "./backend[api,gpu,dev]"

# 2. Apply database migrations:
python3 -m alembic -c backend/alembic.ini upgrade head

# 3. Verify Golden Video SHA-256:
sha256sum data/videos/kitchen_8_day_1.mp4
# Expected: 6cc2bf95b92095a79c7fd229a0bca2900d080bc2bb91f75ec26a02fbb692ceb0

# 4. Run pre-flight diagnostic:
python3 -m castle_qa.deployment.readiness_check
```

