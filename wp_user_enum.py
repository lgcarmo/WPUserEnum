#!/usr/bin/env python3
import argparse
import requests
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
from termcolor import cprint, colored
import tldextract


# --- Métodos de enumeração ---
def check_response(resp):
    if resp.status_code == 200:
        return resp.text
    else:
        cprint(f"[!] Received status code {resp.status_code}", "red")
        return None

def enumerate_via_rest_api(base_url, session):
    url = urljoin(base_url, '/wp-json/wp/v2/users')
    cprint(f"[+] Trying REST API: {url}", "cyan")
    resp = session.get(url)
    if check_response(resp):
        try:
            data = resp.json()
            for user in data:
                cprint(f" - ID: {user.get('id')} | Name: {user.get('name')} | Slug: {user.get('slug')}", "green")
        except:
            cprint("[!] Failed to parse JSON", "red")

def enumerate_via_author_param(base_url, session):
    cprint(f"[+] Trying ?author=ID", "cyan")
    for i in range(1, 11):
        url = f"{base_url}/?author={i}"
        resp = session.get(url, allow_redirects=True)
        if "/author/" in resp.url:
            username = resp.url.rstrip('/').split('/')[-1]
            cprint(f" - ID {i} ➔ {username}", "green")

def enumerate_via_rss(base_url, session):
    url = urljoin(base_url, '/feed/')
    cprint(f"[+] Trying RSS feed: {url}", "cyan")
    resp = session.get(url)
    if check_response(resp):
        usernames = set()
        for line in resp.text.splitlines():
            if "<dc:creator>" in line:
                user = line.strip().replace("<dc:creator>", "").replace("</dc:creator>", "")
                usernames.add(user)
        for u in usernames:
            cprint(f" - {u}", "green")

def enumerate_via_at_mentions(base_url, session):
    url = urljoin(base_url, '/?s=@')
    cprint(f"[+] Trying @ mention search: {url}", "cyan")
    resp = session.get(url)
    if check_response(resp):
        found = set()
        for line in resp.text.splitlines():
            if '@' in line and 'author' in line:
                found.add(line.strip())
        for match in found:
            cprint(f" - {match}", "green")

def enumerate_via_login_error(base_url, session, userlist):
    url = urljoin(base_url, '/wp-login.php')
    cprint(f"[+] Trying login form error message enumeration", "cyan")
    for user in userlist:
        data = {'log': user, 'pwd': 'wrongpassword', 'wp-submit': 'Log In'}
        resp = session.post(url, data=data)
        if 'invalid username' not in resp.text.lower():
            cprint(f" - Possible valid username: {user}", "green")

def enumerate_via_xmlrpc(base_url, session, userlist):
    url = urljoin(base_url, '/xmlrpc.php')
    cprint(f"[+] Trying XML-RPC user enumeration: {url}", "cyan")
    for user in userlist:
        payload = f"""<?xml version="1.0"?>
        <methodCall>
            <methodName>wp.getUsersBlogs</methodName>
            <params>
                <param><value><string>{user}</string></value></param>
                <param><value><string>wrongpass</string></value></param>
            </params>
        </methodCall>"""
        headers = {'Content-Type': 'application/xml'}
        resp = session.post(url, data=payload, headers=headers)
        if 'isAdmin' in resp.text:
            cprint(f"[+] Valid user found: {user}", "green")
        else:
            cprint(f"[-] {user} not found or method not available", "yellow")

def enumerate_via_rest_api_search(base_url, session, userlist):
    ext = tldextract.extract(base_url)
    second_level = ext.domain                 # ex: 'elopar'
    domain_full = ext.registered_domain       # ex: 'elopar.com.br'

    api_url = f"https://api.{second_level}.com"
    fallback_url = f"https://{domain_full}"

    cprint(f"[+] Trying REST API with search filter on {api_url}...", "cyan")
    for user in userlist:
        search_email = user if "@" in user else f"{user}@{domain_full}"
        url = f"{api_url}/wp-json/wp/v2/users?search={search_email}"
        cprint(url, "cyan")
        try:
            resp = session.get(url)
            resp.raise_for_status()
        except requests.exceptions.RequestException:
            cprint(f"[!] Failed to reach {api_url}, falling back to {fallback_url}", "yellow")
            url = f"{fallback_url}/wp-json/wp/v2/users?search={search_email}"
            try:
                resp = session.get(url)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                cprint(f"[!] Failed fallback request: {e}", "red")
                continue

        try:
            data = resp.json()
            if data:
                for u in data:
                    cprint(f" - Found for {search_email} ➔ ID: {u.get('id')} | Slug: {u.get('slug')}", "green")
            else:
                cprint(f" - Not found: {search_email}", "yellow")
        except:
            cprint("[!] Failed to parse JSON", "red")

# --- Execução ---
def run_enumeration(url, proxy, methods, userlist):
    base_url = url.rstrip('/')
    session = requests.Session()
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}

    cprint(f"\n=== Target: {base_url} ===", "magenta", attrs=["bold"])

    for key, func in methods.items():
        cprint(f"\n--- Method {key} ---", "blue")
        if key in ["5", "6", "7"]:
            func(base_url, session, userlist)
        else:
            func(base_url, session)

def main():
    parser = argparse.ArgumentParser(description="WordPress User Enumeration Tool")
    parser.add_argument("-u", "--url", help="Single target URL (e.g., https://example.com)")
    parser.add_argument("-l", "--list", help="File with list of target URLs")
    parser.add_argument("-m", "--method", help="Method number (1-7) or 'all'", default="all")
    parser.add_argument("-t", "--threads", help="Number of threads for list mode", type=int, default=5)
    parser.add_argument("--proxy", help="Proxy (e.g., http://127.0.0.1:8080)", default=None)
    parser.add_argument("--userlist", help="File with list of usernames or emails to test", default=None)
    args = parser.parse_args()

    all_methods = {
        "1": enumerate_via_rest_api,
        "2": enumerate_via_author_param,
        "3": enumerate_via_rss,
        "4": enumerate_via_at_mentions,
        "5": enumerate_via_login_error,
        "6": enumerate_via_xmlrpc,
        #"7": enumerate_via_rest_api_search
    }

    if args.method == "all":
        selected_methods = all_methods
    elif args.method in all_methods:
        selected_methods = {args.method: all_methods[args.method]}
    else:
        cprint("[!] Invalid method selected", "red")
        return

    userlist = ['admin', 'test', 'wordpress']
    if args.userlist:
        with open(args.userlist, "r") as f:
            userlist = [line.strip() for line in f if line.strip()]

    if args.url:
        if not args.url.startswith("http"):
            args.url = "https://" + args.url
        run_enumeration(args.url, args.proxy, selected_methods, userlist)
    elif args.list:
        with open(args.list, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
        urls = [("https://" + url if not url.startswith("http") else url) for url in urls]
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            for url in urls:
                executor.submit(run_enumeration, url, args.proxy, selected_methods, userlist)
    else:
        cprint("[!] You must provide either a URL (-u) or a list file (-l)", "red")

main()
