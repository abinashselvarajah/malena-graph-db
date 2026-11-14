"""Command line:  python main.py scrape --limit 50  |  python main.py merge"""
import argparse

from graph import Graph
from scraper import PhoneDbScraper

parser = argparse.ArgumentParser(description="Build a Neo4j graph of phone specifications from phonedb.net")
sub = parser.add_subparsers(dest="command", required=True)
scrape = sub.add_parser("scrape", help="scrape devices and write them to Neo4j")
scrape.add_argument("--limit", type=int, default=25, help="number of devices (default 25)")
scrape.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")
sub.add_parser("merge", help="share identical components between phones (needs APOC)")
args = parser.parse_args()

graph = Graph()
try:
    if args.command == "scrape":
        graph.init_schema()
        for count, phone in enumerate(PhoneDbScraper(delay=args.delay).scrape(args.limit), start=1):
            print(f"[{count}/{args.limit}] {graph.add_phone(phone)}")
    else:
        graph.merge_identical_components()
finally:
    graph.close()
