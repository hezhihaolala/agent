# Relationship Inference and Family Network Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trustworthy sibling/parent inference, bidirectional spouse aliases, preset person attributes, and a read-only person-centered family relationship network.

**Architecture:** PostgreSQL remains the only persistent store and contains direct facts only. A pure deterministic domain module derives relationships at request time; both the agent and a bounded network service consume that module, while React Flow renders returned nodes and direct/inferred edges.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL, SQLite tests, React, TypeScript, Vite, `@xyflow/react`, Pytest, Vitest, Testing Library, Playwright

**Spec:** `docs/superpowers/specs/2026-09-04-relationship-inference-network-design.md`

## Global Constraints

- Implement directly on `main`, as previously requested by the user.
- PostgreSQL stores direct facts only; inferred relationships are never inserted into `relationships`.
- Do not introduce Neo4j, a derived-relationship cache table, Redis, or a second persistence system.
- Existing `sibling` rows migrate to `sibling_type = "unknown"`; never reinterpret old data as full siblings.
- Stored sibling types are exactly `full`, `paternal_half`, `maternal_half`, and `unknown`.
- Parent information may propagate through a direct sibling fact only according to its stored subtype.
- Incomplete parent data produces partial labels, not an unsupported full/half-sibling conclusion.
- Direct and inferred facts remain distinguishable in API responses and UI text, line style, and accessibility labels.
- The family network defaults to two generations and rejects values outside `1..4`.
- The network is read-only; relationship writes continue through the existing form and confirmation flow.
- Every behavior change follows red-green TDD, runs the complete relevant suites, and receives its own Git commit.
- Immediately push every task commit to `ssh://git@ssh.github.com:443/hezhihaolala/agent.git main:main`, then fetch and require `git rev-list --left-right --count main...origin/main` to print `0 0`.
- Preserve the untracked `.idea/` directory and never include it in a commit.

## File and Responsibility Map

- `backend/alembic/versions/0002_relationship_inference_network.py`: preset person columns and backfilled sibling subtype.
- `backend/app/models.py`: persistence fields only.
- `backend/app/schemas.py`: API contracts for people, sibling subtype, effective facts, and network data.
- `backend/app/domain/relationship_inference.py`: pure direct/inferred fact generation and conflict detection.
- `backend/app/domain/kinship.py`: shortest paths and Chinese labels over effective facts.
- `backend/app/services/genealogy.py`: validation and persistence of direct facts.
- `backend/app/services/relationship_network.py`: bounded network assembly, source aggregation, and filters.
- `backend/app/api/genealogy.py`: CRUD and read-only network routes.
- `backend/app/agent/orchestrator.py`: deterministic lookup using the shared inference module.
- `backend/app/agent/client.py`: model parser vocabulary.
- `src/features/family-network/layout.ts`: deterministic coordinates by generation and relationship role.
- `src/features/family-network/FamilyNetwork.tsx`: React Flow canvas, controls, errors, and center switching.
- `src/features/family-network/PersonDetailPanel.tsx`: desktop panel and mobile bottom drawer.
- `src/components/PersonEditor.tsx`: preset person attributes.
- `src/App.tsx`: composition of the new feature and existing maintenance form.
- `src/types.ts`, `src/api.ts`, and `src/styles.css`: frontend contracts, network request, and presentation.

---

### Task 1: Persist Preset Attributes and Sibling Subtypes Safely

**Files:**
- Create: `backend/alembic/versions/0002_relationship_inference_network.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/genealogy.py`
- Modify: `backend/tests/test_deployment.py`
- Modify: `backend/tests/test_genealogy_api.py`

**Interfaces:**
- Produces: optional person fields `birth_place`, `courtesy_name`, `art_name`, `aliases`, `generation_name`, `family_rank`, and `occupation`.
- Produces: `SiblingType = Literal["full", "paternal_half", "maternal_half", "unknown"]`.
- Produces: `RelationshipCreate.sibling_type: SiblingType | None` and the same response field.
- Enforces: a new sibling defaults to `unknown`; non-sibling requests reject a non-null subtype.

- [ ] **Step 1: Add a failing migration compatibility test**

In `backend/tests/test_deployment.py`, upgrade to `0001_initial`, insert two people and one old sibling row, upgrade to `head`, then assert:

```python
columns = {item["name"] for item in inspect(engine).get_columns("persons")}
with engine.connect() as connection:
    sibling_type = connection.scalar(
        text("SELECT sibling_type FROM relationships WHERE id='r1'")
    )
assert {
    "birth_place", "courtesy_name", "art_name", "aliases",
    "generation_name", "family_rank", "occupation",
} <= columns
assert sibling_type == "unknown"
```

