import { createI18n } from 'vue-i18n'
import en from './en.json'
import it from './it.json'
import fr from './fr.json'
import es from './es.json'
import de from './de.json'
import pt from './pt.json'
import ru from './ru.json'
import zh from './zh.json'
import ja from './ja.json'
import hi from './hi.json'

const supported = ['en','it','fr','es','de','pt','ru','zh','ja','hi']
const STORAGE_KEY = 'lang'

function loadPersistedLang () {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    return supported.includes(saved) ? saved : 'en'   
  } catch {
    return 'en'
  }
}

export const i18n = createI18n({
  legacy: false,
  locale: loadPersistedLang(),
  fallbackLocale: 'en',
  messages: { en, it, fr, es, de, pt, ru , zh , ja, hi }
})

export function setLang (l) {
  if (!supported.includes(l)) return
  i18n.global.locale.value = l
  
  document.dir = (l === 'ar') ? 'rtl' : 'ltr'
  
  try { window.localStorage.setItem(STORAGE_KEY, l) } catch {}
}

export const supportedLangs = supported
