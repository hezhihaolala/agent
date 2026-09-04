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
    id: str | None = None
    sibling_type: str | None = None


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
    assert sibling is not None
    assert sibling.label == "兄弟姊妹（同父，母系不详）"


def test_explicit_sibling_and_paternal_cousin_labels_use_target_gender():
    from backend.app.domain.kinship import find_relationship_path

    people = [
        Person("source", "贺志豪", "male"),
        Person("sister", "贺志兰", "female"),
        Person("cousin", "贺志梅", "female"),
    ]
    relationships = [
        Relationship("sibling", "source", "sister"),
        Relationship("paternal_cousin", "source", "cousin"),
    ]

    sibling = find_relationship_path(people, relationships, "source", "sister")
    cousin = find_relationship_path(people, relationships, "source", "cousin")
    reverse = find_relationship_path(people, relationships, "sister", "source")

    assert sibling is not None and sibling.label == "姐妹"
    assert cousin is not None and cousin.label == "堂姐妹"
    assert reverse is not None and reverse.label == "兄弟"


def test_paternal_cousin_is_derived_from_shared_paternal_grandparent():
    from backend.app.domain.kinship import find_relationship_path

    people = [
        Person("source", "贺志豪", "male"),
        Person("father", "贺万彬", "male"),
        Person("grandfather", "贺守义", "male"),
        Person("uncle", "贺万成", "male"),
        Person("cousin", "贺志梅", "female"),
    ]
    relationships = [
        Relationship("parent", "source", "father"),
        Relationship("parent", "father", "grandfather"),
        Relationship("parent", "uncle", "grandfather"),
        Relationship("parent", "cousin", "uncle"),
    ]

    result = find_relationship_path(people, relationships, "source", "cousin")

    assert result is not None and result.label == "堂姐妹"


def test_inferred_parent_path_exposes_origin_evidence_and_conflict():
    from backend.app.domain.kinship import find_relationship_path

    people = [
        Person("lan", "贺志兰", "female"),
        Person("hao", "贺志豪", "male"),
        Person("father", "贺万彬", "male"),
        Person("other_father", "贺万成", "male"),
    ]
    relationships = [
        Relationship("sibling", "hao", "lan", "s", "full"),
        Relationship("parent", "hao", "father", "f"),
        Relationship("parent", "lan", "other_father", "lf"),
    ]

    inferred = find_relationship_path(people, relationships, "lan", "father")
    direct = find_relationship_path(
        people, relationships, "lan", "other_father"
    )

    assert inferred is not None
    assert inferred.label == "父亲"
    assert inferred.origin == "inferred"
    assert inferred.conflicting is True
    assert inferred.relationship_ids == ["s", "f"]
    assert [step.person_id for step in inferred.steps] == ["lan", "hao", "father"]
    assert direct is not None
    assert direct.origin == "direct"
    assert direct.conflicting is False


def test_direct_only_path_does_not_use_an_inferred_edge():
    from backend.app.domain.kinship import find_relationship_path

    people = [
        Person("lan", "贺志兰", "female"),
        Person("hao", "贺志豪", "male"),
        Person("father", "贺万彬", "male"),
    ]
    relationships = [
        Relationship("sibling", "hao", "lan", "s", "full"),
        Relationship("parent", "hao", "father", "f"),
    ]

    inferred = find_relationship_path(people, relationships, "lan", "father")
    direct_only = find_relationship_path(
        people,
        relationships,
        "lan",
        "father",
        include_inferred=False,
    )

    assert inferred is not None and inferred.label == "父亲"
    assert inferred.origin == "inferred"
    assert direct_only is not None and direct_only.label == "亲属"
    assert direct_only.origin == "direct"


def test_partial_parent_sibling_inference_uses_cautious_label():
    from backend.app.domain.kinship import find_relationship_path

    people = [
        Person("hao", "贺志豪", "male"),
        Person("lan", "贺志兰", "female"),
        Person("father", "贺万彬", "male"),
    ]
    relationships = [
        Relationship("parent", "hao", "father", "hf"),
        Relationship("parent", "lan", "father", "lf"),
    ]

    result = find_relationship_path(people, relationships, "hao", "lan")

    assert result is not None
    assert result.label == "兄弟姊妹（同父，母系不详）"
    assert result.origin == "inferred"


def test_direct_sibling_edge_wins_over_a_parent_derived_edge():
    from backend.app.domain.kinship import find_relationship_path

    people = [
        Person("hao", "贺志豪", "male"),
        Person("lan", "贺志兰", "female"),
        Person("father", "贺万彬", "male"),
        Person("mother", "王录飞", "female"),
    ]
    relationships = [
        Relationship("sibling", "hao", "lan", "s", "unknown"),
        Relationship("parent", "hao", "father", "hf"),
        Relationship("parent", "lan", "father", "lf"),
        Relationship("parent", "hao", "mother", "hm"),
        Relationship("parent", "lan", "mother", "lm"),
    ]

    result = find_relationship_path(people, relationships, "hao", "lan")

    assert result is not None
    assert result.label == "姐妹"
    assert result.origin == "direct"
    assert result.relationship_ids == ["s"]
