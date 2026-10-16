"""Hacked, expired or wrong-business websites found after the link check (pipeline/website_blocklist.json; entries can be added there
without code changes). Shared by the app export (washington.py, WA_APP=1) and the website (scripts/make-site.py), so the app and the
site drop the same links. "domain" covers the registered domain and every subdomain, "url" that exact address. Only the link is
dropped; the place stays."""
import json
import os
import re

BLOCKLIST = json.load(open(os.path.join(os.path.dirname(__file__), "website_blocklist.json")))
assert all(b.get("match") in ("domain", "url") and b.get("domain") for b in BLOCKLIST), "website_blocklist.json: each entry needs domain and match"


def blocked(u):
    if not u:
        return False
    bare = re.sub(r"^(?:[a-z][a-z0-9+.-]*:)?//", "", u.strip(), flags=re.I)
    host = bare.split("/")[0].split("?")[0].split("#")[0].split(":")[0].lower().removeprefix("www.")
    for b in BLOCKLIST:
        if b["match"] == "domain":
            d = b["domain"].strip().lower().removeprefix("www.")
            if host == d or host.endswith("." + d):
                return True
        else:
            want = re.sub(r"^(?:https?:)?//(?:www\.)?", "", b["domain"].strip(), flags=re.I).rstrip("/").lower()
            if re.sub(r"^www\.", "", bare, flags=re.I).rstrip("/").lower() == want:
                return True
    return False
