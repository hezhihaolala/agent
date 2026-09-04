# Family Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable single-administrator genealogy application with deterministic relationship queries, protected archives, source-backed AI answers, and confirmation-gated AI writes.

**Architecture:** Keep the existing React/Vite frontend and add one FastAPI application backed by PostgreSQL in production and SQLite for fast local tests. Caddy serves the built frontend and proxies `/api`; the backend owns authentication, genealogy rules, file access, model orchestration, drafts, and audit records.

**Tech Stack:** React, TypeScript, Vite, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, OpenAI Python SDK, Caddy, Docker Compose, Vitest, Pytest, Playwright

**Spec:** `docs/product-design.md` and `docs/technical-design.md`

## Global Constraints

- Code is implemented directly on `main`, as explicitly requested by the user.
- The MVP has one administrator and no registration, OAuth, or role hierarchy.
- The model never writes formal genealogy data; it may only query allowlisted services and create a persisted draft.
- Every draft is revalidated and explicitly confirmed before a database transaction writes formal data.
- Relationship names and paths are computed by deterministic application code, never guessed by the model.
- PostgreSQL is the production database; no graph database, Redis, Celery, Kubernetes, or large agent framework is introduced.
- Files remain private and are downloaded only through authenticated API routes.
- Every behavior change follows red-green TDD, passes the complete relevant test suite, and receives its own Git commit.
- The current host has Python 3.12 but no local Docker executable; Compose files receive static validation here and a documented Linux smoke-test command.

---

### Task 1: Backend Foundation and Single-Administrator Authentication

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/security.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `create_app(settings: Settings) -> FastAPI`
- Produces: `get_session() -> Iterator[Session]`
- Produces: authenticated request dependency returning `AdminUser`
- Produces: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `GET /api/health`

- [ ] **Step 1: Write the failing authentication tests**

```python
def test_login_sets_session_and_returns_csrf(client):
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'correct horse battery staple'})
    assert response.status_code == 200
    assert response.json()['username'] == 'admin'
    assert response.json()['csrf_token']
    assert 'guiyuan_session=' in response.headers['set-cookie']

def test_wrong_password_is_rejected(client):
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrong'})
    assert response.status_code == 401
```

- [ ] **Step 2: Run `python -m pytest backend/tests/test_auth.py -q` and verify both tests fail because the backend package and routes do not exist**
- [ ] **Step 3: Add settings, SQLAlchemy session management, administrator/session tables, Argon2id password hashing, CSRF token verification, application startup, and the four routes**
- [ ] **Step 4: Run `python -m pytest backend/tests/test_auth.py -q` and verify the authentication tests pass**
- [ ] **Step 5: Run `npm test` and `npm run build` to prove the existing frontend remains green**
- [ ] **Step 6: Commit with `git commit -m "feat: add FastAPI authentication foundation"`**

---

### Task 2: People, Relationships, and Deterministic Kinship Engine

**Files:**
- Create: `backend/app/domain/kinship.py`
- Create: `backend/app/services/genealogy.py`
- Create: `backend/app/api/genealogy.py`
- Create: `backend/tests/test_genealogy_api.py`
- Create: `backend/tests/test_kinship.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `find_relationship_path(people, relationships, source_id, target_id) -> KinshipResult | None`
- Produces: `GET/POST/PATCH/DELETE /api/persons`
- Produces: `GET/POST/DELETE /api/relationships`
- Produces: `GET /api/relationships/path?source_id=...&target_id=...`

- [ ] **Step 1: Write failing domain tests with hand-checked paths**

```python
def test_maternal_grandfather_path():
    result = find_relationship_path(people, relationships, 'mingyuan', 'shouyi')
    assert result.label == '外祖父'
    assert [step.person_name for step in result.steps] == ['张明远', '陈素贞', '陈守义']

