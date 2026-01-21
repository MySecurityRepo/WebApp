<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import Swal from 'sweetalert2'
import { storeToRefs } from 'pinia'
import { useCSRFStore } from '@/stores/csrf'
import { useUserStore } from '@/stores/user'
import { useChatStore } from '@/stores/chat'
import { useLangStore } from '@/stores/lang'
import { useNotificationsStore } from '@/stores/notifications'
import ChatDrawer from '@/components/ChatDrawer.vue'
import { onMounted, ref, onBeforeUnmount, computed, watch } from 'vue';
import api from '@/lib/api'
import { openSearchDialog } from '@/lib/search'
import { useI18n } from 'vue-i18n'
import { Capacitor } from '@capacitor/core';
//import { Collapse, Dropdown } from 'bootstrap';


const { t } = useI18n() 
const userStore = useUserStore()
const langStore = useLangStore()
const csrfStore = useCSRFStore()
const router = useRouter()
const chat = useChatStore()
const { unreadCount } = storeToRefs(chat)
const notification = useNotificationsStore()

const currentLang = computed(() => userStore.user?.lang ?? langStore.lang)
watch(
  () => userStore.user?.lang,
  (newLang) => {
    if (!newLang) return
    if (langStore.lang !== newLang) {
      langStore.setLanguage(newLang)
    }
  },
  { immediate: true } 
)

const { items: notif_items, unread: unread_notifs } = storeToRefs(notification)


/*
document.addEventListener('click', function (event) {
  const navbar = document.getElementById('collapsibleNavbar');
  const button = document.getElementById('button_menu');

  
  if (
    navbar.classList.contains('show') &&
    !navbar.contains(event.target) &&
    !button.contains(event.target)
  ) {
    const bsCollapse = Collapse.getInstance(navbar);
    bsCollapse.hide(); 
  }
});*/


onMounted(async () => {
  if (userStore.user) { 
    notification.attach()
  }
  
  function handleClickOutside(e) {
    const menu = document.querySelector("#button_notifications")
    const dropdown = document.querySelector(".dropdown-menu.show")
  
    if (showNotifications.value && !menu.contains(e.target) && (!dropdown || !dropdown.contains(e.target))) {
      showNotifications.value = false
      notification.markAllRead()
    }
  }
  document.addEventListener("click", handleClickOutside)
})

onBeforeUnmount(() => {

    function handleClickOutside(e) {
      const menu = document.querySelector("#button_notifications")
      const dropdown = document.querySelector(".dropdown-menu.show")
  
      if (showNotifications.value && !menu.contains(e.target) && (!dropdown || !dropdown.contains(e.target))) {
        showNotifications.value = false
        notification.markAllRead()
      }
    }
    document.removeEventListener("click", handleClickOutside)
})

const showNotifications = ref(false)
function ToggleNotifications() {
  showNotifications.value = !showNotifications.value
} 



