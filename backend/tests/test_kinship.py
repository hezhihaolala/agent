from dataclasses import dataclass


@dataclass
class Person:
    id: str
    name: str
    gender: str


@dataclass
class Relationship:
    kind: str
    person_id: str
    relative_id: str


def test_maternal_grandfather_path():
    try:
        from backend.app.domain.kinship import find_relationship_path
    except ModuleNotFoundError:
        find_relationship_path = None

    assert find_relationship_path is not None, "亲属关系引擎尚未实现"
    people = [
        Person("mingyuan", "张明远", "male"),
        Person("suzhen", "陈素贞", "female"),
        Person("shouyi", "陈守义", "male"),
    ]
    relationships = [
        Relationship("parent", "mingyuan", "suzhen"),
        Relationship("parent", "suzhen", "shouyi"),
    ]

    result = find_relationship_path(
        people, relationships, "mingyuan", "shouyi"
    )

    assert result is not None
    assert result.label == "外祖父"
    assert [step.person_name for step in result.steps] == [
        "张明远",
        "陈素贞",
        "陈守义",
    ]


def test_direct_and_sibling_labels_are_deterministic():
    try:
        from backend.app.domain.kinship import find_relationship_path
    except ModuleNotFoundError:
        find_relationship_path = None

    assert find_relationship_path is not None, "亲属关系引擎尚未实现"
    people = [
        Person("daughter", "女儿", "female"),
        Person("father", "父亲", "male"),
        Person("brother", "兄弟", "male"),
    ]
    relationships = [
        Relationship("parent", "daughter", "father"),
        Relationship("parent", "brother", "father"),
    ]

    parent = find_relationship_path(people, relationships, "daughter", "father")
    sibling = find_relationship_path(
        people, relationships, "daughter", "brother"
    )

    assert parent is not None and parent.label == "父亲"
    assert sibling is not None and sibling.label == "兄弟"
