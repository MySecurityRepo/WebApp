
<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/lib/api';
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute();
const kind   = ref(route.query.kind ?? 'posts');
const query  = ref(route.query.q ?? '');
const hasMore = ref(true)
const items   = ref([]);
const loading = ref(false);
const error   = ref(null);
const page   = ref(1);
const sentinelRef = ref(null);
let observer


async function setupObserver() {
  await nextTick()
  if (!sentinelRef.value) return

  observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !loading.value) loadPage() 
    },
    { root: null, rootMargin: '300px 0px', threshold: 0 } 
  ) 							
  observer.observe(sentinelRef.value)
}

watch(() => route.query.q,  q   => { query.value = (q ?? '').toString(); });
watch(() => route.query.kind, k => { kind.value  = (k ?? 'posts').toString(); });


watch([query, kind], () => {
  items.value = []
  page.value = 1
  hasMore.value = true
  error.value = null
  void loadPage() 
}, { immediate: true })



async function loadPage() {
  
  if (loading.value || !hasMore.value || !query.value) return
  loading.value = true
  error.value = null

  const controller = new AbortController()
  const currentPage = page.value 

  try {
    const endpoint =
      kind.value === 'posts' ? `/search/posts-batch/${currentPage}` : `/search/users-batch/${currentPage}`

    const { data } = await api.get(endpoint, { params: { q: query.value, limit: 30 }, signal: controller.signal })

    const newItems = data.items ?? []
    
    items.value = currentPage === 1 ? newItems : items.value.concat(newItems)

    hasMore.value = !!data.has_more
    if (hasMore.value) {
      page.value = currentPage + 1
    }
  } catch {

    hasMore.value = false
      
  } finally {
    loading.value = false
  }

 return () => controller.abort()
}



onMounted(async () => {
  
  await setupObserver()
  await loadPage()

})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})

</script>


<template>
  <div class=" container-fluid mt-3">
    <h1 class="text-warning fw-bold">{{ t('appvue.search') }} 🔎</h1>
    
    <h4 v-if="kind==='posts'"class="mt-5 text-danger fw-bold mb-2 p-outside-large text-break xs-limited-width-text" style="margin-left:0rem !important">{{ t('searchvue.search_results_for') }} "{{ query }}" ({{ t('userprofilevue.posts') }})</h4>
    <h4 v-if="kind==='users'"class="mt-5 text-danger fw-bold mb-2 p-outside-large text-break xs-limited-width-text" style="margin-left:0rem !important">{{ t('searchvue.search_results_for') }} "{{ query }}" ({{ t('userprofilevue.users') }})</h4>
    
    <div v-if="!loading && !items.length " class="p-outside" style="margin-left:0.15rem !important">{{ t('searchvue.no_results') }}</div>
    
    <div v-for="item in items" :key="kind === 'posts' ? `post_${item.post_id}` : `user_${item.id}`" class="result-item">
      <template v-if="kind === 'posts'">
        <div class="d-flex mb-3 flex-wrap">
          <RouterLink :to="`/post/${item.post_id}/${item.slug}`" class="me-3 text-break text-decoration-none text-warning fw-bold m-0 p-outside xs-limited-width-text" style="margin-left:0.1rem !important">- {{ t('searchvue.post') }}: {{ item?.title}}</RouterLink>
          <RouterLink :to="`/user/${item.author_id}`" class="me-3 text-break text-decoration-none text-warning fw-bold m-0 p-outside xs-limited-width-text" style="margin-left:0.1rem !important">{{ t('searchvue.by') }}: {{ item?.author_username}}</RouterLink>
        </div>
      </template>
      <template v-else-if="kind === 'users'">
        <div class="mb-3">
          <RouterLink :to="`/user/${item.id}`" class="me-3 text-break text-decoration-none text-warning fw-bold m-0 p-outside xs-limited-width-text" style="margin-left:0.1rem !important">- {{ t('searchvue.user') }}: {{ item?.username}}</RouterLink>
        </div>
      </template>
    </div>
    <div id="sentinel" ref="sentinelRef" class="text-center" v-show="hasMore" style="height:1px"></div>
  </div>
</template>



