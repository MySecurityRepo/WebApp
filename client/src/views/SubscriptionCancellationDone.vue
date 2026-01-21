<script setup>

import { onBeforeMount } from 'vue' 
import { useRouter } from 'vue-router'
import Swal from 'sweetalert2'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()

onBeforeMount(async () => {
  
  setTimeout(() => router.push('/'), 0)
  
  await Swal.fire({
    title: t('subscription.unsubscription_successfull'),
    text: t('subscription.subscription_successfull_message'),
    iconHtml: '<i class="bi bi-fire mt-3"></i>',
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
  
  return
})


</script>

<template>

</template>
