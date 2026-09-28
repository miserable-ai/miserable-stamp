"""Stamping `@id` markers into the comments above HCL blocks."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import language_for, stamp_code

ID = r"@id c-[0-9a-hjkmnp-tv-z]{10}"


def stamp(src: str, path: str = "main.tf", seed: int = 1) -> str:
    language = language_for(path)
    assert language is not None
    return stamp_code(dedent(src), language, random.Random(seed))


def test_hcl_suffixes_are_recognised() -> None:
    assert language_for("infra/main.tf") is not None
    assert language_for("tests/battery.tftest.hcl") is not None
    assert language_for("config.hcl") is None


def test_id_goes_on_a_new_comment_line_in_the_markers_style() -> None:
    after = stamp("""\
    # The sensor's bucket.
    # @model(dep-sensor-bucket, role=Implements)
    resource "aws_s3_bucket" "sensor" {
      bucket = "sensor"
    }

    // @relation(SR-3, role=Implements)
    module "alerts" {
      source = "./alerts"
    }
    """)
    lines = after.splitlines()
    assert lines[1] == "# @model(dep-sensor-bucket, role=Implements)"
    assert re.fullmatch(r"# " + ID, lines[2])
    assert lines[3] == 'resource "aws_s3_bucket" "sensor" {'
    assert lines[7] == "// @relation(SR-3, role=Implements)"
    assert re.fullmatch(r"// " + ID, lines[8])


def test_the_first_block_of_a_file_is_stamped() -> None:
    # The grammar puts the comments before a file's first block outside the block's body node.
    after = stamp("""\
    # @model(dep-lookup, role=Implements)
    data "aws_iam_policy_document" "lookup" {}
    """)
    assert re.fullmatch(r"# " + ID, after.splitlines()[1])


def test_other_blocks_and_nested_blocks_are_not_stamped() -> None:
    src = dedent("""\
    # @relation(SR-1, role=Implements)
    variable "level" {}

    resource "aws_lambda_function" "monitor" {
      # @relation(SR-2, role=Implements)
      environment {}
    }
    """)
    assert stamp(src) == src


def test_run_blocks_are_stamped_in_terraform_tests_only() -> None:
    src = """\
    # @relation(AC-1, role=Verifies)
    run "raises_the_alert" {
      command = plan
    }
    """
    assert len(re.findall(ID, stamp(src, path="tests/alert.tftest.hcl"))) == 1
    assert stamp(src, path="main.tf") == dedent(src)
