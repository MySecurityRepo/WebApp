const SYSTEM_PATTERNS = [
  { key: 'chatdrawervue.user_added',  re: /^(?<adder>.+) added (?<names>.+) to the chat\.$/ },
  { key: 'chatdrawervue.user_left',   re: /^(?<user>.+) left this chat\.{3}$/ },
  { key: 'chatdrawervue.title_changed', re: /^(?<user>.+) changed the chat title to "?(?<title>.+?)"?$/ },
  { key: 'chatdrawervue.message_deleted', re: /^This message has been deleted\.{3}$/ }
];

export function parseSystemMessage(msg) {
  
  if (msg && msg.system && msg.system.key) {
    return { key: msg.system.key, params: msg.system.params || {} };
  }
  
  const englishText = typeof msg === 'string' ? msg : msg?.text || '';
  for (const { key, re } of SYSTEM_PATTERNS) {
    const m = englishText.match(re);
    if (m && m.groups) return { key, params: m.groups };
  }
  return null;
}