Use explicit `INSERT` statements containing all non-null `0001_initial` columns and fixed IDs `p1`, `p2`, and `r1` so the test is deterministic.

- [ ] **Step 2: Add failing API contract tests**

Add to `backend/tests/test_genealogy_api.py`:

```python
def test_person_attributes_and_sibling_type_round_trip(tmp_path):
    with authenticated_client(tmp_path) as client:
        first = client.post("/api/persons", json={
            "name": "贺志豪", "gender": "male", "birth_place": "湖南衡阳",
            "courtesy_name": "守成", "art_name": "归源", "aliases": "阿豪",
            "generation_name": "志", "family_rank": "长子", "occupation": "教师",
        }).json()
        second = create_person(client, "贺志兰", "female")
        relation = client.post("/api/relationships", json={
            "kind": "sibling", "sibling_type": "full",
            "person_id": first["id"], "relative_id": second["id"],
        })
    assert first["birth_place"] == "湖南衡阳"
    assert first["generation_name"] == "志"
    assert relation.status_code == 201
    assert relation.json()["sibling_type"] == "full"


def test_sibling_type_is_rejected_for_spouse(tmp_path):
    with authenticated_client(tmp_path) as client:
        first = create_person(client, "贺志豪", "male")
        second = create_person(client, "管应拉", "female")
        response = client.post("/api/relationships", json={
            "kind": "spouse", "sibling_type": "full",
            "person_id": first["id"], "relative_id": second["id"],
        })
    assert response.status_code == 422
```

- [ ] **Step 3: Run the new tests and verify the red state**

Run:

```bash
python -m pytest backend/tests/test_deployment.py::test_relationship_inference_migration_preserves_old_siblings backend/tests/test_genealogy_api.py::test_person_attributes_and_sibling_type_round_trip backend/tests/test_genealogy_api.py::test_sibling_type_is_rejected_for_spouse -q
```

Expected: failures for missing columns and `sibling_type`.

- [ ] **Step 4: Add the Alembic migration**

Create revision `0002_relationship_inference_network` with `down_revision = "0001_initial"`. Add the seven nullable person columns and nullable `relationships.sibling_type`, then backfill:

```python
op.execute(
    "UPDATE relationships SET sibling_type = 'unknown' "
    "WHERE kind = 'sibling' AND sibling_type IS NULL"
)
```

In `downgrade()`, drop `sibling_type`, then the seven person columns in reverse order. Never delete or rewrite relationship rows.

- [ ] **Step 5: Update ORM and Pydantic contracts**

Add matching nullable model fields. Define `SiblingType` and add this validator:

```python
@model_validator(mode="after")
def validate_sibling_type(self) -> "RelationshipCreate":
    if self.kind == "sibling" and self.sibling_type is None:
        self.sibling_type = "unknown"
    if self.kind != "sibling" and self.sibling_type is not None:
        raise ValueError("只有兄弟姊妹关系可以设置关系类型")
    return self
```

Add all seven optional string fields to `PersonCreate` and `PersonUpdate`. Keep direct model construction in `GenealogyService`; Pydantic supplies validated values.

- [ ] **Step 6: Run migration, API, and full backend tests**

```bash
python -m pytest backend/tests/test_deployment.py backend/tests/test_genealogy_api.py -q
python -m pytest backend/tests -q
```

Expected: all pass and the old sibling row remains with type `unknown`.

- [ ] **Step 7: Commit Task 1**

```bash
git add backend/alembic/versions/0002_relationship_inference_network.py backend/app/models.py backend/app/schemas.py backend/app/services/genealogy.py backend/tests/test_deployment.py backend/tests/test_genealogy_api.py
git commit -m "feat: add sibling subtypes and person attributes"
```

---

### Task 2: Build the Pure Relationship Inference Engine

**Files:**
- Create: `backend/app/domain/relationship_inference.py`
- Create: `backend/tests/test_relationship_inference.py`
- Modify: `backend/app/domain/kinship.py`
- Modify: `backend/tests/test_kinship.py`

**Interfaces:**
- Produces: `RelationshipOrigin = Literal["direct", "inferred"]`.
- Produces: `SiblingClassification`, containing the four stored types plus `shared_father_unknown_mother` and `shared_mother_unknown_father`.
- Produces: immutable `RelationshipFact(source_id, target_id, kind, direction, sibling_type, origin, path_person_ids, relationship_ids, conflicting)`.
- Produces: `effective_relationships(people, relationships, source_id) -> list[RelationshipFact]`.
- Updates: `find_relationship_path(..., include_inferred: bool = True) -> KinshipResult | None` to expose origin and conflict state.

