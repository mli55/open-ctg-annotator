// The annotator used to live here. It moved to a domain that hospital web
// filters do not block, and the two copies must not both be writable: work
// saved against this one would sit in a KV namespace nobody reads again.
// So every request is sent on, path and query intact, and nothing here can
// be annotated any more. The old KV namespace is left in place untouched as
// a backup.
//
// 302 rather than 301 on purpose: a permanent redirect is cached by browsers
// for a long time and is awkward to take back, and the new home is a
// borrowed domain.
const NEW_HOME = 'https://decel.sensingschool.org';

export default {
  async fetch(req) {
    const url = new URL(req.url);
    return Response.redirect(NEW_HOME + url.pathname + url.search, 302);
  },
};
