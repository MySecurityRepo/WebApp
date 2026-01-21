import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/lib/api'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)

  async function fetchUser() {
    try {
      const res = await api.get('/auth/user')
      user.value = res.data
    } catch {
      user.value = null
    }
  }

  return { user, fetchUser }
})



