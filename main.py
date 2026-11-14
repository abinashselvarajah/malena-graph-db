"""Command line entry point:  python main.py scrape --limit 50 | merge | stats"""
import argparse
import json

from malena.graph import Graph
from malena.scraper import PhoneDbScraper


def main():
    parser = argparse.ArgumentParser(description="Build a Neo4j graph of phone specifications from phonedb.net")
    sub = parser.add_subparsers(dest="command", required=True)
    scrape = sub.add_parser("scrape", help="scrape devices and write them to Neo4j")
    scrape.add_argument("--limit", type=int, default=25, help="number of devices to scrape (default 25)")
    scrape.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")
    sub.add_parser("merge", help="merge identical components into shared nodes (needs APOC)")
    sub.add_parser("stats", help="print node and relationship counts")
    args = parser.parse_args()

    graph = Graph()
    try:
        if args.command == "scrape":
            graph.init_schema()
            scraper = PhoneDbScraper(delay=args.delay)
            for count, phone in enumerate(scraper.scrape(args.limit), start=1):
                print(f"[{count}/{args.limit}] {graph.add_phone(phone)}")
        elif args.command == "merge":
            graph.merge_identical_components()
        elif args.command == "stats":
            print(json.dumps(graph.stats(), indent=2))
    finally:
        graph.close()


if __name__ == "__main__":
    main()
