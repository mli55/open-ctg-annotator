// Decel Review — Cloudflare Worker backend
// Routes: /status, /ann/rec_N.json, POST /save, /export (admin), everything else -> static assets.
// Access: every request must carry ?key=<ACCESS_KEY> (or <ADMIN_KEY>).

const NAME_RE = /^[a-zA-Z0-9_-]{1,40}$/;

function json(o, s = 200) {
  return new Response(JSON.stringify(o), {
    status: s,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  });
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const key = url.searchParams.get('key') || '';
    const isAdmin = env.ADMIN_KEY && key === env.ADMIN_KEY;
    if (env.ACCESS_KEY && key !== env.ACCESS_KEY && !isAdmin)
      return new Response('Access denied — please use the exact link you were given.', { status: 403 });

    const p = url.pathname;

    if (p === '/status') {
      const out = {};
      const list = await env.ANN.list({ prefix: 'rec_' });
      for (const k of list.keys) {
        const a = await env.ANN.get(k.name, 'json');
        if (!a) continue;
        const decels = a.decels || [], cons = a.contractions || [];
        out[String(a.record_id)] = {
          decels: decels.length,
          decels_done: decels.filter(e => e.review !== 'pending').length,
          cons: cons.length,
          cons_done: cons.filter(e => e.review !== 'pending').length,
          n_flag: [...decels, ...cons].filter(e => e.flag).length,
          updated: a.updated,
        };
      }
      return json(out);
    }

    if (p.startsWith('/ann/')) {
      const m = p.match(/^\/ann\/(rec_\d{1,6})\.json$/);
      if (!m) return json({ error: 'bad path' }, 400);
      const a = await env.ANN.get(m[1], 'json');
      return a ? json(a) : json({ error: 'not annotated yet' }, 404);
    }

    if (p === '/save' && req.method === 'POST') {
      let ann;
      try { ann = await req.json(); } catch { return json({ error: 'bad json' }, 400); }
      const rid = parseInt(ann.record_id);
      if (!Number.isFinite(rid)) return json({ error: 'bad record_id' }, 400);
      if (!NAME_RE.test(ann.annotator || '')) return json({ error: 'annotator name required' }, 400);
      const base = ann.base_updated; delete ann.base_updated;
      const cur = await env.ANN.get('rec_' + rid, 'json');
      if (cur && cur.updated != null && cur.updated !== base)
        return json({ error: 'conflict', updated: cur.updated }, 409);
      await env.ANN.put('rec_' + rid, JSON.stringify(ann));
      return json({ ok: true });
    }

    if (p === '/export') {
      if (!isAdmin) return json({ error: 'admin key required' }, 403);
      const out = {};
      const list = await env.ANN.list({ prefix: 'rec_' });
      for (const k of list.keys) out[k.name] = await env.ANN.get(k.name, 'json');
      return json(out);
    }

    return env.ASSETS.fetch(req);   // index.html, /pilot.json, /data/rec_N.json
  },
};
