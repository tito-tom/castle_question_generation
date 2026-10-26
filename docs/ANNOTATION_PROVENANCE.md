# CASTLE QA Studio — Annotation Provenance & Quality Standards

This document describes how annotation metadata, provenance, confidence scores, and lifecycle states are tracked throughout the CASTLE QA Studio platform.

---

## 1. Inference Provenance: Mock vs Real vs Legacy Unverified

To prevent synthetic or mock simulations from contaminating dataset training or evaluation benchmarks, the system maintains strict provenance tracking across the data pipeline.

### 1.1 Canonical Provenance States
Every video analysis and annotation review session carries two provenance fields:
- `is_mock`: Boolean flag (`true` or `false`).
- `inference_mode`: Canonical string (`"real"`, `"mock"`, or `"legacy_unverified"`).

The system enforces four deterministic classification rules:
1. **Explicit Real Inference**: Requires both `is_mock: false` and `inference_mode: "real"`. Displayed without banners. Only explicit real inference can produce `human_verified: true` in Whodunnit exports.
2. **Explicit Mock Simulation**: Any record with `is_mock: true` or `inference_mode: "mock"`. The UI renders an amber `[MOCK / TEST DATA]` banner, and exports tag items as `mock_test_data` or `mock_test_data_human_reviewed`.
3. **Legacy / Unverified**: Records with missing inference metadata, or records where `is_mock: false` but `inference_mode` is missing, are strictly classified as `legacy_unverified` with an amber warning banner. They are **NEVER** assumed or upgraded to real inference. Exports tag them as `legacy_unverified` or `legacy_unverified_human_reviewed` with `human_verified: false`.
4. **Contradictory Metadata Safety Invariant**: If metadata contains contradictory fields (e.g. `is_mock: true` but `model_name: "Qwen/..."` or `inference_mode: "real"`), the system safely forces `is_mock = True` and `inference_mode = "mock"` to ensure mock data can never pose as real inference.

---

## 2. QA Confidence Badges vs Calibrated Probabilities

### 2.1 Heuristic Evidence-Matching
In the Grounded Video QA panel:
- When an annotator asks a question, [GroundedVideoQAService](file:///d:/DCU-Internship/castle-question-generation/backend/src/castle_qa/services/video_qa_service.py) evaluates candidate events using token overlap and semantic matching.
- The returned `confidence` value (e.g. `0.85` / `85%`) is a **heuristic evidence-matching score**, measuring how strongly the lexical elements of the query align with the observable event descriptions.

### 2.2 Critical Distinction
> [!IMPORTANT]
> **Heuristic Score vs. Neural Probability**:
> The confidence percentage displayed in the UI is **NOT a calibrated Bayesian probability** of factual correctness. It reflects evidence correspondence between the question and the extracted event summary. High confidence indicates strong textual overlap in the event timeline, not a guaranteed empirical ground truth.

---

## 3. Human Review Statuses

Annotations progress through four standard review states:

| Status | Label | Meaning |
| :--- | :--- | :--- |
| `pending` | Pending Review | AI-generated candidate event or question awaiting human verification. |
| `accepted` | Accepted | Human annotator verified that the event/question is factually correct. |
| `edited` | Human Edited | Human annotator edited actor, action, object, or question text. |
| `rejected` | Rejected | Human annotator determined the item is hallucinatory, duplicated, or invalid. |

- In Whodunnit exports, rejected items are excluded from the main benchmark candidate pool by default.
- Accepted and edited items are tagged with `human_reviewed: true`.

---

## 4. Temporary vs Persistent Storage

```
Upload -> Temporary Clip (Inactivity TTL 24h)
            |
            v
          User clicks "Save to Library"
            |
            +---> Marked Persistent (Never deleted by cleanup runners)
```

1. **Temporary Status**: All uploaded clips, extracted intervals, generated questions, and draft review sessions are temporary by default.
2. **Inactivity Expiration**: Sessions expire after **24 hours of meaningful inactivity**. User interactions, playback, and `POST /session/{id}/touch` reset the 24-hour inactivity timer.
3. **Stream & Job Protection**: Even if a session's 24-hour timer expires, active inference jobs and active stream leases protect the required media files from being purged.
4. **Persistent Status**: When an annotator clicks **"Save to Library"**, `POST /api/v1/annotations/sessions/{review_id}/save-persistent` is called. The session file is atomically written with `"persistent": true`, permanently exempting it from automated cleanups.

---

## 5. Dual Timestamp Coordinate Mapping

Because original CASTLE recordings are approximately one hour long (~3600 seconds) and local extractions may be up to 600 seconds, event timestamps exist in two coordinate spaces:

```
Source Video (0.0s to ~3745.0s)
  |--------------------------[ Subclip: 120.0s to 720.0s ]------------------------|
                               |                       |
                               v                       v
Uploaded Clip (0.0s to 600.0s) 0.0s                 600.0s
                               |                       |
Event A:                       |-----[ 10.0s - 15.0s ]-|
```

- **`start_seconds` / `end_seconds`**: Relative to the uploaded clip (`10.0s` to `15.0s`). Passed directly to the browser's `<video>` player for seeking and playback bounds.
- **`source_start_seconds` / `source_end_seconds`**: Absolute time in the original CASTLE video (`130.0s` to `135.0s`). Recorded using the extraction offset:
  $$\text{source\_start} = \text{clip\_start} + \text{offset}$$
- **Approximate Alignment**: For native FFmpeg keyframe extractions (`-c copy`), minor keyframe discrepancies (typically < 0.5s) may exist between the exact cut boundary and the nearest I-frame. Annotators should visually verify temporal alignment before finalizing high-precision benchmarks.

---

## 6. Whodunnit Export Adapter Scope and Limitations

1. **Configurable Adapter**: The export adapter generates structured JSON and CSV outputs designed for Whodunnit benchmark research.
2. **Not an Official Schema**: The export format is a compatible research draft and does not represent an officially certified or locked Whodunnit schema.
3. **Distractor Generation**: Multiple-choice candidate distractors are derived heuristically from other identified actors and observed actions in the scene, and must be reviewed by annotators to eliminate unintentional duplicate answers.

---

## 7. Frame Sampling Rates: Baseline vs Proposed Experiments

- **Existing Baseline**: **1.0 FPS** (1 frame per second). This provides reliable temporal coverage while keeping token counts within standard GPU context limits (~1024 to ~1536 tokens).
- **Proposed Experiment (2.0 FPS)**: Increasing sampling rate to 2.0 FPS provides finer temporal granularity for rapid interactions, but doubles token consumption and VRAM usage. It is supported as a configurable option (`VIDEO_FPS=2.0`), not an established baseline.