- [ ] **Step 1: Write a failing inference matrix**

Create `backend/tests/test_relationship_inference.py` with local `Person` and `Relationship` dataclasses. Start with parent propagation:

```python
def test_full_sibling_inherits_both_known_parents():
    people = [
        Person("hao", "贺志豪", "male"), Person("lan", "贺志兰", "female"),
        Person("father", "贺万彬", "male"), Person("mother", "王录飞", "female"),
    ]
    relationships = [
        Relationship("s", "sibling", "hao", "lan", "full"),
        Relationship("f", "parent", "hao", "father"),
        Relationship("m", "parent", "hao", "mother"),
    ]
    actual = {
        fact.target_id for fact in effective_relationships(people, relationships, "lan")
        if fact.kind == "parent" and fact.origin == "inferred"
    }
    assert actual == {"father", "mother"}


@pytest.mark.parametrize(
    ("sibling_type", "expected"),
    [("paternal_half", {"father"}), ("maternal_half", {"mother"}), ("unknown", set())],
)
def test_sibling_type_limits_parent_inheritance(sibling_type, expected):
    facts = effective_relationships(people_fixture, relationships_for(sibling_type), "lan")
    actual = {fact.target_id for fact in facts if fact.kind == "parent" and fact.origin == "inferred"}
    assert actual == expected
```

Define `people_fixture` and `relationships_for` in the same test file with the four people and three relationships shown by the first test. Add separate tests for:

- same known father and mother → `full`;
- common father plus two known different mothers → `paternal_half`;
- common mother plus two known different fathers → `maternal_half`;
- common father with either mother missing → `shared_father_unknown_mother`;
- common mother with either father missing → `shared_mother_unknown_father`;
- inferred parent differs from the target's direct same-gender parent → `conflicting is True` and input rows remain unchanged;
- spouse appears from both directions with `origin == "direct"`;
- father → paternal grandparent → uncle → child derives `paternal_cousin`.

- [ ] **Step 2: Run the tests and verify import failure**

```bash
python -m pytest backend/tests/test_relationship_inference.py -q
```

Expected: collection fails because `relationship_inference` does not exist.

- [ ] **Step 3: Implement immutable effective facts**

Create these definitions:

```python
RelationshipOrigin = Literal["direct", "inferred"]
SiblingClassification = Literal[
    "full", "paternal_half", "maternal_half", "unknown",
    "shared_father_unknown_mother", "shared_mother_unknown_father",
]


@dataclass(frozen=True)
class RelationshipFact:
    source_id: str
    target_id: str
    kind: str
    direction: Literal["up", "down", "same"]
    sibling_type: SiblingClassification | None
    origin: RelationshipOrigin
    path_person_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    conflicting: bool = False
```

Implement `effective_relationships` as a pure function:

1. Index people by ID and direct parents by child and parent gender.
2. For every parent row incident to `source_id`, emit `direction="up"` when the source is the child and `direction="down"` when the source is the parent.
3. For each spouse, sibling, or paternal-cousin row incident to `source_id`, emit the other endpoint with `direction="same"` and `origin="direct"`. Calling the function for either endpoint therefore gives a bidirectional view without duplicating stored rows.
4. Propagate only the permitted parent gender through a direct sibling subtype; include both direct relationship IDs in the evidence path.
5. Mark a proposed parent conflicting when the target already has a different direct parent of the same known gender.
6. Compare pairs using known direct parents to derive sibling classifications; never call a one-parent match full or half when the other parent is missing.
7. Derive paternal cousins only through a male first parent and a shared paternal grandparent.
8. Deduplicate by `(source_id, target_id, kind, direction, sibling_type, origin)` and sort by target name, kind, and subtype.

Generated facts are not persisted and do not feed another inference pass.

- [ ] **Step 4: Make kinship paths consume effective facts**

Extend `KinshipResult` with `origin: RelationshipOrigin` and `conflicting: bool`. With `include_inferred=True`, traverse effective facts and preserve every actual relationship ID. A path is inferred if any edge is inferred and conflicting if any edge conflicts. Keep `include_inferred=False` for direct-only diagnostics.

Add labels `兄弟姊妹（同父，母系不详）` and `兄弟姊妹（同母，父系不详）`; do not infer age-based seniority.

