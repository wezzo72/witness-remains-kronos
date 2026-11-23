#!/usr/bin/env python3
"""Project Kronos. Resumable inventory and Wayback submission.

Does not edit source pages. Does not delete earlier manifest lines.
A URL is confirmed only after the Wayback capture returns HTTP 200.
"""
import hashlib, json, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace/kronos")
MANIFEST = ROOT / "manifest"
SNAP = Path("/tmp/kronos-snapshot")
ORIGIN = "https://gods-witness-remains.grok.me"
UA = "ProjectKronos/1.0 (preservation of a public documentary site)"
STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TODAY = MANIFEST / f"discovery-{STAMP}.jsonl"
QUEUE = MANIFEST / f"wayback-{STAMP}.jsonl"
ASSET_EXT = {".pdf", ".epub", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".mp3", ".mp4", ".zip", ".txt", ".csv", ".json", ".ots"}

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_done(path, key="url"):
    done = {}
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            done[row.get(key)] = row
    return done

def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

def fetch(url, method="GET", data=None, timeout=40):
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read() if method != "HEAD" else b""
            return res.status, dict(res.headers), body, res.geturl()
    except urllib.error.HTTPError as err:
        body = err.read() if method != "HEAD" else b""
        return err.code, dict(err.headers), body, url
    except Exception as err:
        return 0, {}, b"", f"{type(err).__name__}: {err}"

def title_of(body):
    m = re.search(br"<title>(.*?)</title>", body, re.I | re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1).decode("utf-8", "replace")).strip()[:300]

def links_of(body, base):
    found = set()
    for raw in re.findall(br'(?:href|src)="([^"]+)"', body, re.I):
        val = raw.decode("utf-8", "replace").replace("&", "&").split("#")[0]
        if not val or val.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absu = urllib.parse.urljoin(base, val)
        found.add(absu.split("#")[0])
    return found

def kind(url):
    path = urllib.parse.urlparse(url).path.lower()
    suf = Path(path).suffix
    if suf in ASSET_EXT:
        return suf.lstrip(".")
    if path.endswith("/") or suf == "":
        return "html"
    return suf.lstrip(".") or "other"

def inventory_one(url):
    status, headers, body, final = fetch(url)
    digest = hashlib.sha256(body).hexdigest() if body else ""
    row = {
        "url": url,
        "final_url": final if status else "",
        "title": title_of(body),
        "type": headers.get("Content-Type", "").split(";")[0] or kind(url),
        "filename": Path(urllib.parse.urlparse(url).path).name or "index.html",
        "location": urllib.parse.urlparse(url).path or "/",
        "discovered": now(),
        "status": status,
        "size": len(body) if body else int(headers.get("Content-Length") or 0),
        "sha256": digest,
        "robots": headers.get("X-Robots-Tag", ""),
        "capture": "not-submitted",
        "wayback": "",
        "failure": "" if status == 200 else (final if status == 0 else f"HTTP {status}"),
    }
    if status == 200 and body and row["type"].startswith("text/html"):
        rel = urllib.parse.urlparse(url).path.strip("/") or "index"
        dest = SNAP / "pages" / (rel.replace("/", "__") + ".html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        row["snapshot"] = str(dest)
        row["outlinks"] = sorted(links_of(body, url))
    return row

def save_wayback(url):
    status, headers, body, final = fetch(
        "https://web.archive.org/save/" + url, timeout=90
    )
    loc = headers.get("Location") or headers.get("location") or ""
    if status in (200, 302) and "web.archive.org/web/" in (loc or final):
        cap = loc or final
        vstatus, _, vbody, _ = fetch(cap, timeout=60)
        ok = vstatus == 200 and (b"<title>" in vbody or b"pdf" in vbody[:20].lower() or len(vbody) > 500)
        return {
            "url": url,
            "submitted": now(),
            "submit_status": status,
            "wayback": cap if ok else "",
            "verify_status": vstatus,
            "confirmed": bool(ok),
            "failure": "" if ok else f"verify HTTP {vstatus}",
        }
    text = body[:240].decode("utf-8", "replace")
    return {
        "url": url,
        "submitted": now(),
        "submit_status": status,
        "wayback": "",
        "verify_status": 0,
        "confirmed": False,
        "failure": text or f"HTTP {status}",
    }

def main():
    MANIFEST.mkdir(parents=True, exist_ok=True)
    locs = [ln.strip() for ln in (ROOT / "sitemap-locs.txt").read_text().splitlines() if ln.strip()]
    done = load_done(TODAY)
    pending = [u for u in locs if u not in done]
    print(f"inventory {len(pending)} of {len(locs)}", flush=True)
    assets = set()
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(inventory_one, u): u for u in pending}
        n = 0
        for fut in as_completed(futs):
            row = fut.result()
            links = row.pop("outlinks", [])
            for link in links:
                host = urllib.parse.urlparse(link).netloc
                if host.endswith("gods-witness-remains.grok.me") and Path(urllib.parse.urlparse(link).path).suffix.lower() in ASSET_EXT:
                    assets.add(link.split("?")[0])
            append(TODAY, row)
            n += 1
            if n % 25 == 0:
                print(f"inventoried {n}", flush=True)
    print(f"assets from pages {len(assets)}", flush=True)
    (MANIFEST / f"assets-{STAMP}.txt").write_text("\n".join(sorted(assets)))
    # asset heads, resumable
    ahead = MANIFEST / f"assets-{STAMP}.jsonl"
    known = load_done(ahead)
    for url in sorted(assets):
        if url in known:
            continue
        status, headers, _, final = fetch(url, method="HEAD")
        append(ahead, {
            "url": url,
            "title": "",
            "type": headers.get("Content-Type", "").split(";")[0],
            "filename": Path(urllib.parse.urlparse(url).path).name,
            "location": urllib.parse.urlparse(url).path,
            "discovered": now(),
            "status": status,
            "size": int(headers.get("Content-Length") or 0),
            "sha256": "",
            "capture": "not-submitted",
            "wayback": "",
            "failure": "" if status == 200 else (final if status == 0 else f"HTTP {status}"),
        })
        time.sleep(0.15)
    # Wayback queue: pages first, then assets. Confirmed rows are never resubmitted.
    confirmed = {r["url"] for r in load_done(QUEUE).values() if r.get("confirmed")}
    # homepage already confirmed in this run's notes if present
    targets = locs + sorted(assets)
    print(f"wayback queue {len(targets)} already confirmed {len(confirmed)}", flush=True)
    delay = 8
    for url in targets:
        if url in confirmed:
            continue
        result = save_wayback(url)
        append(QUEUE, result)
        print(("OK " if result["confirmed"] else "NO ") + url[:90], result.get("failure", "")[:80], flush=True)
        if result["submit_status"] == 429 or "limit" in result["failure"].lower():
            delay = min(delay * 2, 120)
            print(f"backing off {delay}s", flush=True)
        time.sleep(delay)
    print("done", flush=True)

if __name__ == "__main__":
    main()
