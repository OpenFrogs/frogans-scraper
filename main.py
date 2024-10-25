# -*- coding: utf-8 -*-
import os
import requests
import defusedxml.ElementTree as ET

outdir = os.path.join(os.getcwd(), "archive")
os.makedirs(outdir, exist_ok=True)

address = "frogans*demo"
network, site = address.split("*")

network_dir = os.path.join(outdir, network)
site_dir = os.path.join(network_dir, site)
src_dir = os.path.join(site_dir, "src")

fpbl_url = "http://fpb.p2205.test.lab.op3ft.org/architecture-1/fpbl1.0/data.fpbl"

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
        for param in ucsr_path.findall("./param[@name='domain-name']"):
            domain_names.append(param.text)
        for param in ucsr_path.findall("./param[@name='port']"):
            ports.append(param.text)
        for param in ucsr_path.findall("./param[@name='directory']"):
            directories.append(param.text)
        for param in ucsr_path.findall("./param[@name='location']"):
            locations.append(param.text)
    
    fnsl_server_idx = locations.index("public")
    return domain_names[fnsl_server_idx] + ":" + ports[fnsl_server_idx] + directories[fnsl_server_idx]


fpbl_data = requests.get(fpbl_url, headers=headers).text
f = open(os.path.join(outdir, "data.fpbl"), "w+")
f.write(fpbl_data)
f.close()

root = ET.fromstring(fpbl_data)
fnsl_server = get_server_from_fnsl(root.find(".//bootstrap-fnsl"))
print("Using FNSL server "+fnsl_server)

# We won't actually use this data, just archive it
fnsl_network = requests.get(f'http://{fnsl_server}/fnsl5.0/network-{unicode_to_b36(network)}.fnsl', headers=headers).text
os.makedirs(network_dir, exist_ok=True)
f = open(os.path.join(network_dir, "network-"+unicode_to_b36(network)+".fnsl"), "w+")
f.write(fnsl_network)
f.close()

fnsl_site = requests.get(f'http://{fnsl_server}/fnsl5.0/network-{unicode_to_b36(network)}.site-{unicode_to_b36(site)}.fnsl', headers=headers).text
os.makedirs(site_dir, exist_ok=True)
f = open(os.path.join(site_dir, f'network-{unicode_to_b36(network)}.site-{unicode_to_b36(site)}.fnsl'), "w+")
f.write(fnsl_site)
f.close()

root = ET.fromstring(fnsl_site)
site_server = get_server_from_fnsl(root)
print(f"Found server {site_server} for {address}")
home_slide = root.find(".//file-selector").text
site_root = f"http://{site_server}/network-{unicode_to_b36(network)}.site-{unicode_to_b36(site)}"

fsdl = requests.get(site_root + home_slide, headers=headers).text
os.makedirs(src_dir, exist_ok=True)
f = open(os.path.join(src_dir, home_slide[1:]), "w+")
f.write(fsdl)
f.close()