# MaLeNa graph database

Scrape phone specifications from [phonedb.net](https://phonedb.net) and assemble them into a
[Neo4j](https://neo4j.com) graph of **products → components → properties**.

This is the minimal, self-contained part of the *MaLeNa* project, which looks at re-using parts of
end-of-life products instead of recycling them. Components are the interesting unit there: a graph makes it
easy to ask which phones share the same display, battery or chipset, and so which parts are candidates for
a second life.

The repository contains **no scraped data**. You scrape the pages yourself (see [Scraping etiquette](#scraping-etiquette)).

```
phonedb.net ──► scraper.py ──► dict per phone ──► graph.py ──► Neo4j ──► merge identical components
```

## Graph model

```
(:Product {name, class})
   └─[:HAS_COMPONENT]─► (:Component {name})            e.g. "Display", "Power Supply"
                           └─[:HAS_PROPERTY]─► (:Property {name, value, unit})   e.g. "Pixel density" 255 "PPI"
                                                  ├─[:HAS_VALUE]─► (:Value {value})
                                                  └─[:HAS_UNIT]──► (:Unit {unit})
```

`Value` and `Unit` nodes are shared, so every property with the unit `mAh` points at the same node.
After `merge`, components with exactly the same properties are collapsed into one node that several
products point to. That is what makes "which phones share this part?" a one-hop query.

## Quick start

```bash
docker compose up -d                  # Neo4j 5.20 + APOC on localhost:7474 / 7687
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py scrape --limit 50      # scrape 50 devices into Neo4j (about a minute)
python main.py merge                  # share identical components between phones
python main.py stats                  # node and relationship counts
```

Then open <http://localhost:7474> and try the queries in [`queries.cypher`](queries.cypher).

The Neo4j login is the local default (`neo4j` / `password`, set in `docker-compose.yml`). To use another
server or password, set `NEO4J_URI`, `NEO4J_USER` and `NEO4J_PASSWORD` (see `.env.example`).
Change the password before exposing the database to any network.

## Layout

| File | Purpose |
| --- | --- |
| `malena/scraper.py` | polite phonedb.net scraper and datasheet parser |
| `malena/graph.py` | writes phones into Neo4j, merges duplicate components, statistics |
| `main.py` | command line: `scrape`, `merge`, `stats` |
| `queries.cypher` | example queries |
| `docker-compose.yml` | local Neo4j with APOC |

## Scraping etiquette

- The scraper follows `robots.txt`, identifies itself with a user agent, and waits one second between
  requests (`--delay`). Scraping is capped by `--limit`, 25 devices by default.
- Scraped specifications belong to phonedb.net and its contributors. Check the site's terms before you
  scrape or share data, and do not republish a scraped database.
- phonedb.net does not send its intermediate certificate. The scraper therefore verifies against your
  operating system's trust store (via `truststore`) instead of turning verification off. If that fails on
  your system, install the intermediate certificate or run on macOS/Windows.

## License

MIT, see [LICENSE](LICENSE).
