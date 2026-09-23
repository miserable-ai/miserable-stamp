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
