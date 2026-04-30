# -*- coding: utf-8 -*-
import os
import requests
import re
import defusedxml.ElementTree as ET # Can swap for Python's built-in, this just provides a bit more security
import hashlib
from helpers import *

class AlphaRequest(FrogansRequest):
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

class AlphaScraper(Scraper):
    def __init__(self, settings: dict):
        self.output_dir = settings['output_dir']
        self.headers = settings['headers']
        self.fal_server = settings['fal_server']
        self.site_fnsls = {}
        self.visited = set()
    
    def scrape(self, request: FrogansRequest) -> list[FrogansRequest]:
        if not isinstance(request, AlphaRequest):
            raise TypeError("Request for "+str(request)+" is not an alpha request!")
        if len(request.site) == 0:
            print("Network-only alpha requests aren't supported, skipping ("+str(request)+")")
            return []
        if request.address in self.visited:
            return []
        self.visited.add(request.address)
        print("Visiting "+request.address+" (A)")
        
        site_dir = os.path.join(self.output_dir, request.network, request.site)
        old_site = request.siteFull in self.site_fnsls
        if old_site:
            fnsl_site = self.site_fnsls[request.siteFull]
        else:
            fnsl_enc = f'{unicode_to_b36(request.network.lower())}.lookup.{unicode_to_b36(request.site.lower())}.fnsl'
            sha1 = hashlib.sha1(fnsl_enc.encode()).hexdigest()
            fnsl_site = requests.get(f'http://{self.fal_server}/{sha1[0:2]}/{sha1[2:4]}/{sha1[4:6]}/{fnsl_enc}', headers=self.headers).text
            os.makedirs(site_dir, exist_ok=True)
            f = open(os.path.join(site_dir, "network-"+fnsl_enc), "w+", encoding="utf-8")
            f.write(fnsl_site)
            f.close()
            self.site_fnsls[request.siteFull] = fnsl_site
        
        try:
            root = ET.fromstring(fnsl_site)
        except Exception as _:
            print("Site "+request.siteFull+" is not registered in alpha")
            return []
        site_server = get_server_from_fnsl(root)
        if site_server == None:
            print("Alpha site "+request.siteFull+" is not online")
            return []
        if not old_site:
            print("Found alpha server "+site_server+ " for site "+request.siteFull)
        if request.path == None:
            request.path = root.find(".//home-slide-file").text
        
        res = requests.get("http://" + site_server + request.path, headers=self.headers)
        fpath = os.path.join(site_dir, "src", sanitize_filename(request.path[1:]))
        if not os.path.exists(fpath):
            os.makedirs(os.path.dirname(fpath), exist_ok=True)

        f = open(fpath, "wb+")
        f.write(res.content)
        f.close()
        
        new_requests = []
        fsdl_dec = re.search(r"<frogans-fsdl version=['\"]([^'\"]+)['\"]>", res.text)
        if fsdl_dec is not None:
            version = fsdl_dec.group(1)
            if version != "3.0":
                print("Unexpected version "+version+" at alpha address "+request.address)
            for locMatch in re.finditer(r"(?:name|address)=['\"]([^'\"]+)['\"]", res.text):
                location = locMatch.group(1)
                if location.startswith("/"):
                    location = request.siteFull + location
                elif "*" not in location:
                    location = request.siteFull + "/" + location
                new_requests.append(AlphaRequest(location))
        return new_requests


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
    
    if len(locations) == 0:
        return None
    
    fnsl_server_idx = locations.index("public")
    return domain_names[fnsl_server_idx] + ":" + ports[fnsl_server_idx] + directories[fnsl_server_idx]