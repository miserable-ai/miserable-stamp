"""Stamping `// id:` comments into Context Mapper (CML) models."""

import difflib

import pytest

from miserable_stamp.cml import existing_ids, kebab_case, stamp_cml

MODEL = """\
import "../../usecases/monitor-battery.cml"

// id: ctx-device-link
BoundedContext DeviceLink {
  Aggregate SensorNode {
    useCases = MonitorBattery

    // The sensor's reported charge.
    ValueObject BatteryLevel {
      int percent
    }

    DomainEvent LowBatteryDetected {
      int percent
    }

    enum Unit {
      PERCENT
    }

    Service Charging {
      void charge();
    }
  }
}

UseCase MonitorBattery {
  actor "Clinician"
}

Domain Health {
  Subdomain Monitoring
}
"""


def inserted(before: str, after: str) -> list[str]:
    lines = []
    matcher = difflib.SequenceMatcher(a=before.splitlines(True), b=after.splitlines(True))
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        assert tag in ("equal", "insert"), "stamping changed existing lines"
        if tag == "insert":
            lines += after.splitlines(True)[j1:j2]
    return lines


def test_every_unstamped_declaration_gets_an_id_above_it() -> None:
    after = stamp_cml(MODEL, set())
    assert inserted(MODEL, after) == [
        "  // id: agg-sensor-node\n",
        "    // id: vo-battery-level\n",
        "    // id: ev-low-battery-detected\n",
        "    // id: enum-unit\n",
        "    // id: svc-charging\n",
        "// id: uc-monitor-battery\n",
        "// id: dom-health\n",
        "  // id: sub-monitoring\n",
    ]


def test_the_id_goes_directly_above_the_declaration_below_other_comments() -> None:
    after = stamp_cml(MODEL, set())
    assert (
        "    // The sensor's reported charge.\n    // id: vo-battery-level\n    ValueObject"
        in after
    )


def test_existing_ids_are_kept_and_stamping_is_idempotent() -> None:
    once = stamp_cml(MODEL, set())
    assert once.count("// id: ctx-device-link") == 1
    assert stamp_cml(once, existing_ids(once)) == once


def test_collisions_get_numeric_suffixes() -> None:
    model = "BoundedContext A {\n}\nBoundedContext A2 {\n}\n"
    after = stamp_cml(model, {"ctx-a"})
    assert "// id: ctx-a-2\nBoundedContext A {" in after
    assert "// id: ctx-a2\nBoundedContext A2 {" in after


def test_ids_taken_in_other_files_are_avoided() -> None:
    after = stamp_cml("UseCase MonitorBattery {\n}\n", {"uc-monitor-battery"})
    assert "// id: uc-monitor-battery-2" in after


def test_an_id_separated_by_a_blank_line_does_not_count() -> None:
    model = "// id: ctx-a\n\nBoundedContext A {\n}\n"
    after = stamp_cml(model, existing_ids(model))
    assert after == "// id: ctx-a\n\n// id: ctx-a-2\nBoundedContext A {\n}\n"


def test_existing_ids_are_collected_from_id_lines() -> None:
    assert existing_ids(MODEL) == {"ctx-device-link"}


@pytest.mark.parametrize(
    ("name", "kebab"),
    [
        ("SensorNode", "sensor-node"),
        ("LowBatteryDetected", "low-battery-detected"),
        ("HTTPClient", "http-client"),
        ("Alert2Record", "alert2-record"),
        ("device_link", "device-link"),
        ("A", "a"),
    ],
)
def test_kebab_case(name: str, kebab: str) -> None:
    assert kebab_case(name) == kebab


def test_crlf_is_preserved() -> None:
    after = stamp_cml("BoundedContext A {\r\n}\r\n", set())
    assert after == "// id: ctx-a\r\nBoundedContext A {\r\n}\r\n"


def test_a_repository_in_an_aggregate_root_gets_a_repo_id() -> None:
    """Context Mapper wants a repository's name to end in Repository; the id leaves the suffix
    out, so it names what the repository stores."""
    model = (
        "Aggregate Accounts {\n"
        "  Entity LandingRecord {\n"
        "    aggregateRoot\n"
        "    Repository LandingRecordRepository {\n"
        "      @LandingRecord find(String number);\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    after = stamp_cml(model, set())
    assert inserted(model, after) == [
        "// id: agg-accounts\n",
        "  // id: ent-landing-record\n",
        "    // id: repo-landing-record\n",
    ]
    assert stamp_cml(after, existing_ids(after)) == after


@pytest.mark.parametrize(
    ("name", "stamped"),
    [("Repository", "repo-repository"), ("Accounts", "repo-accounts")],
)
def test_a_repository_name_without_the_suffix_is_kept_whole(name: str, stamped: str) -> None:
    after = stamp_cml(f"Repository {name} {{\n}}\n", set())
    assert after.startswith(f"// id: {stamped}\n")


def test_a_block_comment_opener_inside_a_line_comment_opens_nothing() -> None:
    model = "// see /* the old model\nBoundedContext A {\n}\n"
    assert stamp_cml(model, set()) == (
        "// see /* the old model\n// id: ctx-a\nBoundedContext A {\n}\n"
    )


def test_a_block_comment_opener_inside_a_string_opens_nothing() -> None:
    model = (
        "BoundedContext A {\n"
        '  domainVisionStatement = "paths like src/* are read"\n'
        "  Aggregate B {\n"
        "  }\n"
        "}\n"
    )
    after = stamp_cml(model, set())
    assert inserted(model, after) == ["// id: ctx-a\n", "  // id: agg-b\n"]


def test_declarations_inside_block_comments_are_not_stamped() -> None:
    model = (
        "/* BoundedContext Hidden {\n"
        "BoundedContext AlsoHidden {\n"
        "*/\n"
        "/* one */ /* two\n"
        "BoundedContext StillHidden\n"
        "*/\n"
        "BoundedContext A { /* a trailing comment\n"
        "}  */\n"
    )
    after = stamp_cml(model, set())
    assert inserted(model, after) == ["// id: ctx-a\n"]
