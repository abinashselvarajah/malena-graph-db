# MaLeNa graph database

Scrape phone specifications from [phonedb.net](https://phonedb.net) into a [Neo4j](https://neo4j.com)
graph of **products → components → properties**. Part of the *MaLeNa* project on re-using parts of
end-of-life products: once identical components are shared between phones, "which phones have the same
display, battery or chipset?" becomes a one-hop query.

The repository contains **no scraped data**. You scrape the pages yourself (see [Scraping etiquette](#scraping-etiquette)).

## Graph model

```
(:Product {name, class})
   └─[:HAS_COMPONENT]─► (:Component {name})              e.g. "Display", "Power Supply"
                           └─[:HAS_PROPERTY]─► (:Property {name, value, unit})   e.g. "Pixel density" 255 "PPI"
                                                  ├─[:HAS_VALUE]─► (:Value {value})
                                                  └─[:HAS_UNIT]──► (:Unit {unit})
```

`Value` and `Unit` nodes are shared. After `merge`, components with exactly the same properties collapse
into one node that several products point to.

## Setup

Requires Docker and Python 3.10+.

```bash
git clone https://github.com/abinashselvarajah/malena-graph-db.git
cd malena-graph-db

docker compose up -d                  # Neo4j 5.20 + APOC; ready when http://localhost:7474 opens
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py scrape --limit 50      # scrape 50 devices into Neo4j (about a minute)
python main.py merge                  # share identical components between phones
```

Open <http://localhost:7474> (login `neo4j` / `password`) and paste the queries from
[`queries.cypher`](queries.cypher).

- `scrape` takes `--limit` (default 25) and `--delay` (seconds between requests, default 1.0).
- The login is a local default set in `docker-compose.yml`. To use another server or password, set
  `NEO4J_URI`, `NEO4J_USER` and `NEO4J_PASSWORD`, and change `NEO4J_AUTH` in `docker-compose.yml` before the
  first start. Change the password before exposing the database to a network.
- `docker compose down -v` stops Neo4j and deletes the database.

## Tests

```bash
pip install pytest
python -m pytest
```

The scraper and parser tests run offline. The graph tests need the running Neo4j from above and are skipped
otherwise. They **wipe the database**, so they only run against an empty one (or with `MALENA_TEST_WIPE=1`).

## Scraping etiquette

- The scraper follows `robots.txt`, identifies itself, waits between requests and is capped by `--limit`.
- The specifications belong to phonedb.net and its contributors. Check the site's terms before you scrape
  or share data, and do not republish a scraped database.
- phonedb.net does not send its intermediate certificate, so the scraper verifies against your operating
  system's trust store (`truststore`) instead of disabling verification. On Linux this may fail.

## License

MIT, see [LICENSE](LICENSE).
