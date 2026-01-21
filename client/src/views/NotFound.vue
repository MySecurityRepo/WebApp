<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'


const { t } = useI18n() 
</script>



<template>
  <div class=" container-fluid mt-3">
    <p class="text-warning fw-bold" style="font-size:4rem;">404</p>
    <p class="text-warning fw-bold" style="font-size:2rem;">{{ t('notfoundvue.notfound') }}</p>
    <RouterLink to="/" class="m-0 p-0 fw-bold btn btn-outline-danger border border-1 text-danger border border-0 logout-hover" style="font-size:1.5rem;">{{ t('notfoundvue.gohome') }}</RouterLink>
  </div>
</template>
