import 'sweetalert2/dist/sweetalert2.min.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'vue-select/dist/vue-select.css'
import './assets/main.css'
import 'tippy.js/dist/tippy.css'
import 'tippy.js/themes/light-border.css'

import { ViteSSG } from 'vite-ssg'
import { createPinia } from 'pinia'
import vSelect from 'vue-select'

import App from './App.vue'
import { routes } from './router'  

import { i18n } from '@/i18n'
import { useUserStore } from '@/stores/user'
import { useCSRFStore } from '@/stores/csrf'
import { useLangStore } from '@/stores/lang'



export const createApp = ViteSSG(
  App,
  {
    routes,
    base: import.meta.env.BASE_URL,
  },
  async ({ app, router, isClient }) => {
    const pinia = createPinia()
    app.use(pinia)
    app.use(i18n)

    app.component('v-select', vSelect)

    if (isClient) {
      await import('bootstrap/dist/js/bootstrap.bundle.min.js')
      const userStore = useUserStore(pinia)
      const csrfStore = useCSRFStore(pinia)
      const langStore = useLangStore(pinia)

      await csrfStore.fetchCSRFToken().catch(() => {})
      await userStore.fetchUser().catch(() => {})

      const serverLang = userStore.user?.lang
      const effectiveLang = serverLang || langStore.lang
      langStore.setLanguage(effectiveLang)

      if (import.meta.env.PROD) {
        app.config.devtools = false
      }
    }
  }
)


export function includedRoutes() {
  return [
    '/en',
    '/it',
    '/fr',
    '/es',
    '/de',
    '/ja',
    '/pt',
  ]
}

