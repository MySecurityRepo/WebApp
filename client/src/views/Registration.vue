<script setup>

import { ref } from 'vue'
import Swal from 'sweetalert2'
import api from '@/lib/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const showPassword = ref(false)
const togglePasswordVisibility = () => { showPassword.value = !showPassword.value }
const username = ref('')
const email = ref('')
const password = ref('')
const agreedAge = ref(false)
const agreedTerms = ref(false)


const toggleConsent = () => { agreedTerms.value = !agreedTerms.value }
const toggleAge = () => { agreedAge.value = !agreedAge.value }

async function registrationRequest(){

  try {
  
    if (agreedAge.value===false) {      
      await Swal.fire({
        title: t('appvue.swall_error_title'),
        text: t('registrationvue.swall_error_age'),
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
    
    if (agreedTerms.value===false) {      
      await Swal.fire({
        title: t('appvue.swall_error_title'),
        text: t('registrationvue.swall_error_terms'),
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
    
    const res = await api.post('/auth/register', {
      username: username.value,
      email: email.value,
      password: password.value
    })
    
    await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('registrationvue.activation_message'),
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
    
    if (message === 'USERNAME_NOT_VALID') text = t('errors.username_not_valid')
    else if (message === 'PASSWORD_NOT_VALID') text = t('errors.password_not_valid')
    else if (message === 'EMAIL_NOT_VALID') text = t('errors.email_not_valid')
    else if (message === 'USERNAME_ALREADY_TAKEN') text = t('errors.user_already_taken')
    else if (message === 'EMAIL_ALREADY_TAKEN') text = t('errors.email_already_taken')
    else if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
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
  } finally {
    username.value = ''
    email.value = ''
    password.value = ''
  }
}

  
</script>
  
  
  
<template>
<div class=" container-fluid mt-3">
  <h2 class="text-warning fw-bold">{{ t('registrationvue.header') }} ✍️</h2>
  
  <div class="row mt-5 mb-3"> 
     <div class="col-xxl d-none d-md-block"> 
      <img src="/icons/Book.png" class="mb-3 " alt="Book" width="100%" height="700"> 
    </div>
    <div class="col-xxl ">
      <div class="container-fluid ">
        
        <form method="POST" @submit.prevent="registrationRequest" id=form_reg autocomplete="off" novalidate class="needs-validation w-100 mx-lg-auto my-auto mb-3 w-md-75 form-registration-small" >
          
          <div class="mb-3">
            <label class="form-label text-warning fw-bold registration-labels" for="username">{{ t('registrationvue.username') }}</label>
            <input v-model="username" type="text" class="form-control form-control-lg border-focus xs-form-fields" name="username" id="username" :placeholder="t('registrationvue.username_placeholder')"/>
          </div>
          
          <div class="mb-3">
            <label class="form-label text-warning fw-bold registration-labels" for="email">{{ t('registrationvue.email') }}</label>
            <input v-model="email" type="email" class="form-control form-control-lg border-focus xs-form-fields" name="email" id="email" :placeholder="t('registrationvue.email_placeholder')"/>
          </div>
          
          <div class="mb-4">
            <label class="form-label text-warning fw-bold registration-labels" for="password">{{ t('loginvue.password') }}</label>
            <div class="position-relative d-flex align-items-center">
              <input :type="showPassword ? 'text' : 'password'" v-model="password" class="form-control form-control-lg border-focus xs-form-fields" name="password" id="password" :placeholder="t('registrationvue.password_placeholder')"/>
              <button type="button" class="btn btn-transparent position-absolute end-0 me-2 p-0 toggle-password-class" @click="togglePasswordVisibility" id=lock>
                <i :class="showPassword ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>
    	      </button>
    	    </div>  
          </div>
          
          <div class="mb-3 d-block ">
            <input class="form-check-input custom-checkbox border-focus me-2 mt-1" type="checkbox" @click="toggleAge"/>
            <span class="span-checkmarks text-break"> {{ t('registrationvue.agreeAge') }} </span>
          </div>
          <div class="mb-3 d-block ">
            <input class="form-check-input custom-checkbox border-focus me-2 mt-1" type="checkbox" @click="toggleConsent"/>
            <span class=" span-checkmarks text-break"> {{ t('registrationvue.agreeTos') }}<a class="text-warning" style="text-decoration:none" href="https://thebooksclub.com/docs/TermsofService.html">{{ t('infovue.tos') }}</a>{{ t('registrationvue.agreedPrivacy')}}<a class="text-warning" style="text-decoration:none" href="https://thebooksclub.com/docs/PrivacyPolicy.html">{{ t('infovue.privacypolicy') }}</a>{{ t('registrationvue.agreedFinal')}}
            </span>
          </div>
          <div class=" mb-3 ">
            <button type="submit" id="register" class="btn btn-outline-warning fw-bold my-button-dim me-2" >{{ t('registrationvue.header') }}</button>
            <RouterLink to="/resend-mail" class="btn btn-outline-warning fw-bold my-button-dim">{{ t('registrationvue.resend_email') }}</RouterLink>
          </div>
        </form>
      </div>
    </div>        
  </div>
</div>          
</template>          