- [ ] **Step 5: Run domain and full backend suites**

```bash
python -m pytest backend/tests/test_relationship_inference.py backend/tests/test_kinship.py -q
python -m pytest backend/tests -q
```

Expected: inference matrix and all existing kinship behavior pass.

- [ ] **Step 6: Commit Task 2**

```bash
git add backend/app/domain/relationship_inference.py backend/app/domain/kinship.py backend/tests/test_relationship_inference.py backend/tests/test_kinship.py
git commit -m "feat: derive trustworthy family relationships"
```

---

### Task 3: Expose a Bounded Person-Centered Network API

**Files:**
- Create: `backend/app/services/relationship_network.py`
- Create: `backend/tests/test_relationship_network.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/genealogy.py`

**Interfaces:**
- Produces: `GET /api/genealogy/network?center_id=<id>&generations=2`.
- Accepts: repeatable `kind` filters and optional `verification_status`.
- Produces: `RelationshipNetworkResponse(center_id, nodes, edges)`.
- Produces: edge origin, path IDs, relationship IDs, conflict flag, sources, and status.

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_relationship_network.py`. Build a full-sibling case where only one sibling has parents, link a source to the sibling relationship, and request the other sibling as center:

```python
response = client.get(
    "/api/genealogy/network",
    params={"center_id": lan["id"], "generations": 2},
)
assert response.status_code == 200
body = response.json()
assert body["center_id"] == lan["id"]
assert {node["name"] for node in body["nodes"]} >= {"贺志兰", "贺万彬", "王录飞"}
inferred = [edge for edge in body["edges"] if edge["origin"] == "inferred"]
assert {edge["label"] for edge in inferred} >= {"父亲", "母亲"}
assert all(sibling["id"] in edge["relationship_ids"] for edge in inferred)
```

Add tests that `generations=0` and `5` return 422, an unknown center returns 404, same-generation relations do not consume a generation, parent/child traversal is bounded, kind/status filters remove unrelated edges and orphan nodes, and unrelated sources between the same endpoints are excluded.

- [ ] **Step 2: Run tests and verify the route is absent**

```bash
python -m pytest backend/tests/test_relationship_network.py -q
```

Expected: failures because the route, schemas, and service do not exist.

- [ ] **Step 3: Add network response schemas**

```python
class NetworkNodeResponse(BaseModel):
    id: str
    name: str
    gender: Gender
    birth_date: str | None
    death_date: str | None
    generation_offset: int
    verification_status: VerificationStatus


class NetworkEdgeResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    kind: Literal["parent", "spouse", "sibling", "paternal_cousin"]
    direction: Literal["up", "down", "same"]
    sibling_type: str | None
    label: str
    origin: Literal["direct", "inferred"]
    path_person_ids: list[str]
    relationship_ids: list[str]
    conflicting: bool
    verification_status: VerificationStatus
    sources: list[SourceCitation]


class RelationshipNetworkResponse(BaseModel):
    center_id: str
    nodes: list[NetworkNodeResponse]
    edges: list[NetworkEdgeResponse]
```

- [ ] **Step 4: Implement the bounded service**

Expose this signature in `relationship_network.py`:

```python
def build_relationship_network(
    db: Session,
    center_id: str,
    generations: int,
    kinds: set[str] | None,
    verification_status: str | None,
) -> RelationshipNetworkResponse:
```

Implementation sequence:

1. Load the center or raise `EntityNotFound("人物不存在")`.
2. Load people and direct relationships once; call `effective_relationships` for reached people.
3. Traverse `direction="up"` as `+1`, `down` as `-1`, and `same` as `0`; reject absolute offsets beyond the limit.
4. Track `(person_id, generation_offset)` for traversal and deduplicate response nodes by ID.
5. Apply kind/status filters before final node collection and always retain the center.
6. Fetch sources only for final edge relationship IDs; never match by unordered endpoint pair.
7. Set status conflicting if the fact or any source conflicts, verified only when every traversed direct relationship and source is verified, otherwise unverified.
8. Use stored IDs for direct edges and `inferred:<source>:<target>:<kind>:<subtype>` for inferred IDs.

- [ ] **Step 5: Add the authenticated route**

```python
@router.get("/api/genealogy/network", response_model=RelationshipNetworkResponse)
def relationship_network(
    center_id: str,
    db: DbSession,
    _: CurrentSession,
    generations: int = Query(default=2, ge=1, le=4),
    kind: list[str] | None = Query(default=None),
    verification_status: VerificationStatus | None = None,
):
    return build_relationship_network(
        db, center_id, generations, set(kind) if kind else None, verification_status
    )
