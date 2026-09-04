from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable

from .relationship_inference import (
    RelationshipFact,
    RelationshipOrigin,
    effective_relationships,
)


@dataclass(frozen=True)
class KinshipStep:
    person_id: str
    person_name: str


@dataclass(frozen=True)
class KinshipResult:
    label: str
    steps: list[KinshipStep]
    relationship_ids: list[str]
    origin: RelationshipOrigin
    conflicting: bool


def _value(item: Any, name: str) -> Any:
    return item[name] if isinstance(item, dict) else getattr(item, name)


def _label(
    directions: list[str],
    path: list[str],
    people: dict[str, Any],
    sibling_types: list[str | None],
) -> str:
    target = people[path[-1]]
    target_gender = _value(target, "gender")
    gendered = lambda male, female, fallback: (
        male if target_gender == "male" else female if target_gender == "female" else fallback
    )

    if not directions:
        return "本人"
    if directions == ["up"]:
        return gendered("父亲", "母亲", "父母")
    if directions == ["down"]:
        return gendered("儿子", "女儿", "子女")
    if directions == ["spouse"]:
        return gendered("丈夫", "妻子", "配偶")
    if directions == ["sibling"]:
        if sibling_types == ["shared_father_unknown_mother"]:
            return "兄弟姊妹（同父，母系不详）"
        if sibling_types == ["shared_mother_unknown_father"]:
            return "兄弟姊妹（同母，父系不详）"
        return gendered("兄弟", "姐妹", "兄弟姊妹")
    if directions == ["paternal_cousin"]:
        return gendered("堂兄弟", "堂姐妹", "堂兄弟姊妹")
    if directions == ["up", "up"]:
        first_parent = people[path[1]]
        if _value(first_parent, "gender") == "female":
            return gendered("外祖父", "外祖母", "外祖父母")
        return gendered("祖父", "祖母", "祖父母")
    if directions == ["up", "down"]:
        return gendered("兄弟", "姐妹", "兄弟姐妹")
    if directions == ["down", "down"]:
        return gendered("孙子", "孙女", "孙辈")
    if directions == ["up", "up", "down", "down"]:
        first_parent = people[path[1]]
        if _value(first_parent, "gender") == "male":
            return gendered("堂兄弟", "堂姐妹", "堂兄弟姊妹")
    if directions == ["spouse", "up"]:
        spouse_gender = _value(people[path[1]], "gender")
        if spouse_gender == "female":
            return gendered("岳父", "岳母", "岳父母")
        return gendered("公公", "婆婆", "公婆")
    return "亲属"


def find_relationship_path(
    people: Iterable[Any],
    relationships: Iterable[Any],
    source_id: str,
    target_id: str,
    include_inferred: bool = True,
) -> KinshipResult | None:
    person_map = {_value(person, "id"): person for person in people}
    if source_id not in person_map or target_id not in person_map:
        return None

    people_values = tuple(person_map.values())
    direct_relationships = tuple(relationships)
    graph: dict[str, list[RelationshipFact]] = {}
    for person_id in person_map:
        graph[person_id] = [
            fact
            for fact in effective_relationships(
                people_values, direct_relationships, person_id
            )
            if include_inferred or fact.origin == "direct"
        ]
        graph[person_id].sort(
            key=lambda fact: (
                0 if fact.origin == "direct" else 1,
                _value(person_map[fact.target_id], "name"),
                fact.kind,
                fact.sibling_type or "",
            )
        )

    queue = deque([(source_id, [source_id], [source_id], [], [], [], [], False)])
    visited = {source_id}
    while queue:
        (
            current,
            path,
            evidence_path,
            directions,
            sibling_types,
            origins,
            relationship_ids,
            conflicting,
        ) = queue.popleft()
        if current == target_id:
            return KinshipResult(
                label=_label(directions, path, person_map, sibling_types),
                steps=[
                    KinshipStep(person_id=item, person_name=_value(person_map[item], "name"))
                    for item in evidence_path
                ],
                relationship_ids=relationship_ids,
                origin="inferred" if "inferred" in origins else "direct",
                conflicting=conflicting,
            )
        for fact in graph[current]:
            if fact.target_id not in visited:
                visited.add(fact.target_id)
                direction = fact.direction if fact.kind == "parent" else fact.kind
                new_relationship_ids = list(relationship_ids)
                for relationship_id in fact.relationship_ids:
                    if relationship_id not in new_relationship_ids:
                        new_relationship_ids.append(relationship_id)
                queue.append(
                    (
                        fact.target_id,
                        [*path, fact.target_id],
                        [*evidence_path, *fact.path_person_ids[1:]],
                        [*directions, direction],
                        [*sibling_types, fact.sibling_type],
                        [*origins, fact.origin],
                        new_relationship_ids,
                        conflicting or fact.conflicting,
                    )
                )
    return None
