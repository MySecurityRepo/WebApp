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

const password1 = ref('')
const password2 = ref('')

const showPassword1 = ref(false)
const togglePasswordVisibility1 = () => { showPassword1.value = !showPassword1.value }

const showPassword2 = ref(false)
const togglePasswordVisibility2 = () => { showPassword2.value = !showPassword2.value }

const token = route.query.token

const tokenValid = ref(false)


onMounted(async () => {

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
        confirmButton: 'my-swal-btn',
        icon: 'my-swal-icon'
      }
    })
    return
  }

  try {
    const res = await api.get(`/auth/reset-password/${token}`)
    message.value = res.data.message
    tokenValid.value = true
    
  } catch (err) {
  
    setTimeout(() => router.push('/'), 0)
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('resetpasswordvue.invalid_token'),
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
    tokenValid.value = false
  }
})


async function passwordReset(){
  try {
    const res1 = await api.post(`/auth/reset-password/${token}`, {
      password1 : password1.value,
      password2 : password2.value
      })
      await Swal.fire({
        title:  t('emailconfirmationvue.swall_success_title'),
        text: t('resetpasswordvue.password_reset'),
        iconHtml: '<i class="bi bi-key"></i> ',
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
      setTimeout(() => router.push('/login'), 3000)
      
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'PASSWORD_NOT_VALID') text = t('errors.password_not_valid')
    else if (message === 'PASSWORD_DONT_CORRESPOND') text = t('errors.passwords_dont_correspond')
    else if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else text = t('deleteconfirmationvue.swall_error_general')
  
    await Swal.fire({
      title:  t('appvue.swall_error_title'),
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
  } finally {
    password1.value = ""
    password2.value = ""
  }
}
</script>

<template>
<div class=" container-fluid mt-3">
  <h2 class="text-warning fw-bold">{{ t('resetpasswordvue.header') }}</h2>
  
  <div class="row mt-5"> 
    <div class="col d-none d-md-block"> 
      <img src="/icons/Book.png" class="mb-3 " alt="Book" width="100%" height="700">  
    </div>
    
    <div class="col mx-auto">
      <div class="container-fluid ">
      
        <div v-if="tokenValid">
          <form method="POST" @submit.prevent="passwordReset" id=form_reg autocomplete="off" novalidate class="needs-validation w-100 mx-lg-auto my-auto mb-3 w-md-75 form-registration-small"> 
            <div class="mb-3">
              <label class="form-label text-warning fw-bold registration-labels" for="password1">{{ t('loginvue.password') }}</label>
              <div class="position-relative d-flex align-items-center">
                <input :type="showPassword1 ? 'text' : 'password'" v-model="password1" class="form-control form-control-lg border-focus xs-form-fields" name="password1" id="password1" :disabled="!tokenValid" placeholder="Enter your Password"/>
                <button type="button" class="btn btn-transparent position-absolute end-0 me-2 p-0 toggle-password-class" @click="togglePasswordVisibility1" id=lock>
                  <i :class="showPassword1 ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>
    	        </button>
    	      </div>
            </div>
            <div class="mb-3">
              <label class="form-label text-warning fw-bold registration-labels" for="password2">{{ t('resetpasswordvue.confirm_password') }}</label>
              <div class="position-relative d-flex align-items-center">
                <input :type="showPassword2 ? 'text' : 'password'" v-model="password2" class="form-control form-control-lg border-focus xs-form-fields" name="password2" id="password2" :disabled="!tokenValid" placeholder="Enter your Password"/>
                <button type="button" class="btn btn-transparent position-absolute end-0 me-2 p-0 toggle-password-class" @click="togglePasswordVisibility2" id=lock>
                  <i :class="showPassword2 ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>
    	        </button>
    	      </div>
            </div>
            <button type="submit" id="register" class="btn btn-outline-warning fw-bold my-button-dim" >{{ t('forgotpasswordvue.send') }}</button>
          </form>      
        </div>
      </div>
    </div>
  </div>
</div>        
</template>