async function logoutRequest(){

  try { 
    const res = await api.post('/auth/logout')
    userStore.user.value = null
    userStore.fetchUser()
    showNotifications.value = false
    notif_items.value = []
    unread_notifs.value = 0
    notification.detach()
    if (chat.socket) {
      chat.socket?.disconnect()
      chat.socket?.off()
      chat.socket = null;
      chat.setActiveThread(null)
      chat._listenersBound = false
    }
    await csrfStore.fetchCSRFToken();
   
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else text = t('appvue.swall_error_logout')
   
    Swal.fire({
      title: t('appvue.swall_error_title'),
      text: text,
      icon: 'error',
      background: '#111',      
      color: '#ff0000',           
      iconColor: '#ff4444',    
      confirmButtonText: 'OK',
      customClass: {
        popup: 'swal2-dark-popup',
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
  }
}


async function openSearch() {
  const result = await openSearchDialog()
  if (!result) return

  if (result.kind === 'posts' && result.post_id && result.slug) {
    router.push(`/post/${result.post_id}/${result.slug}`)
  } else if (result.kind === 'users' && result.id) {
    router.push(`/user/${result.id}`)
  } else {  
    router.push({
    path: `/search`,
    query: { kind: result.kind, q: result.query  }
    })
  }
}


async function changeLang(nextLang) {
  const prev = currentLang.value
  if (!nextLang || nextLang === prev) return

  const { isConfirmed } = await Swal.fire({
    title: t('appvue.swall_change_title'),
    text: t('appvue.swall_change_message'),
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: t('appvue.yes'),
    cancelButtonText: t('appvue.no'),
    background: '#111',     
    color: '#FFC107',
    iconColor: '#FF9800',
    customClass: {
      popup: 'swal2-dark-popup-yellow',
      confirmButton: 'my-swal-btn-yellow',
      cancelButton: 'my-swal-btn-yellow',
      icon: 'my-swal-icon-yellow'
    },
    buttonsStyling: false
  });

  if (!isConfirmed) return;

  langStore.setLanguage(nextLang)

  if (userStore?.user) {
    try {
      await api.put('/change-language', { nextLang })
      await userStore.fetchUser();
      notification.detach();
      notification.attach();
      return;
       
    } catch (err) {
      langStore.setLanguage(prev)
      await Swal.fire({
        title: t('appvue.swall_error_title'),
        text: t('appvue.swall_error_language'),
        icon: 'error',
        background: '#111',
        color: '#ff0000',
        iconColor: '#ff4444',
        confirmButtonText: 'OK',
        customClass: {
          popup: 'swal2-dark-popup',
          icon: 'my-swal-icon',
          confirmButton: 'my-swal-btn'
        },
        buttonsStyling: false
      });
    }
  }
}

const isNative = Capacitor.isNativePlatform(); 
const margin_top = isNative ? '2.5rem' : '0';

</script>
  
<template>
  
  <div class="container-fluid" :style="{ marginTop: margin_top }">
     
    <nav class="navbar navbar-expand-xxl navbar-dark border border-2 border-danger rounded-2 flex-wrap align-items-center xs-limited-width mt-2">
      <RouterLink to="/" class="ms-2 fw-bold btn btn-outline-danger text-danger border border-0 logout-hover" id="title_route">The Books Club</RouterLink>
      
      <div class="d-flex align-items-center flex-nowrap gap-1 ms-auto">
        <button class="position-relative rounded-circle d-flex align-items-center justify-content-center btn btn-black border-2 border-danger btn-outline-danger p-0 m-0 logout-hover circle-class" type="button" @click="chat.setDrawerOpen(true)" :disabled="!userStore.user">
          <i class="bi border-2 bi-chat-dots text-danger p-0 m-0 btn-outline-danger logout-hover " style="font-size: 1.5rem;"></i>
          <span v-if="unreadCount" class="position-absolute start-100 badge badge-class bg-danger text-black ms-0 mt-4 me-2 d-flex justify-content-center align-items-center">{{ unreadCount }}</span>
        </button>
        <div class="position-relative p-0 m-0">
          <button id="button_notifications" type="button" class="p-0 m-0 position-relative rounded-circle d-flex align-items-center justify-content-center btn btn-black border-2 border-danger btn-outline-danger logout-hover rounded-circle circle-class m-0"  @click="showNotifications ? (ToggleNotifications(), notification.markAllRead()) : ToggleNotifications()" :disabled="!userStore.user" >
            <span class="exclamation-point p-0 m-0">!</span>
            <span v-if="unread_notifs" class="position-absolute start-100 badge badge-class bg-danger text-black ms-0 mt-4 me-2 d-flex justify-content-center align-items-center">{{ unread_notifs }}</span>
          </button>
          <div v-if="showNotifications && notif_items.length !== 0" class="dropdown-menu dropdown-menu-end show mt-2 border-1 border-danger dropdown-class" role="menu" @click.stop>
            <div v-for="item in notif_items" class="dropdown-item text-wrap text-start">
              <RouterLink :to="`/post/${item.postId}/${item.postSlug}/${item.commentId}`" class="dropdown-item text-wrap text-start btn btn-sm btn-outline-warning w-100 text-start fw-bold " :key="item.id" style="font-size:0.8rem !important">{{item.text}}<span v-if="item.action==='reply'" class="fw-bold">: "{{item.parentText}}"</span><span v-if="!item.isRead" class="text-danger small"> New!! </span>  </RouterLink>
            </div>
          </div>
          <div v-if="showNotifications && notif_items.length === 0" class="dropdown-menu dropdown-menu-end show mt-2 border-1 border-danger dropdown-class" role="menu" @click.stop>
            <div class="dropdown-item text-wrap text-start">
              <button class="dropdown-item text-wrap text-start btn btn-sm btn-outline-warning w-100 text-start fw-bold" style="font-size:0.8rem !important">{{ t('appvue.not') }}</button>
            </div>
          </div>
        </div>
       </div>
        <button class="btn navbar-toggler ms-1 border border-danger me-1 btn-outline-danger border-2 logout-hover" type="button" data-bs-toggle="collapse" data-bs-target="#collapsibleNavbar" id="button_menu"><span class="navbar-toggler-icon button-menu "></span></button>
        <div class="collapse navbar-collapse" id="collapsibleNavbar">
          <div class="d-flex flex-column flex-xxl-row gap-2 mt-2 mt-sm-0 w-100 justify-content-sm-end">
            <button class="nav-link fw-bold btn btn-outline-danger px-1 py-1 text-danger logout-hover text-navigation" @click="openSearch" :disabled="!userStore.user">{{ t('appvue.search') }}</button>
            <ul class="navbar-nav flex-column flex-xxl-row">
              <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle btn btn-outline-danger text-danger fw-bold logout-hover px-1 py-1 text-navigation" role="button" data-bs-toggle="dropdown">{{ t('appvue.categories') }}</a> 
                <ul class="dropdown-menu text-center background-language border-1 border-danger">
                  <li><RouterLink v-if="userStore.user" to="/favorites" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.favorites') }}</RouterLink></li>
                  <li><RouterLink to="/" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.home') }}</RouterLink></li>           
                  <li><RouterLink to="/books" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.books') }}</RouterLink></li>
                  <li><RouterLink to="/tech-science" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.tech') }}</RouterLink></li>
                  <li><RouterLink to="/movies-series" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.serie') }}</RouterLink></li>              
                  <li><RouterLink to="/art-music" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.art') }}</RouterLink></li>
                  <li><RouterLink to="/sports" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.sport') }}</RouterLink></li>
                  <li><RouterLink to="/social" class="dropdown-item px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.social') }}</RouterLink></li>
                </ul>
              </li>
            </ul>
            <template v-if="userStore.user">
              <RouterLink to="/post/new" class="nav-link px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.newpost') }}</RouterLink>
              <RouterLink :to="`/user/${userStore.user.id}`" class="nav-link px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.profile') }}</RouterLink>
              <button class="nav-link px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation" @click="logoutRequest">{{ t('appvue.logout') }}</button>
            </template>
              
            <template v-else>
              <RouterLink to="/login" class="nav-link px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.login') }}</RouterLink>
              <RouterLink to="/registration" class="nav-link px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.register') }}</RouterLink>
            </template>
            <RouterLink to="/info-contacts" class="nav-link px-1 py-1 fw-bold btn btn-outline-danger text-danger logout-hover text-navigation">{{ t('appvue.info') }}</RouterLink>
          </div>
      </div>
    </nav>
              
    <div class="dropdown position-absolute end-0 me-3 mt-5 language-menu">
      <button id="button_lang" type="button" class="border-0 btn-like bg-transparent" style="cursor: pointer; width:1.8rem; height:1.8rem;" data-bs-toggle="dropdown">
        <i class="bi bi-globe-americas text-warning" style="font-size:1.8rem;"></i>
      </button>
      <ul class="dropdown-menu text-center border-1 border-danger background-language" id="lang_menu">
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('en')" style="cursor: pointer;">{{ t('appvue.english') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('it')" style="cursor: pointer;">{{ t('appvue.italian') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('fr')" style="cursor: pointer;">{{ t('appvue.french') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('es')" style="cursor: pointer;">{{ t('appvue.spanish') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('de')" style="cursor: pointer;">{{ t('appvue.german') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('pt')" style="cursor: pointer;">{{ t('appvue.portuguese') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('ru')" style="cursor: pointer;">{{ t('appvue.russian') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('zh')" style="cursor: pointer;">{{ t('appvue.chinese') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('ja')" style="cursor: pointer;">{{ t('appvue.japanese') }}</li>
        <li class="dropdown-item px-1 py-0 fw-bold me-2 text-navigation" @click="changeLang('hi')" style="cursor: pointer;">{{ t('appvue.hindi') }}</li>  
      </ul>
    </div>
    
    <RouterView :key="currentLang"/>
    <!--<RouterView v-slot="{ Component }">
      <keep-alive :include="['TechPage', 'SportPage', 'SocialPage', 'SeriePage', 'PostPage', 'HomePage', 'UserPage', 'FavPage', 'BooksPage', 'ArtPage']">
        <component :is="Component" :key="currentLang" />
      </keep-alive>
    </RouterView>-->
    
  </div> 
  
  <ChatDrawer />
  
</template>


<style scoped>
  

</style>
