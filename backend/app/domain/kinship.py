from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class KinshipStep:
    person_id: str
    person_name: str


@dataclass(frozen=True)
class KinshipResult:
    label: str
    steps: list[KinshipStep]
    relationship_ids: list[str]


def _value(item: Any, name: str) -> Any:
    return item[name] if isinstance(item, dict) else getattr(item, name)


def _optional_value(item: Any, name: str) -> Any | None:
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


def _label(directions: list[str], path: list[str], people: dict[str, Any]) -> str:
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
) -> KinshipResult | None:
    person_map = {_value(person, "id"): person for person in people}
    if source_id not in person_map or target_id not in person_map:
        return None

    graph: dict[str, list[tuple[str, str, str | None]]] = {
        person_id: [] for person_id in person_map
    }
    for relationship in relationships:
        person_id = _value(relationship, "person_id")
        relative_id = _value(relationship, "relative_id")
        kind = _value(relationship, "kind")
        relationship_id = _optional_value(relationship, "id")
        if person_id not in graph or relative_id not in graph:
            continue
        if kind == "parent":
            graph[person_id].append((relative_id, "up", relationship_id))
            graph[relative_id].append((person_id, "down", relationship_id))
        elif kind == "spouse":
            graph[person_id].append((relative_id, "spouse", relationship_id))
            graph[relative_id].append((person_id, "spouse", relationship_id))
        elif kind in {"sibling", "paternal_cousin"}:
            graph[person_id].append((relative_id, kind, relationship_id))
            graph[relative_id].append((person_id, kind, relationship_id))

    queue = deque([(source_id, [source_id], [], [])])
    visited = {source_id}
    while queue:
        current, path, directions, relationship_ids = queue.popleft()
        if current == target_id:
            return KinshipResult(
                label=_label(directions, path, person_map),
                steps=[
                    KinshipStep(person_id=item, person_name=_value(person_map[item], "name"))
                    for item in path
                ],
                relationship_ids=[item for item in relationship_ids if item],
            )
        for neighbor, direction, relationship_id in graph[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(
                    (
                        neighbor,
                        [*path, neighbor],
                        [*directions, direction],
                        [*relationship_ids, relationship_id],
                    )
                )
    return None
