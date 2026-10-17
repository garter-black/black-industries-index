#!/usr/bin/env python3
"""black-industries-index - verify the committed source against LIVE production, read-only.

    python verify.py

TWO facts make a naive byte comparison fail here, and both are handled
explicitly rather than papered over:

1. The committed src/index.html is SANITISED - one anchor pointing at the
   forbidden domain was removed in the repo copy only; production is
   untouched. It therefore cannot be byte-equal to live.

2. The Cloudflare Web Analytics beacon is present on BOTH sides and its
   count differs between responses. The origin file has one baked in; some
   live responses carry a second one injected at the edge. Stripping the
   beacon from live but not from the build would compare a beacon-free
   document against one containing a beacon, which can never match and
   proves nothing. Both sides are normalised. (Trap 20: never carry a
   normaliser forward without re-deriving it against the new site.)

So the claim proved is the one that matters:

    sanitise(strip_beacons(live))  ==  strip_beacons(build(committed))

Equal on both sides means the committed source differs from live by the
sanitisation and by nothing else. Any other difference - drift, a missed
injection, a stale build - breaks the equality and is reported with the
offset of the first differing byte.

    python build.py           src/index.html -> dist/index.html
    python build.py --verify  build and print byte count + SHA-256

TRAP 16: never loosen this comparison to make it pass. If the two sides
differ, find the missing layer.
"""
import hashlib, os, re, subprocess, sys, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
LIVE = "https://box.black.industries/"

BEACON = re.compile(rb'<script type="module" src="https://static\.cloudflareinsights\.com[^"]*"[^>]*>\s*</script>\n?', re.I)

# House rule: no link to the forbidden domain may enter git.
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
    built_bf = BEACON.sub(b"", built)

    live_raw = fetch(LIVE)
    live_bf = BEACON.sub(b"", live_raw)
    live_clean, removed = sanitise(live_bf.decode("utf-8"))
    live_clean = live_clean.encode("utf-8")

    print("live     %6d B raw / %6d B beacon-free  sha %s" % (len(live_raw), len(live_bf), hashlib.sha256(live_bf).hexdigest()[:24]))
    print("sanitised live (%d anchor removed) %6d B  sha %s" % (removed, len(live_clean), hashlib.sha256(live_clean).hexdigest()[:24]))
    print("built    %6d B raw / %6d B beacon-free  sha %s" % (len(built), len(built_bf), hashlib.sha256(built_bf).hexdigest()[:24]))
    print("byte-equal to raw live: %s   <- EXPECTED False: the repo copy is sanitised and the beacon count varies"
          % (built == live_raw))

    if built_bf == live_clean:
        print("RESULT MATCH sanitise(strip(live)) == strip(build(committed))")
        print("        -> the sanitisation is the ONLY difference from production")
        return 0
    print("RESULT DIFFER  the sanitisation is not the only difference - investigate")
    for i, (a, b) in enumerate(zip(built_bf, live_clean)):
        if a != b:
            print("first difference at byte %d" % i)
            print("  built          : %r" % built_bf[max(0, i-70):i+70])
            print("  sanitised live : %r" % live_clean[max(0, i-70):i+70])
            break
    else:
        print("one side is a prefix of the other; delta %+d B" % (len(built_bf) - len(live_clean)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
