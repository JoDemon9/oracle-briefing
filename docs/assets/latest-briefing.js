/* Refresh the complete newspaper only after validating its published snapshot. */
(async () => {
  'use strict';
  const source = 'https://jodemon9.github.io/Claude-Briefing/';
  const marker = document.querySelector('meta[name="oracle-snapshot-sha256"]');
  if (!marker) return;
  const daily = Boolean(document.querySelector('meta[name="oracle-day-id"]'));
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  const hex = bytes => [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2,'0')).join('');
  const digest = async bytes => hex(await crypto.subtle.digest('SHA-256', bytes));
  try {
    const response = await fetch(source + 'data/' + (daily ? 'day-latest.json' : 'latest.json') + '?t=' + Date.now(), {cache:'no-store', signal:controller.signal});
    if (!response.ok) throw Error('Missing publication');
    const info = await response.json();
    const id = daily ? info.day_id : info.edition_id;
    if (info.status !== 'published' || info.html_url !== source + (daily ? 'today.html' : 'latest.html') ||
        !(daily ? /^\d{4}-\d{2}-\d{2}$/ : /^\d{4}-\d{2}-\d{2}-(morning|midday|evening)$/).test(id) ||
        !/^[a-f0-9]{64}$/.test(info.html_sha256) || !/^[a-f0-9]{64}$/.test(info.version)) throw Error('Invalid publication');
    if (info.html_sha256 === marker.content && info.version === document.querySelector('meta[name="oracle-snapshot-version"]')?.content) return;
    const currentId = document.querySelector('meta[name="oracle-day-id"]')?.content;
    const currentTime = Date.parse(document.querySelector('meta[name="' + (daily ? 'oracle-day-updated-at' : 'oracle-published-at') + '"]')?.content || '');
    const nextTime = Date.parse(daily ? info.updated_at : info.published_at);
    if ((daily && id < currentId) || (Number.isFinite(currentTime) && (!Number.isFinite(nextTime) || nextTime < currentTime))) throw Error('Older publication');
    const page = await fetch(info.html_url + '?version=' + info.html_sha256, {cache:'no-store', signal:controller.signal});
    if (!page.ok) throw Error('Missing newspaper');
    const bytes = await page.arrayBuffer();
    if (await digest(bytes) !== info.html_sha256) throw Error('Incomplete publication');
    const html = new TextDecoder().decode(bytes);
    const candidate = new DOMParser().parseFromString(html,'text/html');
    if (candidate.querySelector('meta[name="' + (daily ? 'oracle-day-id' : 'oracle-edition-id') + '"]')?.content !== id || !candidate.querySelector('#main')) throw Error('Wrong newspaper');
    if (daily) {
      if (!info.asset_sha256 || typeof info.asset_sha256 !== 'object') throw Error('Missing asset integrity');
      const resources = [...candidate.querySelectorAll('link[rel="stylesheet"][href],script[src],img[src]')];
      // Verify images and assets before replacing the saved good document. Bounded
      // batches avoid flooding mobile connections; any failure leaves the fallback.
      for (let i=0; i<resources.length; i+=6) {
        await Promise.all(resources.slice(i,i+6).map(async node => {
          const url = node.getAttribute(node.tagName === 'LINK' ? 'href' : 'src');
          if (!url.startsWith(source+'assets/') || !/^[a-f0-9]{64}$/.test(info.asset_sha256[url])) throw Error('Unsafe asset');
          const result = await fetch(url, {cache:'no-store',signal:controller.signal});
          if (!result.ok) throw Error('Missing asset');
          const raw = await result.arrayBuffer();
          if (await digest(raw) !== info.asset_sha256[url]) throw Error('Wrong asset');
          if (node.tagName === 'IMG') {
            // Image.decode supports SVG crests as well as raster photographs;
            // createImageBitmap rejects SVG blobs in supported browsers.
            const type = url.split('?')[0].endsWith('.svg') ? 'image/svg+xml' : result.headers.get('content-type') || 'application/octet-stream';
            const objectUrl = URL.createObjectURL(new Blob([raw], {type}));
            try {
              const image = new Image();
              image.src = objectUrl;
              await image.decode();
              if (!image.naturalWidth || !image.naturalHeight) throw Error('Undecodable image');
            } finally { URL.revokeObjectURL(objectUrl); }
          }
        }));
      }
    }
    document.open(); document.write(html); document.close();
  } catch {
    const notice = document.createElement('p');
    notice.id='latest-status'; notice.setAttribute('role','status'); notice.className='wrap muted latest-status';
    notice.textContent='Προβάλλεται η αποθηκευμένη εφημερίδα με την ημερομηνία που αναγράφεται. Η νεότερη ενημέρωση δεν ήταν διαθέσιμη· δοκίμασε ανανέωση.';
    document.querySelector('#main')?.prepend(notice);
  } finally { clearTimeout(timer); }
})();
