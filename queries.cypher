// Example queries for the graph built by `python main.py scrape`.
// Open http://localhost:7474 (login: neo4j / password) and paste them one by one.

// 1. What is in the graph?
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;

// 2. One phone with all its components and properties (the picture for the README)
MATCH (p:Product)
WITH p LIMIT 1
MATCH path = (p)-[:HAS_COMPONENT]->(:Component)-[:HAS_PROPERTY]->(:Property)
RETURN path LIMIT 100;

// 3. The ten phones with the biggest battery
MATCH (p:Product)-[:HAS_COMPONENT]->(:Component {name: 'Power Supply'})
      -[:HAS_PROPERTY]->(b:Property {name: 'Nominal battery capacity'})
WHERE b.value =~ '\\d+'
RETURN p.name AS phone, toInteger(b.value) AS mAh
ORDER BY mAh DESC LIMIT 10;

// 4. Which chipsets show up in the most phones?  (run `python main.py merge` first, so that
//    identical components are shared between phones)
MATCH (c:Component {name: 'Application processor, Chipset'})<-[:HAS_COMPONENT]-(p:Product)
MATCH (c)-[:HAS_PROPERTY]->(cpu:Property {name: 'Cpu'})
RETURN cpu.value AS chipset, count(p) AS phones
ORDER BY phones DESC LIMIT 10;

// 5. Components that several phones have in common, i.e. candidates for re-use
MATCH (c:Component)<-[:HAS_COMPONENT]-(p:Product)
WITH c, collect(p.name) AS phones
WHERE size(phones) > 1
RETURN c.name AS component, size(phones) AS shared_by, phones[..5] AS examples
ORDER BY shared_by DESC LIMIT 20;

// 6. Phones that share a display with a given phone
MATCH (:Product {name: $name})-[:HAS_COMPONENT]->(:Component {name: 'Display'})<-[:HAS_COMPONENT]-(other:Product)
RETURN other.name;