def test_parent_cycle_is_rejected(genealogy_service):
    with pytest.raises(RelationshipConflict, match='祖先循环'):
        genealogy_service.add_parent(child_id='ancestor', parent_id='descendant')
```

- [ ] **Step 2: Run the two test files and verify failures are caused by missing engine and routes**
- [ ] **Step 3: Add person and relationship tables, schemas, CRUD services, duplicate/self/cycle validation, breadth-first path search, and direct/two-hop Chinese kinship labels**
- [ ] **Step 4: Add authenticated API tests proving CRUD, duplicate rejection, path output, and audit creation**
- [ ] **Step 5: Run `python -m pytest backend/tests/test_kinship.py backend/tests/test_genealogy_api.py -q` and verify all pass**
- [ ] **Step 6: Commit with `git commit -m "feat: add genealogy data and kinship engine"`**

---

### Task 3: Private Archives and Evidence Links

**Files:**
- Create: `backend/app/services/archives.py`
- Create: `backend/app/api/archives.py`
- Create: `backend/tests/test_archives.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `POST /api/sources` multipart upload
- Produces: `GET /api/sources`, `GET /api/sources/{id}`, `GET /api/sources/{id}/download`
- Produces: `POST /api/sources/{id}/links`
- Consumes: authenticated administrator and genealogy entity IDs from Tasks 1–2

- [ ] **Step 1: Write failing tests proving unauthenticated download is rejected, a valid PDF is stored under a random name, the SHA-256 digest is recorded, and an executable upload is rejected**
- [ ] **Step 2: Run `python -m pytest backend/tests/test_archives.py -q` and verify the route-not-found failures**
- [ ] **Step 3: Add source/source-link models, MIME and size validation, random storage names, hashing, protected download, and person/relationship evidence linking**
- [ ] **Step 4: Run the archive tests and verify uploaded test files are isolated in the pytest temporary directory**
- [ ] **Step 5: Commit with `git commit -m "feat: add private archive management"`**

---

### Task 4: Model Adapter, Source-Backed Answers, and Confirmation-Gated Drafts

