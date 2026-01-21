<script setup>

import { ref, onMounted } from 'vue' 
import Swal from 'sweetalert2'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/lib/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const message = ref('')
const userStore = useUserStore()

const old_password = ref('')
const password1 = ref('')
const password2 = ref('')

const showOldPassword = ref(false)
const toggleOldPasswordVisibility = () => { showOldPassword.value = !showOldPassword.value }

const showPassword1 = ref(false)
const togglePasswordVisibility1 = () => { showPassword1.value = !showPassword1.value }

const showPassword2 = ref(false)
const togglePasswordVisibility2 = () => { showPassword2.value = !showPassword2.value }


async function modifyPassword(){
  try {
    const res1 = await api.post(`/modify-password`, {
    
      old_password : old_password.value,
      password1 : password1.value,
      password2 : password2.value
      })
      
      await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('modifypasswordvue.modify_password_message'),
      iconHtml: '<i class="bi bi-key"></i>',
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
      
      
      setTimeout(() => router.push('/'), 3000)
      
  } catch (err) {
    
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'PASSWORD_NOT_VALID') text = t('errors.password_not_valid')
    else if (message === 'CURRENT_PASSWORD_WRONG') text = t('errors.current_password_wrong')
    else if (message === 'PASSWORD_DONT_CORRESPOND') text = t('errors.passwords_dont_correspond')
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
    old_password.value = ""
    password1.value = ""
    password2.value = ""
  }
}

onMounted(async () => {
  await userStore.fetchUser();

  if (!userStore.user) {
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('modifypasswordvue.necessary_login'),
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
    router.push('/login');
    return; 
  }
})

</script>


<template>
<div class=" container-fluid mt-3">
  <h2 class="text-warning fw-bold">{{ t('modifypasswordvue.header') }}</h2>
  
  <div class="row mt-5"> 
    <div class="col d-none d-md-block"> 
      <img src="/icons/Book.png" class="mb-3 " alt="Book" width="100%" height="700"> 
    </div>
    
    <div class="col">
      <div class="container-fluid ">
        
        <form method="POST" @submit.prevent="modifyPassword" id=form_reg autocomplete="off" novalidate class="needs-validation w-100 mx-lg-auto my-auto mb-3 w-md-75 form-registration-small"> 
            
            <div class="mb-3 ">
              <label class="form-label text-warning fw-bold registration-labels" for="old_password">{{ t('modifypasswordvue.old_password') }}</label>
              <div class="position-relative d-flex align-items-center">
                <input :type="showOldPassword ? 'text' : 'password'" v-model="old_password" class="form-control form-control-lg border-focus xs-form-fields" name="old_password" id="old_password" placeholder="Enter your current Password"/>
                <button type="button" class="btn btn-transparent position-absolute end-0 me-2 p-0 toggle-password-class" @click="toggleOldPasswordVisibility" id=lock>
                  <i :class="showOldPassword ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>
    	        </button>
    	      </div>
            </div>  
                  
            <div class="mb-3">
              <label class="form-label text-warning fw-bold registration-labels" for="password1">{{ t('modifypasswordvue.new_password') }}</label>
              <div class="position-relative d-flex align-items-center">
                <input :type="showPassword1 ? 'text' : 'password'" v-model="password1" class="form-control form-control-lg border-focus xs-form-fields" name="password1" id="password1" placeholder="Enter your Password"/>
                <button type="button" class="btn btn-transparent position-absolute end-0 me-2 p-0 toggle-password-class" @click="togglePasswordVisibility1" id=lock>
                  <i :class="showPassword1 ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>
    	        </button>
    	      </div>
            </div>
          
            <div class="mb-3">
              <label class="form-label text-warning fw-bold registration-labels" for="password2">{{ t('modifypasswordvue.confirm_new_password') }}</label>
              <div class="position-relative d-flex align-items-center">
                <input :type="showPassword2 ? 'text' : 'password'" v-model="password2" class="form-control form-control-lg border-focus xs-form-fields" name="password2" id="password2" placeholder="Enter your Password"/>
                <button type="button" class="btn btn-transparent position-absolute end-0 me-2 p-0 toggle-password-class" @click="togglePasswordVisibility2" id=lock>
                  <i :class="showPassword2 ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>
    	        </button>
    	      </div>
            </div>
            <button type="submit" id="register" class="btn btn-outline-warning fw-bold mb-3" >{{ t('forgotpasswordvue.send') }}</button>
        </form>      
        
      </div>
    </div>
  </div>
</div>
</template>







