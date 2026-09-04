from dataclasses import dataclass

import pytest

from backend.app.domain.relationship_inference import effective_relationships


@dataclass
class Person:
    id: str
    name: str
    gender: str


@dataclass
class Relationship:
    id: str
    kind: str
    person_id: str
    relative_id: str
    sibling_type: str | None = None


people_fixture = [
    Person("hao", "贺志豪", "male"),
    Person("lan", "贺志兰", "female"),
    Person("father", "贺万彬", "male"),
    Person("mother", "王录飞", "female"),
]


def relationships_for(sibling_type: str) -> list[Relationship]:
    return [
        Relationship("s", "sibling", "hao", "lan", sibling_type),
        Relationship("f", "parent", "hao", "father"),
        Relationship("m", "parent", "hao", "mother"),
    ]


def test_parent_directions_are_relative_to_the_requested_source():
    relationships = [Relationship("p", "parent", "hao", "father")]

    child_view = effective_relationships(people_fixture, relationships, "hao")
    parent_view = effective_relationships(people_fixture, relationships, "father")

    assert [(fact.target_id, fact.direction) for fact in child_view] == [
        ("father", "up")
    ]
    assert [(fact.target_id, fact.direction) for fact in parent_view] == [
        ("hao", "down")
    ]


def test_full_sibling_inherits_both_known_parents():
    facts = effective_relationships(
        people_fixture, relationships_for("full"), "lan"
    )

    inherited = {
        fact.target_id: fact
        for fact in facts
        if fact.kind == "parent" and fact.origin == "inferred"
    }
    assert set(inherited) == {"father", "mother"}
    assert inherited["father"].direction == "up"
    assert inherited["father"].path_person_ids == ("lan", "hao", "father")
    assert inherited["father"].relationship_ids == ("s", "f")


@pytest.mark.parametrize(
    ("sibling_type", "expected"),
    [
        ("paternal_half", {"father"}),
        ("maternal_half", {"mother"}),
        ("unknown", set()),
    ],
)
def test_sibling_type_limits_parent_inheritance(sibling_type, expected):
    facts = effective_relationships(
        people_fixture, relationships_for(sibling_type), "lan"
    )

    actual = {
        fact.target_id
        for fact in facts
        if fact.kind == "parent" and fact.origin == "inferred"
    }
    assert actual == expected


@pytest.mark.parametrize(
    ("relationships", "expected_type"),
    [
        (
            [
                Relationship("af", "parent", "hao", "father"),
                Relationship("bf", "parent", "lan", "father"),
                Relationship("am", "parent", "hao", "mother"),
                Relationship("bm", "parent", "lan", "mother"),
            ],
            "full",
        ),
        (
            [
                Relationship("af", "parent", "hao", "father"),
                Relationship("bf", "parent", "lan", "father"),
                Relationship("am", "parent", "hao", "mother"),
                Relationship("bm", "parent", "lan", "other_mother"),
            ],
            "paternal_half",
        ),
        (
            [
                Relationship("af", "parent", "hao", "father"),
                Relationship("bf", "parent", "lan", "other_father"),
                Relationship("am", "parent", "hao", "mother"),
                Relationship("bm", "parent", "lan", "mother"),
            ],
            "maternal_half",
        ),
        (
            [
                Relationship("af", "parent", "hao", "father"),
                Relationship("bf", "parent", "lan", "father"),
                Relationship("am", "parent", "hao", "mother"),
            ],
            "shared_father_unknown_mother",
        ),
        (
            [
                Relationship("af", "parent", "hao", "father"),
                Relationship("am", "parent", "hao", "mother"),
                Relationship("bm", "parent", "lan", "mother"),
            ],
            "shared_mother_unknown_father",
        ),
    ],
)
def test_direct_parents_classify_siblings_without_overstating_missing_data(
    relationships, expected_type
):
    people = [
        *people_fixture,
        Person("other_father", "兰父", "male"),
        Person("other_mother", "兰母", "female"),
    ]

    facts = effective_relationships(people, relationships, "hao")

    sibling = next(
        fact
        for fact in facts
        if fact.target_id == "lan"
        and fact.kind == "sibling"
        and fact.origin == "inferred"
    )
    assert sibling.direction == "same"
    assert sibling.sibling_type == expected_type


def test_conflicting_inherited_parent_is_flagged_without_mutating_input():
    other_father = Person("other_father", "贺万成", "male")
    people = [*people_fixture, other_father]
    relationships = [
        *relationships_for("full"),
        Relationship("lf", "parent", "lan", "other_father"),
    ]
    original = [relationship.__dict__.copy() for relationship in relationships]

    facts = effective_relationships(people, relationships, "lan")

    inherited_father = next(
        fact
        for fact in facts
        if fact.target_id == "father"
        and fact.kind == "parent"
        and fact.origin == "inferred"
    )
    assert inherited_father.conflicting is True
    assert [relationship.__dict__ for relationship in relationships] == original