**Files:**
- Create: `backend/app/agent/client.py`
- Create: `backend/app/agent/orchestrator.py`
- Create: `backend/app/services/drafts.py`
- Create: `backend/app/api/agent.py`
- Create: `backend/app/api/drafts.py`
- Create: `backend/tests/fakes.py`
- Create: `backend/tests/test_agent.py`
- Create: `backend/tests/test_drafts.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `ModelClient.parse_request(text: str) -> AgentIntent`
- Produces: `POST /api/agent/query -> AgentAnswer | DraftPreview`
- Produces: `GET /api/change-drafts/{id}`, `POST /api/change-drafts/{id}/confirm`, `POST /api/change-drafts/{id}/reject`
- Consumes: kinship and archive services from Tasks 2–3

- [ ] **Step 1: Write a failing fake-model contract test proving a relationship question returns the deterministic path and linked source rather than a model-invented answer**
- [ ] **Step 2: Write a failing draft test proving query-time parsing leaves the person count unchanged and confirmation increases it exactly once**

```python
preview = client.post('/api/agent/query', json={'message': '新增张明远的儿子张予安'}).json()
assert count_people(client) == 24
client.post(f"/api/change-drafts/{preview['draft_id']}/confirm", headers=csrf_headers)
assert count_people(client) == 25
assert client.post(f"/api/change-drafts/{preview['draft_id']}/confirm", headers=csrf_headers).status_code == 409
```

- [ ] **Step 3: Run both test files and verify failures are caused by missing agent and draft services**
- [ ] **Step 4: Implement the provider-neutral model interface, OpenAI-compatible Chat Completions adapter, fake client, allowlisted query orchestration, persisted drafts, revalidation, transactional confirmation/rejection, and audit entries**
- [ ] **Step 5: Add timeout, malformed structured output, ambiguous name, missing path, conflicting source, and already-confirmed draft tests**
- [ ] **Step 6: Run all backend tests with `python -m pytest backend/tests -q`**
- [ ] **Step 7: Commit with `git commit -m "feat: add source-backed agent and confirmed drafts"`**

---

### Task 5: Connect the React Interface to the Real API

**Files:**
- Create: `src/api.ts`
- Create: `src/types.ts`
- Create: `src/components/LoginPage.tsx`
- Create: `src/components/PersonEditor.tsx`
- Create: `src/components/SourceUploader.tsx`
- Modify: `src/App.tsx`
- Modify: `src/App.test.tsx`
- Modify: `src/styles.css`
- Modify: `vite.config.ts`

**Interfaces:**
- Consumes: all authenticated APIs from Tasks 1–4
- Produces: browser flows for login, live overview/tree/archive data, relationship answers, draft preview, and confirmation

- [ ] **Step 1: Replace mock-only UI assertions with failing user-visible tests for login, loaded dashboard counts, API-backed relationship evidence, and draft confirmation**
- [ ] **Step 2: Run `npm test` and verify the new tests fail because no API client or authenticated application state exists**
- [ ] **Step 3: Add a typed fetch wrapper that sends cookies, copies the CSRF cookie into `X-CSRF-Token` for mutations, and converts non-2xx responses into Chinese error messages**
- [ ] **Step 4: Add the login screen and connect overview, tree, archives, chat, preview, and confirmation to backend responses while preserving the approved visual language**
- [ ] **Step 5: Run `npm test` and `npm run build`; fix only integration regressions caused by this task**
- [ ] **Step 6: Start FastAPI and Vite locally, then run a Playwright smoke flow for login → relationship question → draft preview → confirmation → refreshed member count**
- [ ] **Step 7: Commit with `git commit -m "feat: connect web app to family agent API"`**

---

### Task 6: Migrations, Production Deployment, Backup, and Final Verification

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`
- Create: `backend/Dockerfile`
- Create: `Dockerfile.web`
- Create: `compose.yaml`
- Create: `infra/Caddyfile`
- Create: `scripts/backup.sh`
- Create: `scripts/restore.sh`
- Create: `.env.example`
- Create: `docs/deployment.md`
- Modify: `README.md`
- Modify: `package.json`

**Interfaces:**
- Produces: `docker compose up -d --build` deployment on a Linux VPS
- Produces: `npm run test:all` for frontend and backend suites
- Produces: backup archive containing PostgreSQL dump and private files

- [ ] **Step 1: Write a failing migration smoke test that upgrades an empty database and verifies every expected table exists**
- [ ] **Step 2: Write a shell-level backup contract test using temporary directories and a fake `pg_dump`, proving database and archive outputs are both included**
- [ ] **Step 3: Run the new tests and verify they fail because migration and scripts are absent**
- [ ] **Step 4: Add the initial Alembic migration, API/web container builds, Compose services and health checks, Caddy routing, environment template, backup/restore scripts, and Linux deployment guide**
- [ ] **Step 5: Run `python -m pytest backend/tests -q`, `npm test`, `npm run build`, and static Compose/YAML validation**
- [ ] **Step 6: Run the complete local end-to-end smoke flow and verify there are no browser console errors or horizontal overflow at desktop and mobile widths**
- [ ] **Step 7: Update README with setup, test, deployment, backup, default-admin bootstrap, and model configuration instructions**
- [ ] **Step 8: Commit with `git commit -m "ops: add production deployment and backup"`**

---

## Completion Gate

- [ ] `python -m pytest backend/tests -q` passes with no failures.
- [ ] `npm test` passes with no failures.
- [ ] `npm run build` succeeds.
- [ ] Alembic upgrades a clean database.
- [ ] Browser smoke flows pass at desktop and mobile widths.
- [ ] The working tree is clean and every implementation stage has its own commit.
- [ ] Local `main` and `origin/main` resolve to the same commit after push.
