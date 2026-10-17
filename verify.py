#!/usr/bin/env python3
"""black-industries-index - verify the committed source against LIVE production, read-only.

    python verify.py

Fetches the live custom domain, strips ONLY the Cloudflare Web Analytics
beacon (a per-request injection), and compares byte-for-byte with the
output of build.py. Reports the exact byte delta if they differ.

TRAP 16: never loosen this comparison to make it pass. If the two sides
differ, find the missing layer.
"""
import hashlib, os, re, subprocess, sys, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
LIVE = "https://box.black.industries/"

BEACON = re.compile(rb'<script type="module" src="https://static\.cloudflareinsights\.com[^"]*"[^>]*>\s*</script>\n?', re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.py")],
                   check=True, capture_output=True)
    dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "index.html")
    built = open(dist, "rb").read()
    live = fetch(LIVE)
    live_nb = BEACON.sub(b"", live)
    print("live   %d B raw / %d B beacon-free  sha %s" % (len(live), len(live_nb), hashlib.sha256(live_nb).hexdigest()[:24]))
    print("built  %d B                     sha %s" % (len(built), hashlib.sha256(built).hexdigest()[:24]))
    if built == live_nb:
        print("RESULT MATCH byte-exact against live")
        return 0
    print("RESULT DIFFER  delta %+d B" % (len(built) - len(live_nb)))
    for i, (a, b) in enumerate(zip(built, live_nb)):
        if a != b:
            print("first difference at byte %d" % i)
            print("  built: %r" % built[max(0, i-60):i+60])
            print("  live : %r" % live_nb[max(0, i-60):i+60])
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
