<script setup>

import { ref } from 'vue'
import api from '@/lib/api'
import Swal from 'sweetalert2'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const email = ref('')

async function sendResetPassword(){

  try { 
    const res = await api.post('/auth/forgot-password', {
      email: email.value
    })
    
    await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('forgotpasswordvue.email_restore_message'),
      iconHtml: '<i class="bi bi-envelope"></i>',
      background: '#111',      
      color: '#FFC107',          
      iconColor: '#FF9800',
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup-yellow',
        confirmButton: 'my-swal-btn-yellow',
        icon: 'my-swal-icon-yellow'
      }
    })
    
    
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'EMAIL_NOT_VALID') text = t('errors.email_not_valid')
    else if (message === 'USER_NOT_ACTIVE') text = t('errors.user_not_active')
    else if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else if (message === 'USER_NOT_FOUND') text = t('errors.user_not_found')
    else text = t('deleteconfirmationvue.swall_error_general')
    
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
        confirmButton: 'my-swal-btn',
        icon: 'my-swal-icon'
      }
    })
  }
  
  email.value = ''
  
}

</script>

<template>
<div class=" container-fluid mt-3">
  <h2 class="text-warning fw-bold">{{ t('forgotpasswordvue.header') }}</h2>
  
  <div class="row mt-5"> 
    <div class="col d-none d-md-block"> 
      <img src="/icons/Book.png" class="mb-3 " alt="Book" width="100%" height="700"> 
    </div>
    
    <div class="col mx-auto">
      <div class="container-fluid ">
        
        <form method="POST" @submit.prevent="sendResetPassword" id=form_reg autocomplete="off" novalidate class="needs-validation w-100 mx-lg-auto my-auto mb-3 w-md-75 form-registration-small">
          <div class="mb-3">
            <label class="form-label text-warning fw-bold registration-labels" for="email">{{ t('forgotpasswordvue.email') }}</label>
            <input v-model="email" type="email" class="form-control form-control-lg border-focus xs-form-fields mt-2" name="email" id="email" placeholder="Enter your Email"/>
          </div>
          <button type="submit" id="register" class="btn btn-outline-warning fw-bold my-button-dim " >{{ t('forgotpasswordvue.send') }}</button>
        </form>
      </div>
    </div>
  </div>
</div>
</template>
        
        
        
        
        
        
