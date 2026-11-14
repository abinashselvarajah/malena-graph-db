"""Write scraped phones into Neo4j and keep the graph tidy.

Graph model
-----------
(:Product {name, class})-[:HAS_COMPONENT]->(:Component {name})
(:Component)-[:HAS_PROPERTY]->(:Property {name, value, unit})
(:Property)-[:HAS_VALUE]->(:Value {value})      shared between properties
(:Property)-[:HAS_UNIT]->(:Unit {unit})         shared between properties
"""
import os
import re

from neo4j import GraphDatabase

# Datasheet sections that become components (everything else, e.g. the Introduction, stays on the product).
COMPONENT_SECTIONS = {
    "Application processor, Chipset", "Operative Memory", "Non-volatile Memory", "Display",
    "Graphical Subsystem", "Audio/Video Interfaces", "Audio Subsystem", "Cellular Phone",
    "Secondary Cellular Phone", "Control Peripherals", "Communication Interfaces",
    "Multimedia Broadcast", "Satellite Navigation", "Primary Camera System",
    "Secondary Camera System", "Built-in Sensors", "Ingress Protection", "Power Supply",
    "Geographical Attributes", "Software Environment", "Physical Attributes",
}

# "3400 MHz" -> ("3400", "MHz"), "12.85x8.21x0.21 inches" -> ("12.85x8.21x0.21", "inches")
_VALUE_UNIT = re.compile(r"^\s*([\d.,]+(?:x[\d.,]+)*)(?:\s*([^0-9].*))?\s*$")


def split_value_unit(text: str) -> tuple[str, str]:
    match = _VALUE_UNIT.match(text)
    return (match.group(1).strip(), (match.group(2) or "").strip()) if match else (text, "")


def properties_of(attributes: dict) -> list[dict]:
    """Split every spec into one property per comma-separated entry."""
    props = []
    for key, raw in attributes.items():
        for part in (p.strip() for p in str(raw).split(",")):
            value, unit = split_value_unit(part)
            props.append({"name": key.capitalize(), "value": value, "unit": unit})
    return props


ADD_COMPONENT = """
MATCH (p:Product {name: $product})
CREATE (c:Component {name: $component})
CREATE (p)-[:HAS_COMPONENT]->(c)
WITH c
UNWIND $props AS prop
CREATE (c)-[:HAS_PROPERTY]->(pr:Property {name: prop.name, value: prop.value, unit: prop.unit})
FOREACH (_ IN CASE WHEN prop.value <> '' THEN [1] ELSE [] END |
    MERGE (v:Value {value: prop.value}) MERGE (pr)-[:HAS_VALUE]->(v))
FOREACH (_ IN CASE WHEN prop.unit <> '' THEN [1] ELSE [] END |
    MERGE (u:Unit {unit: prop.unit}) MERGE (pr)-[:HAS_UNIT]->(u))
"""

# Identical components (same properties) of different phones collapse into one shared node.
FINGERPRINT = """
MATCH (c:Component)-[:HAS_PROPERTY]->(p:Property)
WITH c, apoc.coll.sort(collect(p.name + ':' + p.value + ':' + p.unit)) AS attributes
SET c.fingerprint = apoc.util.md5([c.name] + attributes)
"""
MERGE_DUPLICATES = """
MATCH (c:Component) WHERE c.fingerprint IS NOT NULL
WITH c.fingerprint AS fingerprint, collect(c) AS nodes WHERE size(nodes) > 1
WITH nodes[0] AS keep, nodes[1..] AS duplicates
UNWIND duplicates AS duplicate
OPTIONAL MATCH (product)-[:HAS_COMPONENT]->(duplicate)
FOREACH (_ IN CASE WHEN product IS NULL THEN [] ELSE [1] END | MERGE (product)-[:HAS_COMPONENT]->(keep))
WITH duplicate
OPTIONAL MATCH (duplicate)-[:HAS_PROPERTY]->(p:Property)
DETACH DELETE p, duplicate
"""


class Graph:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
            auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password")),
        )

    def close(self):
        self.driver.close()

    def init_schema(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT product_name IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE")
            session.run("CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)")
            session.run("CREATE INDEX property_name IF NOT EXISTS FOR (p:Property) ON (p.name)")

    def add_phone(self, data: dict) -> str | None:
        intro = data.get("Introduction", {})
        name = intro.get("Model") or intro.get("Codename") or intro.get("codename")
        if not name:
            return None
        with self.driver.session() as session:
            session.run(
                "MERGE (p:Product {name: $name}) SET p.class = $cls",
                name=name, cls=intro.get("Device Category", "Unknown"),
            )
            for section, attributes in data.items():
                if section in COMPONENT_SECTIONS and isinstance(attributes, dict) and attributes:
                    session.run(ADD_COMPONENT, product=name, component=section, props=properties_of(attributes))
        return name

    def merge_identical_components(self):
        with self.driver.session() as session:
            session.run(FINGERPRINT)
            session.run(MERGE_DUPLICATES)

    def stats(self) -> dict:
        with self.driver.session() as session:
            nodes = session.run("MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS n ORDER BY n DESC")
            rels = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY n DESC")
            return {
                "nodes": {r["label"]: r["n"] for r in nodes},
                "relationships": {r["type"]: r["n"] for r in rels},
            }
