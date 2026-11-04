#!/usr/bin/env python3
"""Post the next queued article to theworldin.wordpress.com via the WordPress.com REST API.

Usage:
  python3 post_article.py            # post next queued article
  python3 post_article.py --dry-run  # parse next article, show what would post

Reads:
  config.json   {site, status: "draft"|"publish"}
  .wp_token     WordPress.com OAuth2 bearer token (chmod 600)
  queue/NN-*.md first line "TITLE: ...", blank line, then HTML body

On success moves the file to posted/ and records it in state.json.
"""
import json
import os
import shutil
import sys
import html as html_module
import http.client
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))

def load_config():
    with open(os.path.join(BASE, "config.json")) as f:
        return json.load(f)

def next_queued():
    qdir = os.path.join(BASE, "queue")
    files = sorted(f for f in os.listdir(qdir) if f.endswith(".md"))
    return os.path.join(qdir, files[0]) if files else None

def parse_article(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    if not lines[0].startswith("TITLE:"):
        raise ValueError(f"{path}: first line must start with 'TITLE:'")
    title = lines[0][len("TITLE:"):].strip()
    body = "\n".join(lines[2:]).strip()
    if not title or not body:
        raise ValueError(f"{path}: missing title or body")
    return title, body

def _norm_title(t):
    """Canonicalize a title for comparison: decode HTML entities, fold
    typographic punctuation WordPress inserts, collapse whitespace."""
    t = html_module.unescape(t or "")
    for a, b in [("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u2026", "...")]:
        t = t.replace(a, b)
    return " ".join(t.split())

def verify_by_title(site, token, title, status):
    """Confirm a post exists after an unreadable POST response.

    Returns a dict like the posts/new response, or raises if the post
    cannot be found — so a successful post is never recorded twice
    and an uncertain post is never recorded at all.
    """
    posts = []
    for st in dict.fromkeys([status, "publish", "draft"]):
        url = (f"https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts"
               f"?status={st}&number=20&fields=ID,title,URL,status")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            posts.extend(json.load(resp).get("posts", []))
    # de-dupe by ID while preserving order
    seen, uniq = set(), []
    for p in posts:
        if p.get("ID") not in seen:
            seen.add(p.get("ID"))
            uniq.append(p)
    want = _norm_title(title)
    for p in uniq:
        if _norm_title(p.get("title", "")) == want:
            return p
    raise RuntimeError(
        "POST response was unreadable and the post was not found in the "
        f"recent {status} listing — not recording; investigate before re-posting."
    )

def post(site, token, title, body, status):
    url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/new"
    payload = json.dumps({"title": title, "content": body, "status": status}).encode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"WordPress API HTTP {e.code}: {detail}")
    except http.client.IncompleteRead as e:
        # Server closed the connection mid-body; the post may still have
        # been created. Never guess — verify via a read-only listing.
        print("WARNING: incomplete POST response; verifying via draft listing...")
        return verify_by_title(site, token, title, status)
    try:
        return json.loads(raw)
    except ValueError:
        print("WARNING: unparseable POST response; verifying via draft listing...")
        return verify_by_title(site, token, title, status)

def record_posted(path, result):
    posted_dir = os.path.join(BASE, "posted")
    os.makedirs(posted_dir, exist_ok=True)
    shutil.move(path, os.path.join(posted_dir, os.path.basename(path)))
    state_path = os.path.join(BASE, "state.json")
    state = {}
    if os.path.exists(state_path):
        with open(state_path) as f:
            state = json.load(f)
    state.setdefault("posted", []).append({
        "file": os.path.basename(path),
        "id": result.get("ID"),
        "url": result.get("URL"),
        "status": result.get("status"),
    })
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

def main():
    dry = "--dry-run" in sys.argv
    cfg = load_config()
    path = next_queued()
    if not path:
        print("QUEUE_EMPTY: no articles waiting in queue/")
        return 0
    title, body = parse_article(path)
    print(f"NEXT: {os.path.basename(path)}")
    print(f"TITLE: {title} ({len(body)} chars)")
    if dry:
        print("DRY_RUN: not posting")
        return 0
    token_path = os.path.join(BASE, ".wp_token")
    if not os.path.exists(token_path):
        print("NO_TOKEN: .wp_token not set up yet — article staged, not posted")
        return 2
    with open(token_path) as f:
        token = f.read().strip()
    result = post(cfg["site"], token, title, body, cfg.get("status", "draft"))
    record_posted(path, result)
    print(f"POSTED: {result.get('URL')} (status={result.get('status')})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
