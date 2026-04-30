# -*- coding: utf-8 -*-
from helpers import *
from alpha import *
from beta import *
import sys
import argparse

parser = argparse.ArgumentParser(prog="Frogans Scraper")
parser.add_argument("--skip-images", action="store_true", help="Skip downloading images")
parser.add_argument("-a", "--alpha", action="store_true", help="Emulate Alpha player")
parser.add_argument("-b", "--beta", action="store_true", help="Emulate Beta player")
parser.add_argument("addresses", nargs="+", help="URLs to test")
args = parser.parse_args()

if not (args.alpha or args.beta):
    print("At least one of Alpha and Beta modes must be specified!")
    sys.exit()

networks = {}
sites = {}

request_queue = []
for address in args.addresses:
    if args.alpha:
        request_queue.append(AlphaRequest(address))
    if args.beta:
        request_queue.append(BetaRequest(address))

request_queue.reverse()
visited = set()

fal_server = "fra-par-th2-fns-01-srv-01-01.fns.test.fcr.frogans"
fpbl_url = "http://fpb.p2205.test.lab.op3ft.org/architecture-1/fpbl1.0/data.fpbl"

headers = {'User-Agent': 'Frogans Scraper 0.2'}

image_extensions = ["png", "jpg", "gif"]

if args.alpha:
    alphadir = os.path.join(os.getcwd(), "archive-alpha2")
    os.makedirs(alphadir, exist_ok=True)
    alpha_scraper = AlphaScraper({'output_dir': alphadir, 'headers': headers, 'fal_server': fal_server})

if args.beta:
    betadir = os.path.join(os.getcwd(), "archive-beta2")
    os.makedirs(betadir, exist_ok=True)
    beta_scraper = BetaScraper({'output_dir': betadir, 'headers': headers, 'fpbl_url': fpbl_url})

while(len(request_queue) > 0):
    request = request_queue.pop()
    extension = re.search("\\.(\\w+)$", request.address)
    if args.skip_images and extension and extension.group(1) in image_extensions:
        continue
    
    if isinstance(request, AlphaRequest):
        request_queue.extend(alpha_scraper.scrape(request))
    elif isinstance(request, BetaRequest):
        request_queue.extend(beta_scraper.scrape(request))