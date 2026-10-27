# CASTLE QA Studio — Lab PC GPU Deployment Guide

This guide describes how to deploy CASTLE QA Studio to a dedicated NVIDIA GPU lab PC for genuine Qwen2.5-VL-7B-Instruct video understanding and question generation.

This guide covers Docker Compose deployment on a host with an NVIDIA GPU. The GPU override runs Qwen inference in the worker container; it does not call a hosted inference API.

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

### 2.3 Verify Containerized GPU Access
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
VIDEO_FPS=2.0
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

## 4. Qwen2.5-VL Model Cache Setup

The named Docker volume keeps the model cache across container rebuilds and restarts. Keep enough free disk space for the model files and temporary download data.

### Correct Step-by-Step Order:
1. **Validate Hardware & Space**: Ensure at least 30 GB free space on the Docker volume partition.
2. **Obtain Download Authorization**: Confirm lab network and Hugging Face access before downloading.
3. **Download Model Weights Once**:
   ```bash
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
5. **Optional Offline Execution**:
   After confirming the model loads successfully, set `HF_HUB_OFFLINE: "1"` and `TRANSFORMERS_OFFLINE: "1"` under the worker environment in `compose.gpu.yaml`.

### Model Download Troubleshooting

If the worker stays at the model-file fetching step, the host network may allow Hugging Face metadata but block the model-file transfer hosts. Allow outbound HTTPS to the hosts listed in the [Hugging Face network requirements](https://huggingface.co/docs/hub/models-downloading#downloading-behind-a-proxy-or-firewall). As a fallback, set `HF_HUB_DISABLE_XET: "1"` under the worker environment and recreate only the worker. Keep the `castle_qa_model_cache` volume; removing it forces a fresh download. See [Hugging Face environment variables](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables#hf_hub_disable_xet).

---

## 5. Docker Orchestration Architecture

The application uses Docker Compose with an override file to decouple CPU laptop development from GPU lab execution:

| File | Purpose | Key Settings |
| :--- | :--- | :--- |
| [compose.yaml](../compose.yaml) | Base orchestration | Starts the API, mock-capable worker, and frontend. |
| [compose.gpu.yaml](../compose.gpu.yaml) | GPU override | Sets real inference mode, mounts the model cache, and reserves NVIDIA GPUs. |

### Starting the Lab Stack
```bash
# Validate merged Compose configuration
docker compose -f compose.yaml -f compose.gpu.yaml config

# Launch all services in background
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build

# Apply the job-queue schema before submitting jobs
docker compose -f compose.yaml -f compose.gpu.yaml exec api python -m alembic -c /app/alembic.ini upgrade head
```

### Checking Services
```bash
# View active container status
docker compose -f compose.yaml -f compose.gpu.yaml ps

# Follow GPU worker inference logs
docker compose -f compose.yaml -f compose.gpu.yaml logs -f worker

# Follow FastAPI backend logs
docker compose -f compose.yaml -f compose.gpu.yaml logs -f api
```

---

## 6. Pre-Flight Readiness Diagnostic

Before starting full inference jobs on the lab PC, run the diagnostic checker:
```bash
# Run inside the worker container:
docker compose -f compose.yaml -f compose.gpu.yaml exec worker python -m castle_qa.deployment.readiness_check
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
This stops the containers but preserves bind-mounted project data and the named model-cache volume. Do not add `-v` unless you intend to remove named volumes.

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
- Keep the frontend and API on a trusted lab network. The application does not provide a public-facing authentication layer for arbitrary Internet traffic.

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

### 8.5 Real GPU Inference Validation
- The worker runs `Qwen/Qwen2.5-VL-7B-Instruct` locally when `VIDEO_UNDERSTANDING_MODE=real` and CUDA is available.
- The first startup downloads the model into the named cache volume. Check worker logs for model-load completion before expecting queued jobs to run.
- Inference duration depends on clip length, frame sampling, generated output, and GPU load; this guide does not promise a fixed processing time.

---

## 9. Updating the Lab PC

Push committed code from the development laptop, then pull the same branch on the Lab PC. Keep local videos, model caches, and generated data outside Git.

### 9.1 Transfer Options

#### Option A: Commit and Push (Recommended Standard Flow)
From the repository root on the laptop:
```powershell
# 1. Review status and stage files
git status
git add -A

# 2. Commit with descriptive handover message
git commit -m "Describe the change"

# 3. Push to remote feature branch
git push origin feature/fastapi-backend
```
Then on the Lab PC:
```bash
git pull origin feature/fastapi-backend
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build
docker compose -f compose.yaml -f compose.gpu.yaml exec api python -m alembic -c /app/alembic.ini upgrade head
```

#### Option B: Offline Git Bundle Transfer (Air-Gapped or Pre-Commit Verification)
If uncommitted local changes cannot be pushed to GitHub immediately:
```powershell
# On Laptop: Create a complete git bundle
git bundle create castle_qa_studio_handover.bundle HEAD feature/fastapi-backend

# Transfer the bundle. Keep local videos and generated files out of the bundle and source control.
# scp castle_qa_studio_handover.bundle user@lab-pc:/path/to/work/
```
On Lab PC:
```bash
git clone castle_qa_studio_handover.bundle castle_question_generation
cd castle_question_generation
```

### 9.2 Lab PC Verification
From the repository root on the lab PC:
```bash
# Check service state and GPU visibility.
docker compose -f compose.yaml -f compose.gpu.yaml ps
nvidia-smi
```