def test_multiple_direct_or_inherited_same_gender_parents_are_conflicting():
    people = [
        *people_fixture,
        Person("other_father", "贺万成", "male"),
    ]
    direct_relationships = [
        Relationship("f", "parent", "hao", "father"),
        Relationship("of", "parent", "hao", "other_father"),
    ]
    inherited_relationships = [
        Relationship("s", "sibling", "hao", "lan", "full"),
        *direct_relationships,
    ]

    direct_fathers = [
        fact
        for fact in effective_relationships(people, direct_relationships, "hao")
        if fact.kind == "parent" and fact.origin == "direct"
    ]
    inherited_fathers = [
        fact
        for fact in effective_relationships(people, inherited_relationships, "lan")
        if fact.kind == "parent" and fact.origin == "inferred"
    ]

    assert len(direct_fathers) == 2
    assert all(fact.conflicting for fact in direct_fathers)
    assert len(inherited_fathers) == 2
    assert all(fact.conflicting for fact in inherited_fathers)


def test_unknown_gender_parents_do_not_create_a_same_gender_conflict():
    people = [
        Person("hao", "贺志豪", "male"),
        Person("first", "长辈甲", "unknown"),
        Person("second", "长辈乙", "unknown"),
    ]
    relationships = [
        Relationship("first", "parent", "hao", "first"),
        Relationship("second", "parent", "hao", "second"),
    ]

    parents = [
        fact
        for fact in effective_relationships(people, relationships, "hao")
        if fact.kind == "parent"
    ]

    assert len(parents) == 2
    assert not any(fact.conflicting for fact in parents)


def test_half_sibling_evidence_includes_shared_and_different_parents():
    people = [
        *people_fixture,
        Person("other_mother", "兰母", "female"),
    ]
    relationships = [
        Relationship("af", "parent", "hao", "father"),
        Relationship("bf", "parent", "lan", "father"),
        Relationship("am", "parent", "hao", "mother"),
        Relationship("bm", "parent", "lan", "other_mother"),
    ]

    facts = effective_relationships(people, relationships, "hao")

    sibling = next(
        fact
        for fact in facts
        if fact.target_id == "lan"
        and fact.kind == "sibling"
        and fact.origin == "inferred"
    )
    assert sibling.sibling_type == "paternal_half"
    assert sibling.path_person_ids == ("hao", "father", "lan")
    assert sibling.relationship_ids == ("af", "bf", "am", "bm")


def test_direct_and_parent_derived_sibling_disagreement_remains_visible():
    relationships = [
        Relationship("s", "sibling", "hao", "lan", "maternal_half"),
        Relationship("af", "parent", "hao", "father"),
        Relationship("bf", "parent", "lan", "father"),
        Relationship("am", "parent", "hao", "mother"),
        Relationship("bm", "parent", "lan", "mother"),
    ]

    facts = effective_relationships(people_fixture, relationships, "hao")

    sibling_facts = [
        fact
        for fact in facts
        if fact.target_id == "lan" and fact.kind == "sibling"
    ]
    assert {(fact.origin, fact.sibling_type) for fact in sibling_facts} == {
        ("direct", "maternal_half"),
        ("inferred", "full"),
    }
    assert all(fact.conflicting for fact in sibling_facts)


def test_spouse_is_direct_and_bidirectional():
    people = [
        Person("hao", "贺志豪", "male"),
        Person("yingla", "管应拉", "female"),
    ]
    relationships = [Relationship("wife", "spouse", "hao", "yingla")]

    forward = effective_relationships(people, relationships, "hao")
    reverse = effective_relationships(people, relationships, "yingla")

    assert [
        (fact.target_id, fact.direction, fact.origin) for fact in forward
    ] == [("yingla", "same", "direct")]
    assert [
        (fact.target_id, fact.direction, fact.origin) for fact in reverse
    ] == [("hao", "same", "direct")]


def test_paternal_cousin_is_derived_only_from_direct_paternal_path():
    people = [
        Person("hao", "贺志豪", "male"),
        Person("father", "贺万彬", "male"),
        Person("grandfather", "贺守义", "male"),
        Person("uncle", "贺万成", "male"),
        Person("cousin", "贺志梅", "female"),
    ]
    relationships = [
        Relationship("sf", "parent", "hao", "father"),
        Relationship("fg", "parent", "father", "grandfather"),
        Relationship("ug", "parent", "uncle", "grandfather"),
        Relationship("cu", "parent", "cousin", "uncle"),
    ]

    facts = effective_relationships(people, relationships, "hao")

    cousin = next(
        fact
        for fact in facts
        if fact.target_id == "cousin"
        and fact.kind == "paternal_cousin"
        and fact.origin == "inferred"
    )
    assert cousin.direction == "same"
    assert cousin.path_person_ids == (
        "hao",
        "father",
        "grandfather",
        "uncle",
        "cousin",
    )
    assert cousin.relationship_ids == ("sf", "fg", "ug", "cu")