```

Catch `EntityNotFound` with the existing error handler. Validate every kind against the four supported kinds and return 422 for invalid filters.

- [ ] **Step 6: Run network and full backend tests**

```bash
python -m pytest backend/tests/test_relationship_network.py -q
python -m pytest backend/tests -q
```

Expected: all pass and querying the network does not increase the database relationship count.

- [ ] **Step 7: Commit Task 3**

```bash
git add backend/app/services/relationship_network.py backend/app/schemas.py backend/app/api/genealogy.py backend/tests/test_relationship_network.py
git commit -m "feat: add person-centered relationship network API"
```

---

### Task 4: Make Agent Answers Use Inferred Facts and Spouse Aliases

**Files:**
- Modify: `backend/app/agent/orchestrator.py`
- Modify: `backend/app/agent/client.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/tests/test_agent.py`

**Interfaces:**
- Consumes: `effective_relationships` and inferred-aware `find_relationship_path` from Task 2.
- Produces: local aliases `对象`, `爱人`, `配偶`, `丈夫`, and `妻子` → `spouses`.
- Produces: `KinshipResponse.origin`, `conflicting`, relationship IDs, and path.
- Preserves: complex questions still fall back to the configured model client.

- [ ] **Step 1: Write failing parent-propagation and reverse-spouse tests**

Add to `backend/tests/test_agent.py`:

```python
def test_full_sibling_parent_lookup_returns_inferred_parents(tmp_path):
    with agent_client(tmp_path, {"kind": "unexpected"}) as (client, model):
        hao = add_person(client, "贺志豪", "male")
        lan = add_person(client, "贺志兰", "female")
        father = add_person(client, "贺万彬", "male")
        mother = add_person(client, "王录飞", "female")
        client.post("/api/relationships", json={
            "kind": "sibling", "sibling_type": "full",
            "person_id": hao["id"], "relative_id": lan["id"],
        })
        for parent in (father, mother):
            client.post("/api/relationships", json={
                "kind": "parent", "person_id": hao["id"], "relative_id": parent["id"],
            })
        response = client.post("/api/agent/query", json={"message": "贺志兰的父母是谁"})
    assert response.status_code == 200
    assert "贺万彬、王录飞" in response.json()["answer"]
    assert all(item["origin"] == "inferred" for item in response.json()["relationships"])
    assert model.messages == []


@pytest.mark.parametrize("alias", ["对象", "爱人", "配偶", "丈夫", "妻子"])
def test_spouse_alias_lookup_is_bidirectional(tmp_path, alias):
    with agent_client(tmp_path, {"kind": "unexpected"}) as (client, model):
        hao = add_person(client, "贺志豪", "male")
        yingla = add_person(client, "管应拉", "female")
        client.post("/api/relationships", json={
            "kind": "spouse", "person_id": hao["id"], "relative_id": yingla["id"],
        })
        response = client.post("/api/agent/query", json={"message": f"管应拉的{alias}是谁"})
    assert response.status_code == 200
    assert "贺志豪" in response.json()["answer"]
    assert response.json()["relationships"][0]["origin"] == "direct"
    assert model.messages == []
