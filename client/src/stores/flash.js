import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useFlashStore = defineStore('flash', () => {
  const flash = ref({ type: '', message: '' })

  function showFlash(type, message) {
    flash.value = { type, message }
    window.scrollTo({
    top: 0,
    behavior: 'smooth'
    })
  }

  function clearFlash() {
    flash.value = { type: '', message: '' }
  }

  return {
    flash,
    showFlash,
    clearFlash,
  }
})
