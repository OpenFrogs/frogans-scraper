# -*- coding: utf-8 -*-
import os
import requests
import re
import defusedxml.ElementTree as ET # Can swap for Python's built-in, this just provides a bit more security
from helpers import *

class BetaRequest(FrogansRequest):
    def __init__(self, address: str):
        super().__init__(address)
        self.network, siteLong = address.split("*")
        if len(siteLong) > 0:
            addrParts = siteLong.split("/", maxsplit=1)
        else:
            addrParts = [""]
        self.site = addrParts[0]
        self.siteFull = self.network+"*"+self.site
        self.path = "/"+addrParts[1] if len(addrParts) > 1 else None

class BetaScraper(Scraper):
    def __init__(self, settings: dict):
        self.output_dir = settings['output_dir']
        self.headers = settings['headers']
        self.networks_fnsls = {}
        self.site_fnsls = {}
        self.visited = set()
        
        # Get FNSL server
        fpbl_data = requests.get(settings['fpbl_url'], headers=self.headers).text
        f = open(os.path.join(self.output_dir, "data.fpbl"), "w+", encoding="utf-8")
        f.write(fpbl_data)
        f.close()
        root = ET.fromstring(fpbl_data)
        fnsl_server = get_server_from_fnsl(root.find(".//bootstrap-fnsl"))
        print("Using FNSL server "+fnsl_server)
        self.fnsl_server = fnsl_server
    
    def scrape(self, request: FrogansRequest) -> list[FrogansRequest]:
        if not isinstance(request, BetaRequest):
            raise TypeError("Request for "+str(request)+" is not a beta request!")
        if request.address in self.visited:
            return []
        self.visited.add(request.address)
        print("Visiting "+request.address+" (B)")
        
        network_dir = os.path.join(self.output_dir, request.network)
        site_dir = os.path.join(network_dir, request.site)
        src_dir = os.path.join(site_dir, "src")
        
        # We don't actually use this data currently, just archive it
        if request.network in self.networks_fnsls:
            fnsl_network = self.networks_fnsls[request.network]
        else:
            filename = f'network-{unicode_to_b36(request.network.lower())}.fnsl'
            fnsl_network = requests.get(f'http://{self.fnsl_server}/fnsl5.0/{filename}', headers=self.headers).text
            os.makedirs(network_dir, exist_ok=True)
            f = open(os.path.join(network_dir, filename), "w+", encoding="utf-8")
            f.write(fnsl_network)
            f.close()
            self.networks_fnsls[request.network] = fnsl_network
        
        old_site = request.siteFull in self.site_fnsls
        if old_site:
            fnsl_site = self.site_fnsls[request.siteFull]
        elif len(request.site) == 0:
            networkExists = "<frogans-fnsl version='5.0'>" in fnsl_network
            if networkExists:
                print(request.network+"* exists")
            else:
                print(request.network+"* does not exist")
                return []
        else:
            filename = f'network-{unicode_to_b36(request.network.lower())}.site-{unicode_to_b36(request.site.lower())}.fnsl'
            fnsl_site = requests.get(f'http://{self.fnsl_server}/fnsl5.0/{filename}', headers=self.headers).text
            os.makedirs(site_dir, exist_ok=True)
            f = open(os.path.join(site_dir, filename), "w+", encoding="utf-8")
            f.write(fnsl_site)
            f.close()
            self.site_fnsls[request.siteFull] = fnsl_site
        
        try:
            root = ET.fromstring(fnsl_site)
        except Exception as e:
            print("Site "+request.siteFull+" is not registered in beta")
            return []
        site_server = get_server_from_fnsl(root)
        if site_server == None:
            print("Beta site "+request.siteFull+" is not online")
            return []
        if not old_site:
            print("Found beta server "+site_server+" for site "+request.address)
        path = request.path
        if path == None:
            path = root.find(".//file-selector").text

        site_root = f"http://{site_server}/network-{unicode_to_b36(request.network.lower())}.site-{unicode_to_b36(request.site.lower())}"
        res = requests.get(site_root + path, headers=self.headers)
        fpath = os.path.join(src_dir, sanitize_filename(path[1:]))
        if not os.path.exists(fpath):
            os.makedirs(os.path.dirname(fpath), exist_ok=True)

        f = open(fpath, "wb+")
        f.write(res.content)
        f.close()
        
        new_requests = []
        fsdl_dec = re.search(r"<frogans-fsdl version=['\"]([^'\"]+)['\"]>", res.text)
        if fsdl_dec is not None:
            version = fsdl_dec.group(1)
            if version != "4.0":
                print("Unexpected version "+version+" at beta address "+request.address)
            for locMatch in re.finditer(r"(?:file|address)=['\"]([^'\"]+)['\"]", res.text):
                location = locMatch.group(1)
                if location.startswith("/"):
                    location = request.siteFull + location
                elif "*" not in location:
                    location = request.siteFull + "/" + location
                new_requests.append(BetaRequest(location))
        return new_requests

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
    
    if len(locations) == 0:
        return None
    
    fnsl_server_idx = locations.index("public")
    return domain_names[fnsl_server_idx] + ":" + ports[fnsl_server_idx] + directories[fnsl_server_idx]