```

Add a conflict test where the sibling's direct father differs from the inferred father. Assert status `conflicting`, both names are visible, and a subsequent `GET /api/relationships` returns the unchanged direct rows.

- [ ] **Step 2: Run agent tests and verify the red state**

```bash
python -m pytest backend/tests/test_agent.py -q
```

Expected: aliases miss local parsing, inferred parents are absent, and origin fields are missing.

- [ ] **Step 3: Route deterministic lookups through effective facts**

Extend `LOOKUP_LABELS` with all five spouse terms. Replace the current loop that runs `find_relationship_path` against every person with one call to `effective_relationships(people, relationships, source_person.id)`, filtered by requested relation type.

Map facts to `KinshipResponse` without asking the model to restate facts. Filter parents/children using `direction`, then include origin, conflict state, actual relationship IDs, and steps from `path_person_ids`. Aggregate sources only from those relationship IDs.

For conflicts, return direct and inferred candidates, set `verification_status="conflicting"`, and include `现有直接记录与系统推导不一致，请核实。` Never choose one candidate as correct.

- [ ] **Step 4: Align the model parser prompt**

Tell the hosted-model parser that `对象`, `爱人`, `丈夫`, and `妻子` resolve to `relation_type="spouses"`. Preserve Pydantic validation and the existing 502 response for malformed model output.

- [ ] **Step 5: Run agent and full backend tests**

```bash
python -m pytest backend/tests/test_agent.py -q
python -m pytest backend/tests -q
```

Expected: direct lookups remain green, propagated parents are inferred, reverse spouse aliases work, and conflict text is explicit.

- [ ] **Step 6: Commit Task 4**

```bash
git add backend/app/agent/orchestrator.py backend/app/agent/client.py backend/app/schemas.py backend/tests/test_agent.py
git commit -m "feat: answer inferred family relationship queries"
```

---

### Task 5: Extend Person and Relationship Maintenance Forms

**Files:**
- Modify: `src/types.ts`
- Modify: `src/api.ts`
- Modify: `src/components/PersonEditor.tsx`
- Modify: `src/App.tsx`
- Modify: `src/App.test.tsx`
- Modify: `src/styles.css`

**Interfaces:**
- Consumes: Task 1 person fields and `sibling_type` contracts.
- Produces: preset person inputs and a conditional sibling subtype selector.
- Preserves: relationship writes use the authenticated `POST /api/relationships` flow.

- [ ] **Step 1: Add failing frontend form tests**

Using the existing authenticated fetch mock in `src/App.test.tsx`, add one test that opens “新增成员”, fills `出生地`, `字`, `号`, `曾用名或乳名`, `字辈`, `家庭排行`, and `职业`, submits, and inspects the JSON request body:

```typescript
const createCall = fetchMock.mock.calls.find(([input, init]) =>
  String(input).endsWith('/api/persons') && init?.method === 'POST'
)
expect(JSON.parse(String(createCall![1]!.body))).toMatchObject({
  birth_place: '湖南衡阳',
  courtesy_name: '守成',
  generation_name: '志',
  occupation: '教师',
})
```

Add a second test that selects relationship kind `sibling`, verifies the conditional selector, chooses `paternal_half`, submits, and asserts the relationship body contains `"sibling_type":"paternal_half"`.

- [ ] **Step 2: Run frontend tests and verify missing controls**

```bash
npm test -- --run src/App.test.tsx
```

Expected: queries for the new labels and sibling subtype fail.

- [ ] **Step 3: Extend frontend contracts**

Add the seven optional person fields and:

```typescript
export type SiblingType = 'full' | 'paternal_half' | 'maternal_half' | 'unknown'

export type Relationship = {
  id: string
  kind: 'parent' | 'spouse' | 'sibling' | 'paternal_cousin'
  sibling_type: SiblingType | null
  person_id: string
  relative_id: string
  verification_status: VerificationStatus
  created_at: string
}
```

Change `api.createRelationship` to accept the three current identifiers plus optional `sibling_type`.

- [ ] **Step 4: Add preset controls and subtype selection**

Add labeled controls to `PersonEditor` for death date, birth place, courtesy name, art name, aliases, generation name, family rank, and occupation. Include each field in create/update payloads; empty values become `null`.

In `FamilyTree`, store `siblingType` with default `unknown` and render only for `kind === 'sibling'`:

```tsx
<label>
  兄弟姊妹类型
  <select
    aria-label="兄弟姊妹类型"
    value={siblingType}
    onChange={(event) => setSiblingType(event.target.value as SiblingType)}
  >
    <option value="full">同父同母</option>
    <option value="paternal_half">同父异母</option>
    <option value="maternal_half">同母异父</option>
    <option value="unknown">关系不详</option>
  </select>
