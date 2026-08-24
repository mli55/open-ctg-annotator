# Deploying the review page (Cloudflare Workers, free tier)

One-time setup (~10 minutes):

1. Install wrangler (needs Node; `brew install node` first if absent):
   npm install -g wrangler
2. Log in to your Cloudflare account:
   wrangler login
3. Create the KV namespace and paste its id into `worker/wrangler.toml`:
   cd worker && wrangler kv namespace create ANN
4. Seed it with the current annotations:
   python3 ../scripts/seed_kv.py
   wrangler kv bulk put seed.json --namespace-id <the id> --remote
5. Set the admin secret (nothing else is needed to let readers in):
   wrangler secret put ADMIN_KEY      # for /export only — never handed out
6. Deploy:
   wrangler deploy
   -> prints https://decel-review.<account>.workers.dev

Send the mailing list ONE plain link, no key:
   https://decel-review.<account>.workers.dev/

Who a reader is comes from the name they type at the top right, and that name
is what decides which blind copy is theirs. Nobody is ever shown anybody
else's blind marks, and before a name is entered nothing blind is served at
all. The reader's browser remembers the name, so coming back to finish picks
their own work up where they left it. The trade this makes for one-link
simplicity: anyone with the URL can open the page, and a reader who types
somebody else's exact name would land in that person's set. The strips are
public PhysioNet data, and nobody has a reason to guess a colleague's name,
so this is a fair trade — but it is a trade, not an oversight.

If per-person links are ever wanted instead, set an ACCESS_KEYS secret — a
JSON object {"<random key>": "reader-id", ...} — and hand each reader
.../?key=<their key>. The page then asks /config, shows that id fixed in the
header and offers no name field, and the id is enforced server-side. Setting
ACCESS_KEYS (or a single shared ACCESS_KEY) also closes the site to anyone
without a key. Record any keys in .keys.local (gitignored), never in a
committed file.

Blind records (BLIND_IDS in worker/wrangler.toml, picked in research_log
blind_lock.json): served with no baseline, no expert overlay and no prefilled
events, and listed first so readers land on them. Annotations live one copy
per reader under ann_blind/<reader>/rec_N. Never seed KV for blind ids
(seed_kv.py only seeds shared pilot records that have annotation files, so the
default flow is already safe). /export returns the shared rec_N keys plus
every ann_blind/<reader>/rec_N set separately.

Maintenance:
- Pull live annotations back for backup/analysis:
  python3 scripts/pull_annotations.py https://decel-review.<account>.workers.dev <ADMIN_KEY>
  then `git add annotations && git commit`.
- Page or data changed? `scripts/sync_from_research_log.sh && cd worker && wrangler deploy`.
- KV wins over the repo once experts start editing — never re-seed KV after
  that without pulling first.
