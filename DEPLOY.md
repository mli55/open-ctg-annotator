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
5. Set the two access secrets (invent two long random strings):
   wrangler secret put ACCESS_KEY     # goes into the expert link
   wrangler secret put ADMIN_KEY      # for /export only
6. Deploy:
   wrangler deploy
   -> prints https://decel-review.<account>.workers.dev

Give experts:  https://decel-review.<account>.workers.dev/?key=<ACCESS_KEY>

Maintenance:
- Pull live annotations back for backup/analysis:
  python3 scripts/pull_annotations.py https://decel-review.<account>.workers.dev <ADMIN_KEY>
  then `git add annotations && git commit`.
- Page or data changed? `scripts/sync_from_research_log.sh && cd worker && wrangler deploy`.
- KV wins over the repo once experts start editing — never re-seed KV after
  that without pulling first.