</label>
```

Send subtype only for siblings and include its Chinese label in `relationshipDescription`.

- [ ] **Step 5: Run frontend and backend contract tests**

```bash
npm test
npm run build
python -m pytest backend/tests/test_genealogy_api.py -q
```

Expected: frontend tests, TypeScript checks, production build, and API tests pass.

- [ ] **Step 6: Commit Task 5**

```bash
git add src/types.ts src/api.ts src/components/PersonEditor.tsx src/App.tsx src/App.test.tsx src/styles.css
git commit -m "feat: edit genealogy attributes and sibling types"
```

---

### Task 6: Render the Read-Only Person-Centered React Flow Network

**Files:**
- Create: `src/features/family-network/layout.ts`
- Create: `src/features/family-network/layout.test.ts`
- Create: `src/features/family-network/FamilyNetwork.tsx`
- Create: `src/features/family-network/FamilyNetwork.test.tsx`
- Create: `src/features/family-network/PersonDetailPanel.tsx`
- Modify: `src/types.ts`
- Modify: `src/api.ts`
- Modify: `src/App.tsx`
- Modify: `src/styles.css`
- Modify: `package.json`
- Modify: `package-lock.json`

**Interfaces:**
- Consumes: `GET /api/genealogy/network` from Task 3.
- Produces: `api.relationshipNetwork(centerId, generations, kinds, status)`.
- Produces: `<FamilyNetwork people onEdit />` with no canvas mutation.
- Produces: `layoutNetwork(network: RelationshipNetwork) -> { nodes: Node[]; edges: Edge[] }`.

- [ ] **Step 1: Install React Flow and capture its lockfile change**

```bash
npm install @xyflow/react
```

Expected: dependency sections in `package.json` and `package-lock.json` change; no other source changes.

- [ ] **Step 2: Write failing deterministic layout tests**

Create a fixture containing center, father, spouse, sibling, and child. In `layout.test.ts` assert:

```typescript
const result = layoutNetwork(networkFixture)
const positions = new Map(result.nodes.map((node) => [node.id, node.position]))
expect(positions.get('father')!.y).toBeLessThan(positions.get('center')!.y)
expect(positions.get('spouse')!.y).toBe(positions.get('center')!.y)
expect(positions.get('child')!.y).toBeGreaterThan(positions.get('center')!.y)
const inferred = result.edges.find((edge) => edge.id === 'inferred-parent')!
expect(inferred.className).toContain('inferred')
expect(inferred.animated).toBe(false)
```

- [ ] **Step 3: Write failing component interaction tests**

In `FamilyNetwork.test.tsx`, mock `@xyflow/react` as an accessible list so jsdom does not need geometry. Verify:

- the first person becomes initial center;
- search selection requests the network by stable person ID;
- clicking a node reloads it as center;
- generation values are limited to 1–4;
- relation/status filters modify the request;
- direct edges expose `aria-label="直接关系：配偶"`;
- inferred edges expose `aria-label="系统推导：父亲"`;
- the detail panel separates attributes, direct relations, inferred relations, and sources;
- “编辑人物” calls `onEdit`, while inferred rows have no write action;
- API failure retains the center and exposes a retry button.

- [ ] **Step 4: Run new frontend tests and verify imports fail**

```bash
npm test -- --run src/features/family-network/layout.test.ts src/features/family-network/FamilyNetwork.test.tsx
```

Expected: feature module and network type imports fail.

- [ ] **Step 5: Add frontend network contracts and client method**

Mirror Task 3 schemas:

```typescript
export type NetworkEdge = {
  id: string
  source_id: string
  target_id: string
  kind: Relationship['kind']
  direction: 'up' | 'down' | 'same'
  sibling_type: string | null
  label: string
  origin: 'direct' | 'inferred'
  path_person_ids: string[]
  relationship_ids: string[]
  conflicting: boolean
  verification_status: VerificationStatus
  sources: Array<Pick<Source, 'id' | 'title' | 'verification_status'>>
}

