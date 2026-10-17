#!/usr/bin/env python3
"""black-industries-index - rebuild the pbi-edge output from committed source.

    python build.py           src/index.html -> dist/index.html
    python build.py --verify  build and print byte count + SHA-256

src/index.html is the source of truth. dist/ is a build artifact and is
git-ignored (plan sec.1).

This lane is read-only against Cloudflare: it never deploys and never
changes DNS. The edge constants below are verbatim from
edge/pbi-edge-transform.mjs, which is verbatim from the deployed
pbi-edge Worker.

TRAP 19: LAYOUT below ends in TWO closing braces - one closes
"elevenlabs-convai{" and one closes "@media(...){" . Never generate this
constant through str.format(); it would consume one brace and the build
would emit 606 B where live emits 608 B.
"""
import hashlib, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "index.html")
DIST = os.path.join(ROOT, "dist")
OUT = os.path.join(DIST, "index.html")

PLAYER_TAG = '<script src="/_pbi/player.js" defer></script>'

# NOTE: ends in }}</style> - two braces. See the Trap 19 note above.
LAYOUT = ("<style>elevenlabs-convai{right:16px!important;bottom:24px!important}"
          "@media(max-width:640px){elevenlabs-convai{right:10px!important;bottom:76px!important}}</style>")

NETWORK_DEFAULT = ("agent_7601kv76b5cgfq9thvb5mxsdqsw0", "#c9c5bb", "#0a0a0a")


def convai_tag(a):
    aid, c1, c2 = a
    return ("<style>elevenlabs-convai{position:fixed;right:16px;bottom:24px;z-index:2147482000}"
            "@media(max-width:640px){elevenlabs-convai{bottom:76px;right:10px}}</style>"
            '<elevenlabs-convai agent-id="' + aid +
            '" avatar-orb-color-1="' + c1 + '" avatar-orb-color-2="' + c2 +
            '"></elevenlabs-convai>'
            '<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>')


def transform(html, agent=NETWORK_DEFAULT):
    out = html
    if "/_pbi/player.js" not in out:
        out = re.sub(r"</head\s*>", PLAYER_TAG + "</head>", out, count=1, flags=re.I)
    out = re.sub(r"</body\s*>", LAYOUT + convai_tag(agent) + "</body>", out, count=1, flags=re.I)
    return out


def main():
    origin = open(SRC, "rb").read().decode("utf-8")
    built = transform(origin).encode("utf-8")
    os.makedirs(DIST, exist_ok=True)
    # newline="" so Windows does not convert LF to CRLF (Trap 9)
    with open(OUT, "wb") as f:
        f.write(built)
    if "--verify" in sys.argv:
        print("origin %d B  sha %s" % (len(origin.encode("utf-8")),
                                        hashlib.sha256(origin.encode("utf-8")).hexdigest()))
        print("built  %d B  sha %s" % (len(built), hashlib.sha256(built).hexdigest()))
        return 0
    print("wrote %s  %d B  sha %s" % (OUT, len(built), hashlib.sha256(built).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
