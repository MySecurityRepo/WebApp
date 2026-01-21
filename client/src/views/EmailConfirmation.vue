<script setup>

import { ref, onMounted } from 'vue' 
import { useRoute, useRouter } from 'vue-router'
import api from '@/lib/api'
import Swal from 'sweetalert2'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const message = ref('')


onMounted(async () => {
  const token = route.query.token

  if (!token) {
  
    setTimeout(() => router.push('/registration'), 0)
    
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
    const res = await api.get(`/auth/confirm/${token}`)
    setTimeout(() => router.push('/login'), 0)
    
    await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      html:`
        ${t('emailconfirmationvue.swall_verification_msg1')}<br>
        ${t('emailconfirmationvue.swall_verification_msg2')}`,
      
      iconHtml: '<i class="bi bi-envelope-check"></i>',
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
    else text = t('deleteconfirmationvue.swall_error_token')
    
    setTimeout(() => router.push('/registration'), 0)
    
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
    <h2 class="text-warning fw-bold">{{ t('emailconfirmationvue.page_header') }}</h2>
  
    <div class="row mt-5 mb-3"> 
      <img src="/icons/Book.png" class="mb-3 " alt="Book" width="80%" height="700">
    </div>
  </div>    
</template>
