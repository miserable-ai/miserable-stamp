"""Stamping `miserable.id` properties into Structurizr DSL deployment elements."""

from miserable_stamp.dsl import element_names, existing_ids, kebab_name, stamp_dsl

WORKSPACE = """\
workspace "Implant" {

    model {
        clinic = softwareSystem "Clinic Portal" {
            api = container "Monitoring API" "Serves readings" "Python"
            db = container "Readings Store"
        }

        live = deploymentEnvironment "Live" {
            deploymentNode "Amazon Web Services" {
                tags "Amazon Web Services - Cloud"

                deploymentNode "eu-west-1" {
                    properties {
                        "miserable.id" "dep-eu-west-1"
                    }

                    dns = infrastructureNode "Route 53" {
                        technology "DNS"
                        properties {
                            "owner" "platform"
                        }
                    }

                    deploymentNode "Lambda" {
                        containerInstance api
                    }

                    // The store.
                    deploymentNode "DynamoDB" {
                        containerInstance db {
                            tags "Store"
                        }
                    }
                }
            }
        }
    }

    views {
        deployment clinic live {
            include *
        }
    }
}
"""


def stamp(text: str, taken: set[str] | None = None) -> str:
    taken = existing_ids(text) if taken is None else taken
    return stamp_dsl(text, taken, element_names(text))


def test_every_deployment_element_without_an_id_gets_one() -> None:
    after = stamp(WORKSPACE)
    assert existing_ids(after) == {
        "dep-amazon-web-services",
        "dep-eu-west-1",
        "dep-route-53",
        "dep-lambda",
        "dep-monitoring-api",
        "dep-dynamo-db",
        "dep-readings-store",
    }


def test_a_properties_block_is_created_after_the_opening_brace() -> None:
    after = stamp(WORKSPACE)
    assert (
        '            deploymentNode "Amazon Web Services" {\n'
        "                properties {\n"
        '                    "miserable.id" "dep-amazon-web-services"\n'
        "                }\n"
        '                tags "Amazon Web Services - Cloud"\n'
    ) in after


def test_an_existing_properties_block_gets_the_id() -> None:
    after = stamp(WORKSPACE)
    assert (
        "                        properties {\n"
        '                            "miserable.id" "dep-route-53"\n'
        '                            "owner" "platform"\n'
        "                        }\n"
    ) in after


def test_braces_are_created_for_an_element_without_them() -> None:
    after = stamp(WORKSPACE)
    assert (
        "                        containerInstance api {\n"
        "                            properties {\n"
        '                                "miserable.id" "dep-monitoring-api"\n'
        "                            }\n"
        "                        }\n"
    ) in after


def test_only_lines_are_added_apart_from_the_opened_brace() -> None:
    before = WORKSPACE.splitlines()
    after = stamp(WORKSPACE).splitlines()
    changed = [line for line in before if line not in after]
    assert changed == ["                        containerInstance api"]


def test_existing_ids_are_kept_and_stamping_is_idempotent() -> None:
    once = stamp(WORKSPACE)
    assert once.count('"dep-eu-west-1"') == 1
    assert stamp(once) == once


def test_collisions_get_numeric_suffixes() -> None:
    text = 'deploymentNode "Lambda" {\n}\n'
    assert '"miserable.id" "dep-lambda-2"' in stamp(text, {"dep-lambda"})
    assert '"miserable.id" "dep-lambda-3"' in stamp(text, {"dep-lambda", "dep-lambda-2"})


def test_two_instances_of_one_container_get_distinct_ids() -> None:
    text = (
        'api = container "API"\n'
        'deploymentNode "A" {\n    containerInstance api\n}\n'
        'deploymentNode "B" {\n    containerInstance api\n}\n'
    )
    after = stamp(text)
    assert {"dep-api", "dep-api-2"} <= existing_ids(after)


def test_an_unknown_instance_is_named_by_its_identifier() -> None:
    after = stamp("deploymentNode X {\n    softwareSystemInstance monitoring.core\n}\n")
    assert existing_ids(after) == {"dep-x", "dep-monitoring-core"}


def test_elements_in_comments_are_not_stamped() -> None:
    text = '# deploymentNode "A" {\n// deploymentNode "B"\n/*\ndeploymentNode "C" {\n}\n*/\n'
    assert stamp(text) == text


def test_an_id_in_a_nested_element_does_not_count_for_its_parent() -> None:
    text = (
        'deploymentNode "Outer" {\n'
        '    deploymentNode "Inner" {\n'
        "        properties {\n"
        '            "miserable.id" "dep-inner"\n'
        "        }\n"
        "    }\n"
        "}\n"
    )
    assert existing_ids(stamp(text)) == {"dep-inner", "dep-outer"}


def test_empty_braces_on_the_element_line_are_opened() -> None:
    after = stamp('deploymentNode "Edge" {}\n')
    assert after == (
        'deploymentNode "Edge" {\n    properties {\n        "miserable.id" "dep-edge"\n    }\n}\n'
    )


def test_crlf_is_preserved() -> None:
    after = stamp('deploymentNode "Edge" {\r\n}\r\n')
    assert "\n" not in after.replace("\r\n", "")
    assert '"miserable.id" "dep-edge"' in after


def test_names_are_kebab_cased() -> None:
    assert kebab_name("Amazon Web Services") == "amazon-web-services"
    assert kebab_name("eu-west-1") == "eu-west-1"
    assert kebab_name("DynamoDB") == "dynamo-db"
    assert kebab_name("SensorNode") == "sensor-node"
    assert kebab_name("EC2 (t4g.small)") == "ec2-t4g-small"
    assert kebab_name("***") == "element"
