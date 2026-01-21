<script setup>

import { ref, onMounted } from 'vue' 
import { useRoute, useRouter } from 'vue-router'
import api from '@/lib/api'
import Swal from 'sweetalert2'
import { useUserStore } from '@/stores/user'
import { useCSRFStore } from '@/stores/csrf'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const message = ref('')
const userStore = useUserStore()
const csrfStore = useCSRFStore()



async function logoutRequest(){

  try { 
    const res = await api.get('/auth/logout') 
    userStore.user.value = null
    userStore.fetchUser()
    notification.detach()
    if (chat.socket) {
      chat.socket?.disconnect()
      chat.socket?.off()
      chat.socket = null;
      chat.setActiveThread(null)
      chat._listenersBound = false
    }
    await csrfStore.fetchCSRFToken();
    
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else text = t('deleteconfirmationvue.swall_error_logout')
   
    Swal.fire({
      title: t('appvue.swall_error_title'),
      text: text,
      icon: 'error',
      background: '#111',      
      color: '#ff0000',           
      iconColor: '#ff4444',    
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup',
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
  }
}


onMounted(async () => {
  const token = route.query.token

  if (!token) {
    setTimeout(() => router.push('/'), 0)
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('deleteconfirmationvue.swall_error_token'),
      icon: 'error',
      background: '#111',      
      color: '#ff0000',        
      iconColor: '#ff4444',    
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup',
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
    return
  }

  try {
    const res = await api.post(`/confirm-account-deletion/${token}`)

    await logoutRequest()
    setTimeout(() => router.push('/'), 0)
    
    await Swal.fire({
      title: t('deleteconfirmationvue.swall_deleted_title'),
      html: `
        ${t('deleteconfirmationvue.swall_deleted_msg1')}<br>
        ${t('deleteconfirmationvue.swall_deleted_msg2')}<br>
        ${t('deleteconfirmationvue.swall_deleted_msg3')}`,
      background: '#111',      
      color: '#FFC107',          
      iconColor: '#FF9800', 
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup-yellow',
        icon: 'my-swal-icon-yellow',
        confirmButton: 'my-swal-btn-yellow'
      }
    })
     
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else text = t('deleteconfirmationvue.swall_error_general'),
    
    setTimeout(() => router.push('/'), 0)
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: text,
      icon: 'error',
      background: '#111',
      color: '#ff0000',        
      iconColor: '#ff4444',   
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup',
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
  }
})
</script>

<template>
  <div class=" container-fluid mt-3">
    <h2 class="text-warning fw-bold">{{ t('deleteconfirmationvue.page_header') }}</h2>
    <div class="row mt-5 mb-3">
      <img src="/icons/Book.png" alt="Book" width="80%" height="500">  
    </div>
  </div>
</template>
