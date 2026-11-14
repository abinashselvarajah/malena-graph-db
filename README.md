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

## Setup

### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose (runs Neo4j), or an existing Neo4j 5 server with the APOC plugin (see [Without Docker](#without-docker))
- Python 3.10 or newer
- Internet access to phonedb.net for the scraping step

### 2. Get the code

```bash
git clone https://github.com/abinashselvarajah/malena-graph-db.git
cd malena-graph-db
```

### 3. Start Neo4j

```bash
docker compose up -d
```

This starts Neo4j 5.20 Community with the APOC plugin. The first start downloads the image and can take a
minute or two. It is ready when <http://localhost:7474> opens (log in with `neo4j` / `password`).
Check the status with `docker compose logs -f neo4j` and look for `Started.`

### 4. Install the Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Configure the connection (optional)

The defaults match `docker-compose.yml`, so you can skip this for a local setup. To connect to another
server or use another password, copy `.env.example` to `.env`, edit it, and export the variables:

```bash
cp .env.example .env
export $(grep -v '^#' .env | xargs)   # Windows PowerShell: set $env:NEO4J_PASSWORD = "..."
```

| Variable | Default |
| --- | --- |
| `NEO4J_URI` | `neo4j://localhost:7687` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | `password` |

If you change the password, change `NEO4J_AUTH` in `docker-compose.yml` as well, **before** the first start
(Neo4j only reads it when it creates the database volume). Change the default password before the database
is reachable from any network.

### 6. Build the graph

```bash
python main.py scrape --limit 50      # scrape 50 devices into Neo4j, about a minute
python main.py merge                  # share identical components between phones
python main.py stats                  # node and relationship counts
```

`scrape` takes `--limit` (devices, default 25) and `--delay` (seconds between requests, default 1.0).
You can run it again with a larger limit; phones that are already in the graph are updated rather than
duplicated. Run `merge` once after scraping is finished.

### 7. Explore it

Open <http://localhost:7474> and paste the queries from [`queries.cypher`](queries.cypher) one by one. The
second query draws one phone with its components and properties as a graph.

### Stop and reset

```bash
docker compose down       # stop Neo4j, keep the data
docker compose down -v    # stop and delete the database (start from scratch)
```

### Without Docker

Install Neo4j 5 (Community or Desktop) and the [APOC core plugin](https://neo4j.com/docs/apoc/current/installation/),
start the database, and set `NEO4J_URI`, `NEO4J_USER` and `NEO4J_PASSWORD` to match. Then continue with step 4.
APOC is only needed for `python main.py merge`.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| `Unable to retrieve routing information` / connection refused | Neo4j is still starting. Wait for `Started.` in `docker compose logs neo4j`. |
| `Neo.ClientError.Security.Unauthorized` | The password does not match. Check `NEO4J_PASSWORD` and `NEO4J_AUTH`, or reset with `docker compose down -v`. |
| `no procedure ... apoc` during `merge` | APOC is not installed. Use the provided `docker-compose.yml` or install the plugin. |
| `CERTIFICATE_VERIFY_FAILED` while scraping | See [Scraping etiquette](#scraping-etiquette): the OS trust store lacks the intermediate certificate. |
| Many `skipped ...` lines | phonedb.net rate-limits or a page changed. Increase `--delay`. |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The scraper and parsing tests run offline. The graph tests need a running Neo4j with APOC (step 3) and
are skipped otherwise. They **wipe the database**, so they only run against an empty one; set
`MALENA_TEST_WIPE=1` to allow wiping a database that already holds data.

## Layout

| File | Purpose |
| --- | --- |
| `malena/scraper.py` | polite phonedb.net scraper and datasheet parser |
| `malena/graph.py` | writes phones into Neo4j, merges duplicate components, statistics |
| `main.py` | command line: `scrape`, `merge`, `stats` |
| `tests/` | pytest tests |
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
