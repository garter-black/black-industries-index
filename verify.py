#!/usr/bin/env python3
"""black-industries-index - verify the committed source against LIVE production, read-only.

    python verify.py

The committed src/index.html is SANITISED: one anchor pointing at the
forbidden domain was removed in the repo copy only; production is
untouched. It therefore CANNOT be byte-equal to live, and this script does
not pretend otherwise.

Instead it proves the claim that actually matters, and proves it exactly:

    sanitise(live)  ==  build(committed source)     byte for byte

where sanitise() is the very function that produced the committed copy. If
those two sides are equal, then the committed source differs from live by
the sanitisation and by nothing else. Any other difference - drift, a
missed injection, a stale build - breaks the equality and is reported.

This is deliberately a round trip rather than "re-insert the anchor at some
offset": computing an insertion point by string search is exactly the kind
of clever step that silently proves nothing.

    python build.py           src/index.html -> dist/index.html
    python build.py --verify  build and print byte count + SHA-256

TRAP 16: never loosen this comparison to make it pass. If the two sides
differ, find the missing layer.
"""
import hashlib, os, re, subprocess, sys, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
LIVE = "https://box.black.industries/"

BEACON = re.compile(rb'<script type="module" src="https://static\.cloudflareinsights\.com[^"]*"[^>]*>\s*</script>\n?', re.I)

# The house rule: no link to the forbidden domain may enter git.
# Remove the anchor element, keep the visible text, so no authored copy is lost.
_ANCHORS = [
    re.compile(r'<a\s+class="row"\s+href="https://theblackgarter\.com\.au"[^>]*>(.*?)</a>', re.S | re.I),
    re.compile(r'<a\s+href="https://theblackgarter\.com\.au"[^>]*>(.*?)</a>', re.S | re.I),
]


def sanitise(doc):
    removed = 0
    for rx in _ANCHORS:
        doc, n = rx.subn(lambda m: m.group(1), doc)
        removed += n
    return doc, removed


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, "build.py")], check=True, capture_output=True)
    built = open(os.path.join(here, "dist", "index.html"), "rb").read()

    live_raw = fetch(LIVE)
    live = BEACON.sub(b"", live_raw)
    live_clean, removed = sanitise(live.decode("utf-8"))
    live_clean = live_clean.encode("utf-8")

    print("live    %d B raw / %d B beacon-free  sha %s" % (len(live_raw), len(live), hashlib.sha256(live).hexdigest()[:24]))
    print("sanitised live (anchors removed: %d)  %d B  sha %s" % (removed, len(live_clean), hashlib.sha256(live_clean).hexdigest()[:24]))
    print("built   %d B                        sha %s" % (len(built), hashlib.sha256(built).hexdigest()[:24]))
    print("byte-equal to raw live: %s   <- EXPECTED False: the repo copy is sanitised" % (built == live))

    if built == live_clean:
        print("RESULT MATCH sanitise(live) == build(committed)  ->  the sanitisation is the ONLY difference")
        return 0
    print("RESULT DIFFER  the sanitisation is not the only difference - investigate")
    for i, (a, b) in enumerate(zip(built, live_clean)):
        if a != b:
            print("first difference at byte %d" % i)
            print("  built         : %r" % built[max(0, i-70):i+70])
            print("  sanitised live: %r" % live_clean[max(0, i-70):i+70])
            break
    else:
        print("one side is a prefix of the other; delta %+d B" % (len(built) - len(live_clean)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
