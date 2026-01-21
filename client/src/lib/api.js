import axios from 'axios'
import { useCSRFStore } from '@/stores/csrf'
import { useLangStore } from '@/stores/lang'
import { useUserStore } from '@/stores/user'
import { Capacitor } from "@capacitor/core";


const isNative = Capacitor.isNativePlatform();
axios.defaults.withCredentials = true

const baseURL = isNative ? "https://thebooksclub.com/api" : "/api";

const api = axios.create({
  baseURL,
  withCredentials: true,
})


api.interceptors.request.use((config) => {
  const userStore = useUserStore()
  const langStore = useLangStore()
  const lang = userStore.user?.lang ?? langStore.lang
  const csrf = useCSRFStore()
  const method = (config.method || 'get').toLowerCase()
  config.headers ??= {}
  
  if (['post','put','patch','delete'].includes(method) && csrf.token) {
    config.headers['X-CSRFToken'] = csrf.token
  }
  if (lang) config.headers['X-Lang'] = lang
  return config
})


let refreshing = null
api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const resp = error.response
    const original = error.config || {}
    const method = (original.method || 'get').toLowerCase()
    const isUnsafe = ['post', 'put', 'patch', 'delete'].includes(method)
    const looksLikeCsrf = resp && resp.status === 403 && resp.data && resp.data.error === 'csrf'

    if (isUnsafe && looksLikeCsrf && !original.__retriedWithNewCsrf) {
      const csrf = useCSRFStore()
      if (!refreshing) {
        refreshing = csrf.fetchCSRFToken().finally(() => { refreshing = null })
      }
      await refreshing
      
      original.__retriedWithNewCsrf = true
      original.headers = original.headers || {}
      original.headers['X-CSRFToken'] = csrf.token
      return api.request(original)
    }
    return Promise.reject(error)
  }
)

export default api