export type RelationshipNetwork = {
  center_id: string
  nodes: Array<Pick<Person, 'id' | 'name' | 'gender' | 'birth_date' | 'death_date' | 'verification_status'> & { generation_offset: number }>
  edges: NetworkEdge[]
}
```

In `api.relationshipNetwork`, build `URLSearchParams`, append every selected kind, and omit empty filters.

- [ ] **Step 6: Implement layout without another dependency**

Group nodes by `generation_offset`. Put center at `(0, 0)`, positive offsets above, negative offsets below, and same-generation spouse/sibling nodes at alternating left/right positions. Use 220 px vertical and 180 px horizontal spacing. Give direct edges class `network-edge direct`, inferred edges `network-edge inferred`, and add `conflicting` when required.

- [ ] **Step 7: Implement canvas and detail panel**

`FamilyNetwork.tsx` must choose `people[0]?.id` only when no center is selected, request data on center/filter changes, import `@xyflow/react/dist/style.css`, and render `ReactFlow`, `Background`, `Controls`, search, generation, relation, and status controls.

Disable node connections and canvas-created edges. Node click calls `setCenterId(node.id)`. Add a legend containing both line styles and text.

`PersonDetailPanel.tsx` receives the selected `Person`, incident edges, and `onEdit`. It separates direct and inferred lists, prints conflict warnings independently of color, and links sources through `/api/sources/{id}/download`.

- [ ] **Step 8: Compose into the existing family page**

Keep relationship maintenance in `FamilyTree`; place `<FamilyNetwork>` above it and retain the people directory as the no-center fallback. Pass existing `onEdit` rather than duplicating person state.

At `max-width: 760px`, render detail as a bottom drawer below the 61 px top bar and above the 65 px mobile navigation. A visible close button restores full canvas access.

- [ ] **Step 9: Run frontend tests and build**

```bash
npm test
npm run build
```

Expected: layout, component, existing application tests, TypeScript checks, and Vite build pass.

- [ ] **Step 10: Commit Task 6**

```bash
git add package.json package-lock.json src/types.ts src/api.ts src/App.tsx src/styles.css src/features/family-network
git commit -m "feat: add interactive family relationship network"
```

---

### Task 7: Complete Browser Acceptance, Documentation, and Release Verification

**Files:**
- Modify: `backend/tests/e2e_app.py`
- Modify: `e2e/family-agent.spec.ts`
- Modify: `README.md`
- Modify: `docs/technical-design.md`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: browser proof of parent propagation, reverse spouse lookup, network navigation, direct/inferred styling, and mobile detail behavior.

- [ ] **Step 1: Extend the browser acceptance flow**

Update the current E2E flow to create four uniquely suffixed people: a primary person, full sibling, father, and spouse. Through the UI:

1. Create a `full` sibling relationship.
2. Create a parent relationship only for the primary person.
3. Create a spouse relationship in primary-person → spouse direction.
4. Ask for the sibling's parents and assert the parent plus “系统推导”.
5. Ask for the spouse's “对象” and assert the primary person's name.
6. Open the family network centered on the sibling.
7. Assert `系统推导：父亲`, `直接关系：配偶`, and right-side details.
8. Click the parent and assert it becomes center.
9. Resize to `390x844`, select a person, and assert the bottom drawer is visible without horizontal overflow.

Use role/name locators rather than CSS selectors so the flow also verifies accessibility labels.

- [ ] **Step 2: Run browser acceptance**

On Windows, use the project interpreter and installed Edge:

```powershell
$env:E2E_API_COMMAND='.\.venv\Scripts\python.exe -m uvicorn backend.tests.e2e_app:app --host 127.0.0.1 --port 8000'
$env:PLAYWRIGHT_EXECUTABLE_PATH='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
npm run test:e2e
```

Expected: one complete flow passes with no browser console errors.

- [ ] **Step 3: Update product documentation**

Update README's feature list and test instructions. Update `docs/technical-design.md` so sibling subtypes, deterministic inference, network endpoint, React Flow, direct/inferred distinction, and the PostgreSQL-only decision match the spec. Do not list Neo4j as a dependency.

- [ ] **Step 4: Run complete verification from fresh processes**

```bash
npm test
python -m pytest backend/tests -q
npm run build
```

Run the Windows E2E command from Step 2 again, then:

```bash
git diff --check
git status --short
```

Expected: zero test failures, successful build, no diff-check output, and `.idea/` as the only unrelated untracked path.

- [ ] **Step 5: Review against the approved spec**

Confirm no inferred relationship is inserted, old sibling rows remain `unknown`, network requests are bounded, conflict states are visible, and no canvas gesture writes data. Fix every Critical or Important review finding and repeat affected tests.

- [ ] **Step 6: Commit Task 7**

```bash
git add backend/tests/e2e_app.py e2e/family-agent.spec.ts README.md docs/technical-design.md
git commit -m "test: cover inferred relationships and family network"
```

- [ ] **Step 7: Push and verify remote synchronization**

```bash
git push ssh://git@ssh.github.com:443/hezhihaolala/agent.git main:main
git fetch ssh://git@ssh.github.com:443/hezhihaolala/agent.git main:refs/remotes/origin/main
git rev-list --left-right --count main...origin/main
```

Expected: final output is `0 0`.

## Completion Criteria

- Existing data upgrades without loss; old sibling rows become `unknown`.
- Preset person fields create, edit, return, and display correctly.
- Full, paternal-half, maternal-half, unknown, and partial-known sibling states follow approved rules.
- Full siblings can inherit both parents for queries without persisting new parent rows.
- Spouse lookup is bidirectional for all approved Chinese aliases.
- Conflicts preserve direct facts and remain visible in API, agent answer, and network UI.
- The two-generation network distinguishes direct and inferred edges and supports center switching.
- Desktop detail panel and mobile bottom drawer are usable and tested.
- Backend, frontend, build, migration, and browser suites pass.
- Every task has its own commit and remote `main` is synchronized.
