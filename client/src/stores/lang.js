import { defineStore } from 'pinia'
import { i18n, setLang } from '@/i18n' 

export const useLangStore = defineStore('lang', {
  state: () => {
    const supported = ['en','it','fr','es','de','pt','ru','zh','ja','hi']
    
    if (import.meta.env.SSR) return
    const browserLang = (navigator.languages && navigator.languages[0]) || navigator.language || 'en'
    const baseLang = browserLang.split('-')[0]
    const initialLang = supported.includes(baseLang) ? baseLang : 'en'

    return { lang: localStorage.getItem('lang') || initialLang, supported }
  },

  actions: {
    setLanguage(lang) {
      if (!this.supported.includes(lang)) return
      this.lang = lang

      localStorage.setItem('lang', lang)

      i18n.global.locale.value = lang
      if (typeof setLang === 'function') setLang(lang)
    },

    resetToBrowserLang() {
      if (import.meta.env.SSR) return
      const browserLang = (navigator.languages && navigator.languages[0]) || navigator.language || 'en'
      const baseLang = browserLang.split('-')[0]
      const lang = this.supported.includes(baseLang) ? baseLang : 'en'
      this.setLanguage(lang)
    }
  }
})
