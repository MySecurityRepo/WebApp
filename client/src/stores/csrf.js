import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/lib/api'  

export const useCSRFStore = defineStore('csrf', () => {
  const token = ref('')

  async function fetchCSRFToken() {
    const res = await api.get('/auth/csrf-token', { withCredentials: true })
    token.value = res.data.csrf_token
    }
  return { token, fetchCSRFToken }
})
