import os

import pytest
from neo4j import GraphDatabase

from graph import Graph, properties_of, split_value_unit

PHONE = {
    "Introduction": {"Model": "Test Phone X", "Device Category": "Smartphone"},
    "Display": {"Resolution": "720x1560", "Pixel Density": "282 PPI"},
    "Power Supply": {"Battery": "Li-ion, built-in", "Nominal Battery Capacity": "6000 mAh battery"},
    "Unknown Section": {"Ignored": "yes"},
}


@pytest.mark.parametrize("text, expected", [
    ("3400 MHz", ("3400", "MHz")),
    ("12.85x8.21x0.21 inches", ("12.85x8.21x0.21", "inches")),
    ("6 GiB RAM", ("6", "GiB RAM")),
    ("720x1560", ("720x1560", "")),
    ("Capacitive", ("Capacitive", "")),
])
def test_split_value_unit(text, expected):
    assert split_value_unit(text) == expected


def test_properties_of_splits_commas_and_normalises_names():
    props = properties_of({"Nominal Battery Capacity": "6000 mAh", "Battery": "Li-ion, built-in"})
    assert props == [
        {"name": "Nominal battery capacity", "value": "6000", "unit": "mAh"},
        {"name": "Battery", "value": "Li-ion", "unit": ""},
        {"name": "Battery", "value": "built-in", "unit": ""},
    ]


# --- integration tests: only run when a Neo4j with APOC is reachable (e.g. `docker compose up -d`) ---

def _connect():
    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    auth = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password"))
    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        driver.verify_connectivity()
    except Exception:
        driver.close()
        return None
    return driver


@pytest.fixture
def graph():
    driver = _connect()
    if driver is None:
        pytest.skip("no Neo4j reachable")
    with driver.session() as session:
        # the tests wipe the database, so they refuse to run against one that already holds data
        if session.run("MATCH (n) RETURN count(n)").single()[0] and os.environ.get("MALENA_TEST_WIPE") != "1":
            driver.close()
            pytest.skip("database is not empty; set MALENA_TEST_WIPE=1 to let the tests wipe it")
        session.run("MATCH (n) DETACH DELETE n")
    g = Graph()
    yield g
    g.close()
    driver.close()


def count(graph, query):
    with graph.driver.session() as session:
        return session.run(query).single()[0]


def test_add_phone_builds_products_components_and_properties(graph):
    graph.init_schema()
    assert graph.add_phone(PHONE) == "Test Phone X"
    assert count(graph, "MATCH (:Product {name: 'Test Phone X', class: 'Smartphone'}) RETURN count(*)") == 1
    assert count(graph, "MATCH (:Product)-[:HAS_COMPONENT]->(c:Component) RETURN count(c)") == 2  # unknown section skipped
    assert count(graph, "MATCH (p:Property {name: 'Nominal battery capacity'})-[:HAS_UNIT]->(:Unit {unit: 'mAh battery'}) RETURN count(p)") == 1


def test_add_phone_without_a_name_is_ignored(graph):
    assert graph.add_phone({"Introduction": {}}) is None
    assert count(graph, "MATCH (n) RETURN count(n)") == 0


def test_merge_shares_identical_components_between_phones(graph):
    graph.add_phone(PHONE)
    graph.add_phone({**PHONE, "Introduction": {"Model": "Test Phone Y"}, "Power Supply": {"Battery": "NiMH"}})
    graph.merge_identical_components()
    # both phones have the identical Display, so only one Display component is left, shared by two products
    assert count(graph, "MATCH (c:Component {name: 'Display'}) RETURN count(c)") == 1
    assert count(graph, "MATCH (:Product)-[:HAS_COMPONENT]->(:Component {name: 'Display'}) RETURN count(*)") == 2
    assert count(graph, "MATCH (c:Component {name: 'Power Supply'}) RETURN count(c)") == 2  # different, stays separate
