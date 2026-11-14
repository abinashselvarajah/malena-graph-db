// Paste into the Neo4j browser (http://localhost:7474), one query at a time.

// 1. What is in the graph?
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;

// 2. One phone with all its components and properties
MATCH (p:Product) WITH p LIMIT 1
MATCH path = (p)-[:HAS_COMPONENT]->(:Component)-[:HAS_PROPERTY]->(:Property)
RETURN path LIMIT 100;

// 3. The ten phones with the biggest battery
MATCH (p:Product)-[:HAS_COMPONENT]->(:Component {name: 'Power Supply'})
      -[:HAS_PROPERTY]->(b:Property {name: 'Nominal battery capacity'})
WHERE b.value =~ '\\d+'
RETURN p.name AS phone, toInteger(b.value) AS mAh ORDER BY mAh DESC LIMIT 10;

// 4. Components that several phones share (run `python main.py merge` first)
MATCH (c:Component)<-[:HAS_COMPONENT]-(p:Product)
WITH c, collect(p.name) AS phones WHERE size(phones) > 1
RETURN c.name AS component, size(phones) AS shared_by, phones[..5] AS examples
ORDER BY shared_by DESC LIMIT 20;
