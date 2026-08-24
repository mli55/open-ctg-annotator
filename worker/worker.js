// Decel Review — Cloudflare Worker backend
// Routes: /status, /ann/rec_N.json, POST /save, /export (admin), everything else -> static assets.
// Access: every request must carry ?key=<a key in ACCESS_KEYS>, ?key=<ACCESS_KEY> or ?key=<ADMIN_KEY>.
//
// Blind records (ids in the BLIND_IDS var): annotations are kept one copy per
// reader under ann_blind/<reader>/rec_N. Who the reader is comes from a
// personal key when ACCESS_KEYS issues one, and otherwise from the name they
// enter in the header — the case where one shared link goes to a mailing list.
// Either way a request only ever names ONE reader, and only that reader's copy
// is served: nobody is shown anybody else's blind marks, and with no name at
// all nothing blind is served. Shared (non-blind) records keep one rec_N copy.

const NAME_RE = /^[a-zA-Z0-9_-]{1,40}$/;

function json(o, s = 200) {
  return new Response(JSON.stringify(o), {
    status: s,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  });
}

function keyOwner(env, key) {          // annotator id a personal key maps to, else null
  if (!env.ACCESS_KEYS || !key) return null;
  try {
    const who = JSON.parse(env.ACCESS_KEYS)[key];
    return typeof who === 'string' && NAME_RE.test(who) ? who : null;
  } catch { return null; }
}

/* Which blind set belongs to this request. A personal key names its reader;
   with the shared link they name themselves in the header. Unnamed is a real
   answer — it means no blind set is theirs yet, so none is served.
   Case-folded on purpose: "Jake" and "jake" are one reader coming back on a
   second machine, and telling them apart would silently hand them an empty
   page and lose the reading they already did. */
function readerKey(url, who, declared) {
  const n = who ?? declared ?? url.searchParams.get('annotator');
  return typeof n === 'string' && NAME_RE.test(n) ? n.toLowerCase() : null;
}

function blindIds(env) {
  return new Set(String(env.BLIND_IDS || '').split(',')
    .map(s => parseInt(s, 10)).filter(Number.isFinite));
}

function summ(a) {
  const decels = a.decels || [], cons = a.contractions || [];
  return {
    decels: decels.length,
    decels_done: decels.filter(e => e.review !== 'pending').length,
    cons: cons.length,
    cons_done: cons.filter(e => e.review !== 'pending').length,
    n_flag: [...decels, ...cons].filter(e => e.flag).length,
    updated: a.updated,
  };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const key = url.searchParams.get('key') || '';
    const isAdmin = env.ADMIN_KEY && key === env.ADMIN_KEY;
    const who = keyOwner(env, key);
    const locked = env.ACCESS_KEY || env.ACCESS_KEYS;
    if (locked && !isAdmin && who === null && key !== env.ACCESS_KEY)
      return new Response('Access denied — please use the exact link you were given.', { status: 403 });

    const p = url.pathname;
    const blind = blindIds(env);

    /* Who the reader is, answered by the key alone. The page shows it fixed in
       the header and offers nothing to type: a name field would let two links
       file their work under one name, which is exactly what the blind sets are
       arranged to prevent. */
    if (p === '/config') return json({ annotator: who, locked: !!who });

    if (p === '/status') {
      const out = {};
      const list = await env.ANN.list({ prefix: 'rec_' });
      for (const k of list.keys) {
        const a = await env.ANN.get(k.name, 'json');
        if (a) out[String(a.record_id)] = summ(a);
      }
      const me = readerKey(url, who);
      if (me) {                       // blind records: only your own copies
        const bl = await env.ANN.list({ prefix: `ann_blind/${me}/` });
        for (const k of bl.keys) {
          const a = await env.ANN.get(k.name, 'json');
          if (a) out[String(a.record_id)] = summ(a);
        }
      }
      return json(out);
    }

    if (p.startsWith('/ann/')) {
      const m = p.match(/^\/ann\/(rec_(\d{1,6}))\.json$/);
      if (!m) return json({ error: 'bad path' }, 400);
      const me = readerKey(url, who);
      const kk = blind.has(parseInt(m[2], 10))
        ? (me ? `ann_blind/${me}/${m[1]}` : null)   // unnamed -> nothing is yours
        : m[1];
      const a = kk && await env.ANN.get(kk, 'json');
      return a ? json(a) : json({ error: 'not annotated yet' }, 404);
    }

    if (p === '/save' && req.method === 'POST') {
      let ann;
      try { ann = await req.json(); } catch { return json({ error: 'bad json' }, 400); }
      const rid = parseInt(ann.record_id);
      if (!Number.isFinite(rid)) return json({ error: 'bad record_id' }, 400);
      if (!NAME_RE.test(ann.annotator || '')) return json({ error: 'annotator name required' }, 400);
      const base = ann.base_updated; delete ann.base_updated;
      let kk = 'rec_' + rid;
      /* On a shared record only the "last saved by" field is settled by the
         key. History is left exactly as sent: those lines carry the names of
         earlier reviewers, and rewriting them would hand one reviewer's work
         to whoever saved last. */
      if (who) ann.annotator = who;
      if (blind.has(rid)) {
        const me = readerKey(url, who, ann.annotator);
        if (!me) return json({ error: 'enter your name before marking a blind record' }, 400);
        /* The folder is case-folded; the name shown stays as it was typed.
           When a personal key issued the identity it also overrides what was
           typed — a blind set has exactly one author, and the export is only
           worth reading if every line says who that was. */
        if (who) {
          ann.annotator = who;
          if (Array.isArray(ann.history)) for (const h of ann.history) h.by = who;
        }
        kk = `ann_blind/${me}/rec_${rid}`;
      }
      const cur = await env.ANN.get(kk, 'json');
      if (cur && cur.updated != null && cur.updated !== base)
        return json({ error: 'conflict', updated: cur.updated }, 409);
      await env.ANN.put(kk, JSON.stringify(ann));
      return json({ ok: true });
    }

    if (p === '/export') {
      if (!isAdmin) return json({ error: 'admin key required' }, 403);
      const out = {};
      for (const prefix of ['rec_', 'ann_blind/']) {
        const list = await env.ANN.list({ prefix });
        for (const k of list.keys) out[k.name] = await env.ANN.get(k.name, 'json');
      }
      return json(out);
    }

    return env.ASSETS.fetch(req);   // index.html, /pilot.json, /data/rec_N.json
  },
};
