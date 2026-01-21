<script setup>
import { useI18n } from 'vue-i18n'
import { useHead } from '@vueuse/head'

const { t } = useI18n()


useHead({
  title: "The Books Club",
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/info-contacts"
    }
  ]
})


</script>


<template>
  <div class=" container-fluid mt-3">
    <h1 class="text-warning fw-bold">{{ t('appvue.info') }} 📃</h1>
    <p class="text-center mt-5 p-outside">{{ t('infovue.header') }}</p>
    <p class="text-center mt-4 p-outside">{{ t('infovue.privacytext1') }}<span style="color:#ffc107; font-weight: bold;">{{ t('infovue.usersprivacy') }} </span>{{ t('infovue.privacytext2') }} <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">{{ t('infovue.tos') }} </a>{{ t('infovue.and') }}<a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">{{ t('infovue.privacypolicy') }} </a>{{ t('infovue.privacyend') }}</p>
    <p class="text-center mt-4 p-outside">{{ t('infovue.abusetext1') }}<span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span>{{ t('infovue.abusetext2') }}<br>{{ t('infovue.abusetext3') }}<a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/child-safety-policy.html">{{ t('infovue.doc_ref') }}</a>{{ t('infovue.abusetext4') }}</p>
    <p class="text-center mt-4 p-outside">{{ t('infovue.push_not') }}</p>
    
    <p class="text-center mt-4 p-outside"><span style="color:#ffc107; font-weight: bold;">{{ t('infovue.adstext0') }}</span> {{ t('infovue.adstext1') }}<span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>{{ t('infovue.adstext2') }}</p>
    
    
    
    <p class="text-center mt-4 p-outside">{{ t('infovue.techtext1') }}<span style="color:#ffc107; font-weight: bold;">support@thebooksclub.com</span>{{ t('infovue.techtext2') }}</p>
    <p class="text-center mt-4 p-outside">{{ t('infovue.message') }}</p>
    <p class="text-center mt-4 p-outside text-warning">©The Books Club</p>
   
    <p class="text-center small text-warning mt-4 mb-0">P.IVA: 02121900472</p>
    <p class="text-center small text-warning mt-1">contacts@thebooksclub.com</p>
    
  </div>
</template>
