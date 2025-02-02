# -*- coding: utf-8 -*-
import os
import requests
import re
import defusedxml.ElementTree as ET # Can swap for Python's built-in, this just provides a bit more security
import hashlib

outdir = os.path.join(os.getcwd(), "archive-alpha")
os.makedirs(outdir, exist_ok=True)

sites = {}

addresses_queue = ["frogans*lab"]
visited = set()

#fal_server = "a.dev-1.fal.fns.test.fcr.frogans"
fal_server = "fra-par-th2-fns-01-srv-01-01.fns.test.fcr.frogans"
#fal_server = "fra-par-th2-fns-01-srv-02-01.fns.test.fcr.frogans" # Doesn't work
#fal_server = "51.178.59.247"

headers = {'User-Agent': 'Frogans Scraper 0.1'}

# https://stackoverflow.com/a/60498038/8507259
def b36_encode(i):
    if i < 36: return "0123456789abcdefghijklmnopqrstuvwxyz"[i]
    return b36_encode(i // 36) + b36_encode(i % 36)

def unicode_to_b36(s: str) :
    result = ""
    for char in s:
        # Convert the codepoint to base 36 and pad it with 0s to a length of 4
        base36_str = b36_encode(ord(char)).zfill(4)
        result += base36_str
    return result

# Note: only partially consumes FNSL, not fully spec-compliant
def get_server_from_fnsl(root):
    domain_names = []
    ports = []
    directories = []
    locations = []
    for ucsr_path in root.findall(".//ucsr-path"):
        for param in ucsr_path.findall("./domain-name"):
            domain_names.append(param.text)
        for param in ucsr_path.findall("./port"):
            ports.append(param.text)
        for param in ucsr_path.findall("./directory"):
            directories.append(param.text)
        for param in ucsr_path.findall("./location"):
            locations.append(param.text)
    
    fnsl_server_idx = locations.index("public")
    return domain_names[fnsl_server_idx] + ":" + ports[fnsl_server_idx] + directories[fnsl_server_idx]

while(len(addresses_queue) > 0):
    address = addresses_queue.pop()
    if address in visited:
        continue
    visited.add(address)
    print("Visiting "+address)
    network, siteLong = address.split("*")
    addrParts = siteLong.split("/", maxsplit=1)
    site = addrParts[0]
    path = "/"+addrParts[1] if len(addrParts) > 1 else None
    
    network_dir = os.path.join(outdir, network)
    site_dir = os.path.join(network_dir, site)
    src_dir = os.path.join(site_dir, "src")
    
    if site in sites:
        fnsl_site = sites[site]
    else:
        fnsl_enc = f'{unicode_to_b36(network.lower())}.lookup.{unicode_to_b36(site.lower())}.fnsl'
        sha1 = hashlib.sha1(fnsl_enc.encode()).hexdigest()
        print(f'http://{fal_server}/{sha1[0:2]}/{sha1[2:4]}/{sha1[4:6]}/{fnsl_enc}')
        fnsl_site = requests.get(f'http://{fal_server}/{sha1[0:2]}/{sha1[2:4]}/{sha1[4:6]}/{fnsl_enc}', headers=headers).text
        os.makedirs(site_dir, exist_ok=True)
        f = open(os.path.join(site_dir, f'network-{unicode_to_b36(network.lower())}.site-{unicode_to_b36(site.lower())}.fnsl'), "w+")
        f.write(fnsl_site)
        f.close()
        sites[site] = fnsl_site
    
    try:
        root = ET.fromstring(fnsl_site)
    except Exception as _:
        print("Invalid FNSL data, skipping")
        continue
    site_server = get_server_from_fnsl(root)
    if path == None:
        print(f"Found server {site_server} for {address}")
        path = root.find(".//home-slide-file").text

    #site_root = f"http://{site_server}/network-{unicode_to_b36(network)}.site-{unicode_to_b36(site)}"
    res = requests.get("http://" + site_server + path, headers=headers)
    fpath = os.path.join(src_dir, path[1:])
    if not os.path.exists(fpath):
        os.makedirs(os.path.dirname(fpath), exist_ok=True)

    f = open(fpath, "wb+")
    f.write(res.content)
    f.close()
    
    fsdl_dec = re.search(r"<frogans-fsdl version=['\"]([^'\"]+)['\"]>", res.text)
    if fsdl_dec is not None:
        version = fsdl_dec.group(1)
        if version != "3.0":
            print("Unexpected version "+version+" at address "+address)
        for locMatch in re.finditer(r"(?:name|address)=['\"]([^'\"]+)['\"]", res.text):
            location = locMatch.group(1)
            if location.startswith("/"):
                location = network + "*" + site + location
            elif "*" not in location:
                location = network + "*" + site + "/" + location
            addresses_queue.append(location)