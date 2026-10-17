#!/usr/bin/env python3
"""black-industries-index - verify the committed source against LIVE production, read-only.

    python verify.py

The committed src/index.html is SANITISED: one anchor linking the forbidden
domain was removed in the repo copy only, production untouched. It therefore
CANNOT be byte-equal to live, and this script does not pretend otherwise.

Instead it proves the exact opposite claim, which is the one that matters:
**the only difference between this repo's output and live is that removed
anchor.** It re-inserts the anchor at its known position and requires the
result to equal live byte-for-byte. If anything else differs, RESULT DIFFER.

    python build.py           src/index.html -> dist/index.html
    python build.py --verify  build and print byte count + SHA-256

TRAP 16: never loosen this comparison to make it pass. If the two sides
differ, find the missing layer.
"""
import hashlib, os, re, subprocess, sys, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
LIVE = "https://box.black.industries/"

BEACON = re.compile(rb'<script type="module" src="https://static\.cloudflareinsights\.com[^"]*"[^>]*>\s*</script>\n?', re.I)

# The exact anchor removed in the repo copy (house rule: no link to the
# forbidden domain may be committed). Restoring it must reproduce live.
ANCHOR = b'<a class="row" href="https://theblackgarter.com.au">'


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, "build.py")], check=True, capture_output=True)
    built = open(os.path.join(here, "dist", "index.html"), "rb").read()
    live = BEACON.sub(b"", fetch(LIVE))

    print("live   %d B beacon-free  sha %s" % (len(live), hashlib.sha256(live).hexdigest()[:24]))
    print("built  %d B               sha %s" % (len(built), hashlib.sha256(built).hexdigest()[:24]))
    print("byte-equal to live: %s   <- EXPECTED False: the repo copy is sanitised" % (built == live))

    idx = built.find(b'\n    \r\n      <div class="idx">01.06</div>')
    if idx < 0:
        idx = built.find(b'<div class="idx">01.06</div>')
        start = built.rfind(b'<a', 0, idx)
        restored = built[:start] + ANCHOR + built[start:]
    else:
        cut = built.rfind(b"\n", 0, idx) + 1
        restored = built[:cut] + ANCHOR + built[cut:]

    print("restored-with-anchor %d B  sha %s" % (len(restored), hashlib.sha256(restored).hexdigest()[:24]))
    if restored == live:
        print("RESULT MATCH the ONLY difference is the removed forbidden anchor")
        return 0
    print("RESULT DIFFER  the sanitisation is not the only difference - investigate")
    for i, (a, b) in enumerate(zip(restored, live)):
        if a != b:
            print("first difference at byte %d" % i)
            print("  restored: %r" % restored[max(0, i-70):i+70])
            print("  live    : %r" % live[max(0, i-70):i+70])
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
