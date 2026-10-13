/* Show the latest published newspaper at the portal URL. No news generation. */
(async () => {
  'use strict';
  const source = 'https://jodemon9.github.io/Claude-Briefing/';
  const marker = document.querySelector('meta[name="oracle-snapshot-sha256"]');
  if (!marker) return;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(source + 'data/latest.json?t=' + Date.now(), {cache: 'no-store', signal: controller.signal});
    if (!response.ok) throw Error('Missing latest edition');
    const info = await response.json();
    if (info.status !== 'published' || info.html_url !== source + 'latest.html' ||
        !/^\d{4}-\d{2}-\d{2}-(morning|midday|evening)$/.test(info.edition_id) ||
        !/^[a-f0-9]{64}$/.test(info.html_sha256) || !/^[a-f0-9]{64}$/.test(info.version)) throw Error('Invalid publication');
    if (info.html_sha256 === marker.content && info.version === document.querySelector('meta[name="oracle-snapshot-version"]')?.content) return;
    const currentTime = Date.parse(document.querySelector('meta[name="oracle-published-at"]')?.content || '');
    const nextTime = Date.parse(info.published_at || '');
    if (Number.isFinite(currentTime) && (!Number.isFinite(nextTime) || nextTime < currentTime)) throw Error('Older publication');
    const page = await fetch(info.html_url + '?version=' + info.html_sha256, {cache: 'no-store', signal: controller.signal});
    if (!page.ok) throw Error('Missing newspaper');
    const bytes = await page.arrayBuffer();
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
    if (hash !== info.html_sha256) throw Error('Incomplete publication');
    const html = new TextDecoder().decode(bytes);
    const candidate = new DOMParser().parseFromString(html, 'text/html');
    if (candidate.querySelector('meta[name="oracle-edition-id"]')?.content !== info.edition_id || !candidate.querySelector('#main')) throw Error('Wrong edition');
    // Preserve this address and its fragment; the portable document uses absolute asset URLs.
    document.open();
    document.write(html);
    document.close();
  } catch {
    const notice = document.createElement('p');
    notice.id = 'latest-status';
    notice.setAttribute('role', 'status');
    notice.className = 'wrap muted latest-status';
    notice.textContent = 'Προβάλλεται η αποθηκευμένη έκδοση με την ημερομηνία που αναγράφεται. Η νεότερη ενημέρωση δεν ήταν διαθέσιμη· δοκίμασε ανανέωση.';
    document.querySelector('#main')?.prepend(notice);
  } finally {
    clearTimeout(timer);
  }
})();
