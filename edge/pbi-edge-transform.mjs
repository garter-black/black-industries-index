\
// pbi-edge HTMLRewriter transform, reproduced verbatim from the deployed Worker source
// work/witchcraft-identity-lock-20261013/candidates/pbi-edge/worker.js
//   PLAYER_TAG            worker.js:193
//   convaiTag()           worker.js:199-208
//   NETWORK_DEFAULT       worker.js:139
//   LAYOUT                worker.js:616
//   footerBlock = ""      worker.js:634 -- these hosts are absent from SPONSORS,
//                         SPONSORS2 and ORIGIN_LEGAL_HOSTS
//   agentFor() -> default worker.js:150-153 -- these hosts are absent from AGENTS
//
// HTMLRewriter's `end.before(html, {html:true})` serialises the payload with a
// trailing newline, so the injected block lands as `...payload\n</body>`.
// Cloudflare Web Analytics appends its own beacon script after that; it is
// infrastructure, not source, and verify.py removes it before comparing.

export const PLAYER_TAG = '<script src="/_pbi/player.js" defer></script>';

export const LAYOUT =
  "<style>elevenlabs-convai{right:16px!important;bottom:24px!important}" +
  "@media(max-width:640px){elevenlabs-convai{right:10px!important;bottom:76px!important}}</style>";

export const NETWORK_DEFAULT = {
  id: "agent_7601kv76b5cgfq9thvb5mxsdqsw0",
  c1: "#c9c5bb",
  c2: "#0a0a0a",
};

export function convaiTag(a) {
  return (
    "<style>elevenlabs-convai{position:fixed;right:16px;bottom:24px;z-index:2147482000}" +
    "@media(max-width:640px){elevenlabs-convai{bottom:76px;right:10px}}</style>" +
    '<elevenlabs-convai agent-id="' + a.id +
    '" avatar-orb-color-1="' + a.c1 + '" avatar-orb-color-2="' + a.c2 +
    '"></elevenlabs-convai>' +
    '<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>'
  );
}

// Pure string transform. The Worker uses HTMLRewriter (DOM-aware); this page is a
// single flat document with exactly one </head> and one </body>, so string surgery on
// the end tags is equivalent - and it is what verify.py proves byte-for-byte against
// three independent live fetches.
export function transform(html, host) {
  if (typeof host !== "string" || !host) throw new Error("host required");
  let out = html;
  // ExistingTagDetector: never inject a second player tag.
  if (!out.includes("/_pbi/player.js")) {
    out = out.replace(/<\/head\s*>/i, PLAYER_TAG + "</head>");
  }
  const bodyPayload = LAYOUT;              // footerBlock is "" for these hosts
  const convaiPayload = convaiTag(NETWORK_DEFAULT);
  out = out.replace(/<\/body\s*>/i, bodyPayload + convaiPayload + "\n</body>");
  return out;
}
