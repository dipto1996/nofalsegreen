// Reproduce data/real_lca/sample_120.csv from DOL's public LCA disclosure file.
//
// DOL's site refuses scripted downloads, so this runs in a browser: open
// https://www.dol.gov/agencies/eta/foreign-labor/performance, paste this into the
// developer console, and await the result. It streams the workbook, keeps rows by
// a fixed rule, and returns the CSV and its SHA-256, which must equal the one in
// PROVENANCE.md. Employer, FEIN and contact or attorney columns are never read.
// This is the exact procedure used on 2026-10-06 (two console steps, joined here).
(async () => {
  const fflate = await import('https://cdn.jsdelivr.net/npm/fflate@0.8.2/esm/browser.js');
  const buf = new Uint8Array(await (await fetch('https://www.dol.gov//media/LCA_Disclosure_Data_FY2026_Q3.xlsx')).arrayBuffer());
  // Step 1: keep sheet row r iff (r * 2654435761 mod 2^32) mod 300 == 0 (and the header).
  const KEEP = r => r === 1 || (((Math.imul(r, 2654435761) >>> 0) % 300) === 0);
  function streamEntry(name, onText) {
    return new Promise((resolve, reject) => {
      const uz = new fflate.Unzip(); uz.register(fflate.UnzipInflate); let found = false;
      uz.onfile = f => { if (f.name === name) { found = true; const dec = new TextDecoder();
        f.ondata = (err, chunk, final) => { if (err) return reject(err); onText(dec.decode(chunk, {stream: !final})); if (final) resolve(); }; f.start(); } };
      const step = 1 << 22;
      for (let i = 0; i < buf.length; i += step) uz.push(buf.subarray(i, Math.min(buf.length, i + step)), i + step >= buf.length);
      if (!found) reject(new Error('no ' + name));
    });
  }
  const rows = {}; let carry = ''; let nrows = 0; const need = new Set();
  await streamEntry('xl/worksheets/sheet1.xml', txt => { carry += txt; let end;
    while ((end = carry.indexOf('</row>')) >= 0) { const seg = carry.slice(0, end); carry = carry.slice(end + 6);
      const m = seg.match(/<row[^>]*\sr="(\d+)"/); if (!m) continue; const r = +m[1]; nrows = Math.max(nrows, r); if (!KEEP(r)) continue;
      const cells = {};
      for (const c of seg.matchAll(/<c r="([A-Z]+)\d+"([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) { const col = c[1], attrs = c[2], inner = c[3] || '';
        const v = (inner.match(/<v>([\s\S]*?)<\/v>/) || [])[1];
        if (/t="s"/.test(attrs) && v !== undefined) { cells[col] = {s: +v}; need.add(+v); }
        else if (/t="inlineStr"/.test(attrs)) cells[col] = {v: [...inner.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(x => x[1]).join('')};
        else if (v !== undefined) cells[col] = {v}; }
      rows[r] = cells; } });
  const sst = {}; let carry2 = ''; let idx = 0;
  await streamEntry('xl/sharedStrings.xml', txt => { carry2 += txt; let end;
    while ((end = carry2.indexOf('</si>')) >= 0) { const seg = carry2.slice(0, end); carry2 = carry2.slice(end + 5);
      if (need.has(idx)) sst[idx] = [...seg.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(x => x[1]).join(''); idx++; } });
  const val = c => c === undefined ? '' : ('s' in c ? sst[c.s] : c.v);
  const header = {}; for (const [col, c] of Object.entries(rows[1])) header[col] = val(c);
  const colOf = Object.fromEntries(Object.entries(header).map(([c, h]) => [h, c]));
  const WANT = ['CASE_NUMBER','CASE_STATUS','VISA_CLASS','JOB_TITLE','SOC_CODE','SOC_TITLE','FULL_TIME_POSITION','BEGIN_DATE','END_DATE','WAGE_RATE_OF_PAY_FROM','WAGE_RATE_OF_PAY_TO','WAGE_UNIT_OF_PAY','PREVAILING_WAGE','PW_UNIT_OF_PAY','PW_WAGE_LEVEL','WORKSITE_CITY','WORKSITE_STATE'];
  const all = Object.entries(rows).filter(([r]) => r !== '1').map(([r, cells]) => ({row: +r, ...Object.fromEntries(WANT.map(h => [h, val(cells[colOf[h]])]))}));
  // Step 2: certified H-1B, annual wage and prevailing-wage units, both wages present.
  const el = all.filter(x => /^Certified$/i.test(x.CASE_STATUS) && x.VISA_CLASS === 'H-1B' && x.WAGE_UNIT_OF_PAY === 'Year'
                         && x.PW_UNIT_OF_PAY === 'Year' && x.PREVAILING_WAGE && x.WAGE_RATE_OF_PAY_FROM);
  // Step 3: order by FNV-1a of CASE_NUMBER + '|20261006' and take the first 120.
  const fnv = s => { let h = 0x811c9dc5; for (const ch of s + '|20261006') { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; } return h; };
  el.sort((a, b) => fnv(a.CASE_NUMBER) - fnv(b.CASE_NUMBER));
  const F = ['CASE_NUMBER','JOB_TITLE','SOC_CODE','SOC_TITLE','FULL_TIME_POSITION','BEGIN_DATE','END_DATE','WAGE_RATE_OF_PAY_FROM','WAGE_RATE_OF_PAY_TO','PREVAILING_WAGE','PW_WAGE_LEVEL','WORKSITE_CITY','WORKSITE_STATE'];
  const q = v => { v = String(v ?? '').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&apos;/g,"'"); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  const csv = [F.join(','), ...el.slice(0, 120).map(x => F.map(f => q(x[f])).join(','))].join('\n') + '\n';
  const sha = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(csv)))].map(b => b.toString(16).padStart(2, '0')).join('');
  console.log({sheet_rows: nrows, kept_by_hash: all.length, eligible: el.length, sha256: sha});
  return csv;
})();
