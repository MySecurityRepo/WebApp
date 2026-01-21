<script setup>
import { ref} from 'vue'
import Swal from 'sweetalert2'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useCSRFStore } from '@/stores/csrf'
import { useNotificationsStore } from '@/stores/notifications'
import { useChatStore } from '@/stores/chat'
import api from '@/lib/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const userStore = useUserStore()
const csrfStore = useCSRFStore()
const notification = useNotificationsStore()
const chat = useChatStore()

const showPassword = ref(false)
const togglePasswordVisibility = () => { showPassword.value = !showPassword.value }

const router = useRouter()
const username_or_email = ref('')
const password = ref('')
const remember_me = ref(false)

const toggleRememberMe = () => { remember_me.value = !remember_me.value }


async function loginRequest(){

  try {
    const res = await api.post('/auth/login', {
      username_or_email: username_or_email.value,
      password: password.value,
      remember_me: remember_me.value  
    })
    
    await csrfStore.fetchCSRFToken();
    await userStore.fetchUser();
    chat.ensureConnected()
  
    setTimeout(() => {
      notification.attach()
      router.push('/')}, 0)
    
  } catch (err) { 
    
    const message = err.response?.data?.message ?? ''
    const days = err.response?.data?.days ?? 0
    let text
    
    if (message === 'USERNAME_OR_PASSWORD_NOT_VALID') text = t('errors.username_or_password_not_valid')
    else if (message === 'USER_NOT_ACTIVE') text = t('errors.user_not_active')
    else if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else if (message === 'USER_IS_MODERATED_1') text = t('errors.user_is_moderated_1')
    else if (message === 'USER_IS_MODERATED') text = t('errors.user_is_moderated_2') + days + t('errors.user_is_moderated_3')
    else text = t('loginvue.login_failed')
    
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
    username_or_email.value = '';
    password.value = '';
    remember_me.value = false;
    showPassword.value = false;
  }
}

</script>


<template>
<div class=" container-fluid mt-3">
  <h2 class="text-warning fw-bold">{{ t('loginvue.login') }} 🔑</h2>
  
  <div class="row mt-5"> 
    <div class="col-xxl d-none d-md-block mb-3"> 
      <img src="/icons/Book.png" alt="Book" width="100%" height="700"> 
    </div>
    <div class="col-xxl">
      <div class="container-fluid ">
                                                       
        <form method="POST" @submit.prevent="loginRequest" id=form_reg autocomplete="off" novalidate class="needs-validation w-100 mx-lg-auto my-auto mb-3 w-md-75 form-registration-small">												
          <div class="mb-3">
            <label class="form-label text-warning fw-bold registration-labels" for="username">{{ t('loginvue.username_or_email') }}</label>
            <input v-model="username_or_email" type="text" class="form-control form-control-lg border-focus xs-form-fields" name="username" id="username" :placeholder="t('registrationvue.username_placeholder')"/>
          </div>
          <div class="mb-4">
            <label class="form-label text-warning fw-bold registration-labels" for="password">{{ t('loginvue.password') }}</label>
            <div class="position-relative d-flex align-items-center">
              <input :type="showPassword ? 'text' : 'password'" v-model="password" class="form-control form-control-lg  border-focus xs-form-fields" name="password" id="password" :placeholder="t('registrationvue.password_placeholder')"/>
              <button type="button" class="btn btn-transparent position-absolute end-0 p-0 toggle-password-class" @click="togglePasswordVisibility" id=lock>
                <i :class="showPassword ? 'bi bi-unlock' : 'bi bi-lock'" class="text-warning fw-bold" style="font-size:1.5rem"></i>             
    	      </button>
    	    </div>    	    
          </div>
          <div class="mb-3 d-flex align-items-center">
            <button type="submit" id="login" class="btn btn-outline-warning fw-bold my-button-dim" >{{ t('loginvue.login') }}</button>
              <input class="form-check-input custom-checkbox border-focus ms-5 me-2" type="checkbox" name="remember" @click="toggleRememberMe"/>
              <span class=" text-warning comment-author mt-1" > {{ t('loginvue.remember_me') }} </span>
          </div>
          <RouterLink to="/forgot-password" class="text-warning mt-5" style="text-decoration:none;">{{ t('loginvue.forgot_password') }}</RouterLink>
        </form>
      </div>
    </div>        
  </div>  
</div> 
</template>



              







