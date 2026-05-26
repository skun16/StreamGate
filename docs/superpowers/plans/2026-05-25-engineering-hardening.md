# StreamGate Engineering Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small production-readiness pass for StreamGate without changing the public chat API behavior.

**Architecture:** Keep chat behavior unchanged, add a focused diagnostics router for safe configuration visibility, add pytest coverage around diagnostics and RAGFlow client behavior, and remove empty placeholder modules that imply unfinished middleware/services. Configuration examples live at the repository root.

**Tech Stack:** Python 3.13, FastAPI, httpx, pydantic-settings, pytest, FastAPI TestClient.

---

### Task 1: Test Infrastructure And Diagnostics Tests

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/test_diagnostics.py`

- [ ] **Step 1: Add test dependencies**

Run: `uv add --dev pytest`

- [ ] **Step 2: Write failing diagnostics tests**

Create tests that override config values, build the FastAPI app, and assert `GET /diagnostics/ragflow` returns safe metadata only: base URL, chat mapping booleans, timeout values, and concurrency values. The response must not include `RAGFLOW_API_KEY` or raw Chat IDs.

- [ ] **Step 3: Run diagnostics tests**

Run: `uv run pytest tests/test_diagnostics.py -v`

Expected: fail because the diagnostics router does not exist yet.

### Task 2: Diagnostics Endpoint

**Files:**
- Create: `app/api/diagnostics.py`
- Modify: `app/main.py`

- [ ] **Step 1: Implement diagnostics router**

Add `GET /diagnostics/ragflow` returning:

- `status: "ok"`
- `ragflow.base_url`
- `ragflow.api_key_configured`
- `ragflow.chat_mappings` with booleans for all configured user group and chat type pairs
- `timeouts`
- `limits`

- [ ] **Step 2: Register router**

Include the diagnostics router in `create_app()`.

- [ ] **Step 3: Run diagnostics tests**

Run: `uv run pytest tests/test_diagnostics.py -v`

Expected: pass.

### Task 3: RAGFlow Client Coverage

**Files:**
- Create: `tests/test_ragflow_client.py`

- [ ] **Step 1: Write RAGFlow client tests**

Cover chat ID selection, JSON line parsing, invalid JSON errors, and session ID reuse.

- [ ] **Step 2: Run RAGFlow client tests**

Run: `uv run pytest tests/test_ragflow_client.py -v`

Expected: pass against existing behavior.

### Task 4: Project Cleanup And Environment Example

**Files:**
- Create: `.env.example`
- Delete: `app/middleware/auth.py`
- Delete: `app/middleware/access_log.py`
- Delete: `app/services/session_service.py`
- Delete: `app/services/stream_service.py`
- Modify: `app/api/chat.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `.env.example`**

Document every environment variable from `app/core/config.py` with safe placeholder values.

- [ ] **Step 2: Remove placeholder files**

Delete four three-byte files that contain only a stray character and are not imported.

- [ ] **Step 3: Remove unused imports**

Remove unused imports from `app/api/chat.py`.

- [ ] **Step 4: Update project metadata**

Replace the placeholder project description in `pyproject.toml`.

### Task 5: Final Verification

**Files:**
- Read: all changed files

- [ ] **Step 1: Run all tests**

Run: `uv run pytest -v`

- [ ] **Step 2: Inspect git diff**

Run: `git diff --stat` and `git diff --check`.

- [ ] **Step 3: Report results**

Summarize changed files and verification output, noting that existing user changes in `test.ipynb` were left untouched.
