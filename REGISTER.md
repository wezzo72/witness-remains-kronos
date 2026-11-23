# PROJECT: THE WITNESS REMAINS — THE GREAT RECKONING

Original website: https://gods-witness-remains.grok.me

Archival destination: Internet Archive / Wayback Machine

Date of this run: 23 November 2026

This is a finding aid for the preservation work. It is not a court and not a verdict. Allegations in the source stay allegations.

## Confirmed capture

| Source | Wayback | Verified |
|---|---|---|
| https://gods-witness-remains.grok.me/ | https://web.archive.org/web/20261123123407/https://gods-witness-remains.grok.me/ | HTTP 200. Title: God’s Witness Remains \| The Great Reckoning. 333,383 bytes. |

No other URL is claimed as archived. The rest are in a running queue. A submission is not a capture.

## Discovery, verified from the live site

| Item | Count |
|---|---|
| Sitemap pages fetched | 445 |
| HTTP 200 | 445 |
| HTTP failed | 0 |
| SHA-256 computed | 445 |
| HTML bytes | 119,556,080 |
| Embedded files linked from those pages | 539 |

Embedded files by type: 251 jpg, 205 pdf, 24 txt, 19 ots, 10 js, 7 csv, 5 zip, 4 css, 4 json, 4 epub, 3 png, 2 mp3, 1 svg.

Each page row is in `manifest/discovery-2026-11-23.jsonl` with URL, title, filename, type, path, time, status, size, and SHA-256.

## Not done, and why

- Internet Archive item upload needs an archive.org account and S3 keys. None were supplied. No collection URL is invented.
- `robots.txt` allows all crawlers. Live responses also sent `x-robots-tag: noindex`. Save Page Now still stored the homepage. Later captures will be checked the same way.
- GitHub Actions cannot be added until the preservation repository accepts a workflow. The weekly run is already scheduled in this assistant.

## Method

`preserve.py` reads the sitemap, fetches each page, hashes it, lists embedded files, then submits URLs to `https://web.archive.org/save/` with a delay. It appends results. It does not delete earlier lines. A row is confirmed only when the Wayback URL itself returns HTTP 200.
