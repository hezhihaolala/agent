from dataclasses import dataclass, replace
from typing import Any, Iterable, Literal


RelationshipOrigin = Literal["direct", "inferred"]
SiblingClassification = Literal[
    "full",
    "paternal_half",
    "maternal_half",
    "unknown",
    "shared_father_unknown_mother",
    "shared_mother_unknown_father",
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


def _value(item: Any, name: str) -> Any:
    return item[name] if isinstance(item, dict) else getattr(item, name)


def _optional_value(item: Any, name: str) -> Any | None:
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


def _relationship_ids(*items: Any) -> tuple[str, ...]:
    return tuple(
        relationship_id
        for item in items
        if (relationship_id := _optional_value(item, "id")) is not None
    )


def effective_relationships(
    people: Iterable[Any], relationships: Iterable[Any], source_id: str
) -> list[RelationshipFact]:
    person_map = {_value(person, "id"): person for person in people}
    if source_id not in person_map:
        return []

    direct_relationships = tuple(relationships)
    parent_rows: dict[str, dict[str, list[Any]]] = {}
    for relationship in direct_relationships:
        if _value(relationship, "kind") != "parent":
            continue
        child_id = _value(relationship, "person_id")
        parent_id = _value(relationship, "relative_id")
        if child_id not in person_map or parent_id not in person_map:
            continue
        gender = _value(person_map[parent_id], "gender")
        parent_rows.setdefault(child_id, {}).setdefault(gender, []).append(
            relationship
        )

    facts: list[RelationshipFact] = []
    for relationship in direct_relationships:
        person_id = _value(relationship, "person_id")
        relative_id = _value(relationship, "relative_id")
        if person_id not in person_map or relative_id not in person_map:
            continue
        kind = _value(relationship, "kind")
        target_id: str | None = None
        direction: Literal["up", "down", "same"] | None = None
        if kind == "parent":
            if source_id == person_id:
                target_id, direction = relative_id, "up"
            elif source_id == relative_id:
                target_id, direction = person_id, "down"
        elif kind in {"spouse", "sibling", "paternal_cousin"}:
            if source_id == person_id:
                target_id, direction = relative_id, "same"
            elif source_id == relative_id:
                target_id, direction = person_id, "same"
        if target_id is None or direction is None:
            continue
        facts.append(
            RelationshipFact(
                source_id=source_id,
                target_id=target_id,
                kind=kind,
                direction=direction,
                sibling_type=(
                    _optional_value(relationship, "sibling_type") or "unknown"
                    if kind == "sibling"
                    else None
                ),
                origin="direct",
                path_person_ids=(source_id, target_id),
                relationship_ids=_relationship_ids(relationship),
                conflicting=(
                    kind == "parent"
                    and _value(person_map[relative_id], "gender")
                    in {"male", "female"}
                    and len(
                        parent_rows.get(person_id, {}).get(
                            _value(person_map[relative_id], "gender"), []
                        )
                    )
                    > 1
                ),
            )
        )

    _infer_parents_from_siblings(
        facts, direct_relationships, parent_rows, source_id
    )
    _infer_siblings_from_parents(facts, person_map, parent_rows, source_id)
    _infer_paternal_cousins(facts, person_map, parent_rows, source_id)
    facts = _mark_sibling_disagreements(facts)

    deduplicated: dict[
        tuple[str, str, str, str, str | None, str], RelationshipFact
    ] = {}
    for fact in facts:
        key = (
            fact.source_id,
            fact.target_id,
            fact.kind,
            fact.direction,
            fact.sibling_type,
            fact.origin,
        )
        previous = deduplicated.get(key)
        if previous is None or (fact.conflicting and not previous.conflicting):
            deduplicated[key] = fact

    return sorted(
        deduplicated.values(),
        key=lambda fact: (
            _value(person_map[fact.target_id], "name"),
            fact.kind,
            fact.sibling_type or "",
            0 if fact.origin == "direct" else 1,
        ),
    )


def _infer_parents_from_siblings(
    facts: list[RelationshipFact],
    relationships: tuple[Any, ...],
    parent_rows: dict[str, dict[str, list[Any]]],
    source_id: str,
) -> None:
    allowed_genders = {
        "full": {"male", "female"},
        "paternal_half": {"male"},
        "maternal_half": {"female"},
        "unknown": set(),
    }
    for sibling in relationships:
        if _value(sibling, "kind") != "sibling":
            continue
        person_id = _value(sibling, "person_id")
        relative_id = _value(sibling, "relative_id")
        if source_id == person_id:
            sibling_id = relative_id
        elif source_id == relative_id:
            sibling_id = person_id
        else:
            continue
        sibling_type = _optional_value(sibling, "sibling_type") or "unknown"
        for gender in allowed_genders.get(sibling_type, set()):
            existing_parent_ids = {
                _value(row, "relative_id")
                for row in parent_rows.get(source_id, {}).get(gender, [])
            }
            for parent_relationship in parent_rows.get(sibling_id, {}).get(gender, []):
                parent_id = _value(parent_relationship, "relative_id")
                if parent_id in existing_parent_ids:
                    continue
                facts.append(
                    RelationshipFact(
                        source_id=source_id,
                        target_id=parent_id,
                        kind="parent",
                        direction="up",
                        sibling_type=None,
                        origin="inferred",
                        path_person_ids=(source_id, sibling_id, parent_id),
                        relationship_ids=_relationship_ids(
                            sibling, parent_relationship
                        ),
                        conflicting=(
                            bool(existing_parent_ids)
                            or len(parent_rows.get(sibling_id, {}).get(gender, [])) > 1
                        ),
                    )
                )


def _infer_siblings_from_parents(
    facts: list[RelationshipFact],
    person_map: dict[str, Any],
    parent_rows: dict[str, dict[str, list[Any]]],
    source_id: str,
) -> None:
    source_parents = parent_rows.get(source_id, {})
    for candidate_id in person_map:
        if candidate_id == source_id:
            continue
        candidate_parents = parent_rows.get(candidate_id, {})
        classification = _classify_siblings(source_parents, candidate_parents)
        if classification is None:
            continue
        evidence = _sibling_evidence(
            source_parents, candidate_parents, classification
        )
        facts.append(
            RelationshipFact(
                source_id=source_id,
                target_id=candidate_id,
                kind="sibling",
                direction="same",
                sibling_type=classification,
                origin="inferred",
                path_person_ids=(
                    source_id,
                    _value(evidence[0], "relative_id"),
                    candidate_id,
                ),
                relationship_ids=_relationship_ids(*evidence),
                conflicting=any(
                    len(source_parents.get(gender, [])) > 1
                    or len(candidate_parents.get(gender, [])) > 1
                    for gender in ("male", "female")
                ),
            )
        )


def _classify_siblings(
    first: dict[str, list[Any]], second: dict[str, list[Any]]
) -> SiblingClassification | None:
    first_fathers = {_value(row, "relative_id") for row in first.get("male", [])}
    second_fathers = {_value(row, "relative_id") for row in second.get("male", [])}
    first_mothers = {_value(row, "relative_id") for row in first.get("female", [])}
    second_mothers = {_value(row, "relative_id") for row in second.get("female", [])}
    shared_father = bool(first_fathers & second_fathers)
    shared_mother = bool(first_mothers & second_mothers)

    if shared_father and shared_mother:
        return "full"
    if shared_father and first_mothers and second_mothers:
        return "paternal_half"
    if shared_mother and first_fathers and second_fathers:
        return "maternal_half"
    if shared_father and (not first_mothers or not second_mothers):
        return "shared_father_unknown_mother"
    if shared_mother and (not first_fathers or not second_fathers):
        return "shared_mother_unknown_father"
    return None


def _sibling_evidence(
    first: dict[str, list[Any]],
    second: dict[str, list[Any]],
    classification: SiblingClassification,
) -> tuple[Any, ...]:
    shared_genders = (
        ("male", "female")
        if classification == "full"
        else ("female",)
        if classification in {"maternal_half", "shared_mother_unknown_father"}
        else ("male",)
    )
    evidence: list[Any] = []
    for gender in shared_genders:
        first_by_parent = {
            _value(row, "relative_id"): row for row in first.get(gender, [])
        }
        second_by_parent = {
            _value(row, "relative_id"): row for row in second.get(gender, [])
        }
        for parent_id in sorted(first_by_parent.keys() & second_by_parent.keys()):
            evidence.extend((first_by_parent[parent_id], second_by_parent[parent_id]))
            break
    differing_gender = (
        "female"
        if classification == "paternal_half"
        else "male"
        if classification == "maternal_half"
        else None
    )
    if differing_gender is not None:
        evidence.extend(
            sorted(
                first.get(differing_gender, []),
                key=lambda row: _value(row, "relative_id"),
            )
        )
        evidence.extend(
            sorted(
                second.get(differing_gender, []),
                key=lambda row: _value(row, "relative_id"),
            )
        )
    return tuple(evidence)


def _infer_paternal_cousins(
    facts: list[RelationshipFact],
    person_map: dict[str, Any],
    parent_rows: dict[str, dict[str, list[Any]]],
    source_id: str,
) -> None:
    for source_father_row in parent_rows.get(source_id, {}).get("male", []):
        father_id = _value(source_father_row, "relative_id")
        for grandparent_rows in parent_rows.get(father_id, {}).values():
            for father_grandparent_row in grandparent_rows:
                grandparent_id = _value(father_grandparent_row, "relative_id")
                for uncle_id, uncle_parents in parent_rows.items():
                    if (
                        uncle_id == father_id
                        or _value(person_map[uncle_id], "gender") != "male"
                    ):
                        continue
                    shared_rows = [
                        row
                        for rows in uncle_parents.values()
                        for row in rows
                        if _value(row, "relative_id") == grandparent_id
                    ]
                    for uncle_grandparent_row in shared_rows:
                        for cousin_id, cousin_parents in parent_rows.items():
                            if cousin_id == source_id:
                                continue
                            for cousin_parent_row in cousin_parents.get("male", []):
                                if _value(cousin_parent_row, "relative_id") != uncle_id:
                                    continue
                                facts.append(
                                    RelationshipFact(
                                        source_id=source_id,
                                        target_id=cousin_id,
                                        kind="paternal_cousin",
                                        direction="same",
                                        sibling_type=None,
                                        origin="inferred",
                                        path_person_ids=(
                                            source_id,
                                            father_id,
                                            grandparent_id,
                                            uncle_id,
                                            cousin_id,
                                        ),
                                        relationship_ids=_relationship_ids(
                                            source_father_row,
                                            father_grandparent_row,
                                            uncle_grandparent_row,
                                            cousin_parent_row,
                                        ),
                                    )
                                )


def _mark_sibling_disagreements(
    facts: list[RelationshipFact],
) -> list[RelationshipFact]:
    direct_types = {
        fact.target_id: fact.sibling_type
        for fact in facts
        if fact.kind == "sibling"
        and fact.origin == "direct"
        and fact.sibling_type != "unknown"
    }
    inferred_types = {
        fact.target_id: fact.sibling_type
        for fact in facts
        if fact.kind == "sibling" and fact.origin == "inferred"
    }
    conflicts = {
        target_id
        for target_id in direct_types.keys() & inferred_types.keys()
        if direct_types[target_id] != inferred_types[target_id]
    }
    return [
        replace(fact, conflicting=True)
        if fact.kind == "sibling" and fact.target_id in conflicts
        else fact
        for fact in facts
    ]
