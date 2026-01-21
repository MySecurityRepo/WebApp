<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import api from '@/lib/api'

const props = defineProps({
  slot: { type: String, required: true },
  index: { type: Number, required: false },
  ad_type: { type: String, required: true },
  lang: { type: String, required: true },
})


const ad      = ref(null)
const root    = ref(null)
const fetched = ref(false)
const sentImp = ref(false)
let observer  = null
let viewTimer = null
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const clickHref = computed(() => {
  if (!ad.value?.href) return '#'
  return API_BASE ? `${API_BASE}${ad.value.href}` : ad.value.href
})


function renderAdMedia(content, kind) {
  const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
  const toAbs = (p) => {
    if (!p) return ''
    if (/^https?:\/\//i.test(p)) return p
    return BASE ? `${BASE}/${String(p).replace(/^\/?/, '')}` : `/${String(p).replace(/^\/?/, '')}`
  }


  const extFromPath = (p) => {
    const s = String(p)
    const cutQ = s.split('#')[0].split('?')[0]
    const i = cutQ.lastIndexOf('.')
    return i >= 0 ? cutQ.slice(i + 1).toLowerCase() : ''
  }
  
  const src = toAbs(content)
  const ext = extFromPath(content)

  if (!kind) {
    if (['png','jpg','jpeg','webp','gif','avif','svg'].includes(ext)) kind = 'image'
    else if (ext === 'mp4' || ext === 'webm') kind = 'video'
    else throw new Error(`Unsupported media extension: .${ext}`)
  }

  if (kind === 'image') {
    if (!['png','jpg','jpeg','webp','gif','avif','svg'].includes(ext)) {
      throw new Error(`Expected image, got .${ext}`)
    }
    return `
      <img src="${src}"
           loading="lazy" decoding="async"
           class="img-fluid rounded mx-auto d-block"
           alt="Advertisement">
    `
  }

  if (kind === 'video') {
    if (!(ext === 'mp4' || ext === 'webm')) {
      throw new Error(`Expected video, got .${ext}`)
    }
    const mime = ext === 'webm' ? 'video/webm' : 'video/mp4'
    return `
      <video autoplay muted controls playsinline loop preload="metadata"
             style="max-width:100%;height:auto" class="mx-auto d-block">
        <source src="${src}" type="${mime}">
      </video>
    `
  }

  throw new Error(`Unsupported kind: ${kind}`)
}


async function fetchAd() {
  if (fetched.value) return
  const res  = await api.get('/ad', { params: { ad_type: props.ad_type,  slot: props.slot, lang:props.lang }})
  const data = res.data
  ad.value   = data?.ad || null
  ad.value.enhancedBody = renderAdMedia(ad.value.content, ad.value.kind),
  
  fetched.value = true
}


async function sendImpressionOnce() {
  if (sentImp.value || !ad.value?.cid) return
  
  const payload = { cid: ad.value.cid, ad_type: ad.value.ad_type, issued_at: ad.value.issued_at, sig: ad.value.sig, lang:ad.value.lang }
  try {
    await api.post('/impression', payload)
  } catch { }
  sentImp.value = true
  if (sentImp.value) observer.disconnect()
}


onMounted(() => {
  observer = new IntersectionObserver((entries) => {
    const entry = entries[0]
    if (!entry) return

    if (entry.isIntersecting) {
      fetchAd()
    }

    if (entry.isIntersecting && entry.intersectionRatio >= 0.4 && !sentImp.value) {
      clearTimeout(viewTimer)
      viewTimer = setTimeout(() => sendImpressionOnce(), 1000)
    } else {
      clearTimeout(viewTimer)
    }
  }, { root: null, rootMargin: '200px', threshold: [0, 0.5] })

  if (root.value) observer.observe(root.value)
})


onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(viewTimer)
})
</script>




<template>
  <div ref="root" class="ad-card" role="complementary" aria-label="Advertisement">
    <template v-if="ad">
      <a :href="clickHref" rel="sponsored nofollow noopener">
      
      
      <div class="card card-width mx-auto border border-2 border-warning rounded-2 mb-5">
        <div class="card-body">
          <h2 class="card-title text-warning text-center fw-bold mb-4">{{ ad?.title}}</h2>
          <div class="text-secondary text-center enhanced-post" v-html="ad.enhancedBody"></div> 
        </div>
      </div>
      
      </a>
    </template>
    
    <div v-else class="card card-width mx-auto border border-2 border-warning rounded-2 mb-5" aria-hidden="true">
      <div class="card-body text-center text-secondary py-2 px-2">
        <div class="spinner-border text-warning" style="width: 2rem; height: 2rem;">
          <span class="visually-hidden">Loading...</span>
        </div>      
      </div>
    </div>
    
  </div>
</template>
