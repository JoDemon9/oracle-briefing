import fs from 'node:fs/promises';

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT  = process.env.TELEGRAM_CHAT_ID;
const BASE  = process.env.BRIEFING_BASE_URL || 'https://jodemon9.github.io/oracle-briefing';
let arg = process.argv[2];
let date = new Date().toISOString().slice(0, 10);
let mdPath = '';

if (arg) {
  if (arg.endsWith('.md')) {
    mdPath = arg;
    const m = arg.match(/(\d{4}-\d{2}-\d{2}(?:-[a-zA-Z]+)?)/);
    if (m) date = m[1];
  } else {
    date = arg;
  }
}

if (!mdPath) {
  const hour = new Date().getUTCHours() + 3; // Cyprus Time EEST (UTC+3)
  const editionTag = hour >= 17 ? '-evening' : (hour >= 12 ? '-midday' : '');
  const candidates = [
    `docs/briefings/${date}${editionTag}.md`,
    `briefings/oracle-briefing-${date}${editionTag}.md`,
    `docs/briefings/${date}.md`,
    `briefings/oracle-briefing-${date}.md`
  ];
  for (const cand of candidates) {
    try {
      await fs.access(cand);
      mdPath = cand;
      const m = cand.match(/(\d{4}-\d{2}-\d{2}(?:-[a-zA-Z]+)?)/);
      if (m) date = m[1];
      break;
    } catch {}
  }
}

if (!mdPath) mdPath = `briefings/oracle-briefing-${date}.md`;
const esc = (s) => {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
};
const md = await fs.readFile(mdPath, 'utf8');

// --- εξαγωγή των βασικών από το markdown ---
const grab = (start, end) => {
  const i = md.indexOf(start);
  if (i === -1) return '';
  const j = end ? md.indexOf(end, i) : md.length;
  return md.slice(i, j === -1 ? md.length : j);
};
const firstHeading = (block) => (block.match(/^###?\s+(.+)$/m) ?? [, ''])[1].trim();

const topStory = firstHeading(grab('## ⭐', '## 📊') || grab('## ⚡', '## 📊') || grab('## 🏁', '## 🔔'));
const dashRows = (grab('## 📊', '## 🏦') || grab('## 📊', '## 🎯') || grab('## 🔔', '## ⚽'))
  .split('\n').filter(l => l.startsWith('| **')).slice(0, 6)
  .map(l => {
    const c = l.split('|').map(s => s.trim()).filter(Boolean);
    return `• ${c[0].replace(/\*\*/g, '')}: ${c[1]} (${c[2]})`;
  }).join('\n');
const myFile = (grab('## 🎯', '## 📅') || grab('## 🎯', '## ⚽') || grab('## 🎯', '---'))
  .split('\n').filter(l => l.startsWith('*   **') || (l.startsWith('*   ') && l.includes('**'))).slice(0, 2)
  .map(l => '• ' + l.replace(/^\*\s+\*\*/, '').replace(/\*\*/g, '').split(':')[0]).join('\n');
const deadlines = grab('## 📅', '## 🔍')
  .split('\n').filter(l => l.startsWith('*   **')).slice(0, 3)
  .map(l => '• ' + l.replace(/^\*\s+\*\*/, '').replace(/\*\*/g, '').replace(/\(\[.*?\]\(.*?\)\)/g, '').trim()).join('\n');

const sportsBlock = grab('## ⚽', '## 🌤️');
let sportsSummary = '';
if (sportsBlock.includes('### ΟΜΟΝΟΙΑ')) {
  const mOm = sportsBlock.match(/\*\*Επόμενος αγώνας:\*\*\s*(.+)/);
  if (mOm) {
    let rawOm = mOm[1].trim();
    rawOm = rawOm.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2">$1</a>');
    rawOm = rawOm.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    sportsSummary = `⚽ <b>Αθλητικά:</b> ${rawOm}`;
  }
}

const weatherBlock = grab('## 🌤️', '## 🗂️');
let weatherSummary = '';
const mW = weatherBlock.match(/\*\*Θερμοκρασία:\*\*\s*(.+)/);
if (mW) {
  let cleanW = mW[1].replace(/\(\[.*?\]\(.*?\)\)/g, '').replace(/[*_]/g, '').trim();
  weatherSummary = `🌤️ <b>Καιρός:</b> ${esc(cleanW)}`;
}

let editionTime = '';
for (const l of md.split('\n').slice(0, 6)) {
  const mEd = l.match(/\*\*(\d{1,2}:\d{2}\s*ώρα Κύπρου.*?)\*\*/);
  if (mEd) {
    editionTime = mEd[1].trim();
    break;
  }
}

let headerText = `🏛️ <b>THE ORACLE SOVEREIGN</b> — ${date}`;
if (editionTime) headerText += `\n🕒 <i>${esc(editionTime)}</i>`;

const msgParts = [
  headerText,
  `⭐ <b>Θέμα της ημέρας</b>\n${esc(topStory)}`,
  `📊 <b>Αγορές</b>\n${esc(dashRows)}`,
  `🎯 <b>Ο φάκελός μου</b>\n${esc(myFile) || '—'}`,
  `📅 <b>Προθεσμίες</b>\n${esc(deadlines) || '—'}`
];

if (sportsSummary) msgParts.push(sportsSummary);
if (weatherSummary) msgParts.push(weatherSummary);
msgParts.push(`📖 <a href="${BASE}/briefings/${date}.html">Πλήρης έκδοση</a>`);

let text = msgParts.join('\n\n');

if (text.length > 4000) text = text.slice(0, 3900) + '\n…\n' + `<a href="${BASE}/briefings/${date}.html">Πλήρης έκδοση</a>`;

const api = (method, body) =>
  fetch(`https://api.telegram.org/bot${TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(async r => {
    const j = await r.json();
    if (!j.ok) throw new Error(`${method}: ${j.description}`);
    return j;
  });

await api('sendMessage', {
  chat_id: CHAT,
  text,
  parse_mode: 'HTML',
  link_preview_options: { is_disabled: false },
  reply_markup: {
    inline_keyboard: [
      [{ text: '📖 Διαβάστε την Πλήρη Έκδοση', url: `${BASE}/briefings/${date}.html` }],
      [{ text: '🏛️ Αρχική Πύλη (The Oracle)', url: `${BASE}/` }]
    ]
  },
  disable_notification: false
});

console.log('Στάλθηκε επιτυχώς το briefing', date);
