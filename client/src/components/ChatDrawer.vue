<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed, reactive, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { useFlashStore } from '@/stores/flash'
import api from '@/lib/api'
import Swal from 'sweetalert2'
import { openSearchUsersToAdd } from '@/lib/search'
import { useI18n } from 'vue-i18n'
import { parseSystemMessage } from '@/lib/systemMessage';
import { Capacitor } from '@capacitor/core'
import { pickFile } from "@/lib/filePicker.js";



const { t, locale } = useI18n()
const chat = useChatStore()
const userStore = useUserStore()
const flashStore = useFlashStore()
const draft = ref('')
const attachments = ref([])  
const isExpanded = ref(false)
const isUploading = ref(false)
const listEl = ref(null)
const drawerEl = ref(null)

let instance = null
let Offcanvas = null


async function ensureInstance() {
  if (!Offcanvas) {
    const module = await import('bootstrap/js/dist/offcanvas')
    Offcanvas = module.default
  }
  if (drawerEl.value && !instance) {
    instance = Offcanvas.getOrCreateInstance(drawerEl.value, {
      backdrop: true,
      keyboard: true,
      scroll: false,
    })
  }
}


const platform = computed<'web' | 'ios' | 'android'>(() => {
  const p = Capacitor.getPlatform()
  if (p === 'ios') return 'ios'
  if (p === 'android') return 'android'
  return 'web'
})


const LRM = '\u200E' 


function formatListLocalized(items) {
  if (!items || !items.length) return ''
  try {
    const lf = new Intl.ListFormat(locale.value, { style: 'long', type: 'conjunction' })
    return lf.format(items)
  } catch {
      
    return items.join(', ')
  }
}


function splitEnglishNamesList(s) {
  if (!s) return [];
  s = s.trim().replace(/\.$/, '');
  const i = s.lastIndexOf(' and ');
  if (i !== -1) s = s.slice(0, i) + ', ' + s.slice(i + 5);
  return s.split(/\s*,\s*/).filter(Boolean);
}


function systemText(msg) {
  const parsed = parseSystemMessage(msg)
  if (!parsed) return typeof msg === 'string' ? msg : msg?.text || '';

  const params = { ...parsed.params };
  
  if (Array.isArray(params.names)) {
    let arr = params.names;
    if (locale.value.startsWith('ar')) arr = arr.map(n => `${LRM}${n}${LRM}`);
    params.names = formatListLocalized(arr);
  } 
  
  else if (typeof params.names === 'string') {
    let arr = splitEnglishNamesList(params.names);
    if (locale.value.startsWith('ar')) arr = arr.map(n => `${LRM}${n}${LRM}`);
    params.names = formatListLocalized(arr);
  }
  
  for (const k of ['user', 'adder', 'title']) {
    if (params[k] && locale.value.startsWith('ar')) {
      params[k] = `${LRM}${params[k]}${LRM}`;
    }
  }

  return t(parsed.key, params)
}


const canSend = computed(() => {
  const hasText = draft.value.trim().length > 0
  const hasAtts = attachments.value.length > 0
  const threadOk = users_chat.value.length > 0 || !!chat.activeThreadId
  return threadOk && (hasText || hasAtts) && !chat.isConnecting && !isUploading.value
})



async function waitForModerationStatus( uploadId, { maxAttempts = 1000, delayMs = 1000 } = {} ) {  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const res = await api.get(`/moderation_status/${uploadId}`);
    const data = res.data;
    if (data.status === 'approved' || data.status === 'rejected') {
      return data;
    }
    await new Promise(resolve => setTimeout(resolve, delayMs));
  }
  return data;
}


let uploadModalOpen = false;
async function upload(file) {
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  isUploading.value = true
  try {
  
    if (!uploadModalOpen) {
      uploadModalOpen = true;
      Swal.fire({
        title: t('homevue.moderation_title'),
        html: `<i class="bi bi-hourglass-top text-warning"></i> ${t('homevue.moderation_msg')} 1...<i class="bi bi-hourglass-bottom text-warning"></i>⌛️`,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        backdrop: true,
        background: '#111',
        color: '#FFC107',
        customClass: { popup: 'swal2-dark-popup-yellow' },
          didOpen: () => Swal.showLoading(),
      });
    }
    
    if (Swal.isVisible()) {
      Swal.update({
        html: `<div style="display:flex; flex-direction:column; align-items:center;"><div class="mb-5"><i class="bi bi-hourglass-top text-warning"></i> ${t('homevue.moderation_msg')}...<i class="bi bi-hourglass-bottom text-warning"></i></div> <div class=" swal2-loader mx-auto" style="display:block;"></div></div>`,
      });
    }
    
    const res = await api.post('/upload', fd)
    const uploadId = res.data.upload_id
    const moderationResult = await waitForModerationStatus(uploadId);
    
    if (moderationResult.status === 'approved') {
      
      if (Swal.isVisible()) Swal.close();
      uploadModalOpen = false;
      const att = {
        id: uploadId,
        mime: moderationResult.mime || file.type,
        url: moderationResult.location ? `/${moderationResult.location.replace(/^\/?/, '')}` : null,
        variants: moderationResult.variants || null,
        name: res.data.name || file.name || 'attachment',
        thumbnail: moderationResult.thumbnail
      };
      
      if (!attachments.value.some(a => a.id === att.id)) attachments.value.push(att)
      return;
      
    } else if (moderationResult.status === 'rejected') {
      if (Swal.isVisible()) Swal.close();
      uploadModalOpen = false;
      await Swal.fire({
        title: t('appvue.swall_error_title'),
        text: t('homevue.upload_rejected'),
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
      return;
    } else if (moderationResult.status === 'pending') {
      
      if (Swal.isVisible()) Swal.close();
      uploadModalOpen = false;
      await Swal.fire({
        title: t('appvue.swall_error_title'),
        text: t('homevue.moderation_timeexceeded'),
        icon: 'error',
        background: '#111',
        color: '#ff0000',
        iconColor: '#ff4444',
        confirmButtonText: t('appvue.ok'),
        customClass: {
          popup: 'swal2-dark-popup',
          icon: 'my-swal-icon',
          confirmButton: 'my-swal-btn',
        },
      });  
    } 
  } catch (err) {
    if (Swal.isVisible()) Swal.close();
    uploadModalOpen = false;
    const message = err.response?.data?.message ?? ''
    let text
    if (message === 'FILE_TOO_LARGE') text = t('errors.file_to_large')
    else if (message === 'FILE_NOT_ALLOWED') text = t('errors.file_not_allowed')
    else if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
    else text = t('deleteconfirmationvue.swall_error_general')
    await Swal.fire({
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
  } finally {
    isUploading.value = false
  }
}


const MAX_FILE_MB = 40
const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

async function onFileChange(e) {
  const f = e.target.files?.[0]
  if (!f) return
  if (f.size > MAX_FILE_BYTES) {
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('errors.file_too_big'),
      icon: 'error',
      background: '#111',      
      color: '#ff0000',           
      iconColor: '#ff4444',    
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup',
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })   
    return
  }
  if (f) upload(f)
  e.target.value = ''
}



function removeAtt(attachment_id) {
  attachments.value = attachments.value.filter(a => a.id !== attachment_id)
  return
}
  

function onPaste(e) {
  const f = e.clipboardData?.files?.[0]
  if (f && (f.type.startsWith('image/') || f.type.startsWith('video/') || f.type === 'application/pdf')) {
    e.preventDefault()
    upload(f)
  }
}


function onDrop(e) {
  const f = e.dataTransfer?.files?.[0]
  if (f && (f.type.startsWith('image/') || f.type.startsWith('video/') || f.type === 'application/pdf')) {
    e.preventDefault()
    upload(f)
  }
}



function debounce(fn, ms=250) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms) }
}

const searchText = ref('')
const users = ref([])

async function doSearch() {
  try {
    const query = searchText.value.trim()
    if (!query) {
      users.value = []
      return
    }

    const res = await api.get('search/users', {
      params: { query, limit: 10 }
    })

    users.value = res.data.items || []
  } catch (err) {
    users.value = []
  }
}

const searchUser = debounce(doSearch, 300)

const users_chat = ref([])


function addUserToChat(user) {
  
  if (!users_chat.value.find(u => u.id === user.id)) {
    users_chat.value.push(user)
    const participantIds = users_chat.value.map(u => u.id)
    chat.searchThreadById({participantIds})
    users.value = []
    searchText.value = ''
  }else{
    users.value = []
    searchText.value = ''
  }
}

function remUserFromChat(user) {
  if (users_chat.value.find(u => u.id === user.id)) {
    users_chat.value = users_chat.value.filter(u => u.id !== user.id)
    const participantIds = users_chat.value.map(u => u.id)
    chat.searchThreadById({participantIds})
    users.value = []
    searchText.value = ''
  }else{
    users.value = []
    searchText.value = ''
  }
}

function resetUserChat(){
  users.value = []
  searchText.value = ''
}


const usersChatNames = computed(() => {
  const formatter = new Intl.ListFormat(locale.value, { style: 'long', type: 'conjunction' })
  return formatter.format(users_chat.value.map(u => u.username))
})


const lf = computed(() => new Intl.ListFormat(locale.value, {
  style: 'long',
  type: 'conjunction'
}))

function formatParticipants(participants) {
  if (!participants || participants.length === 0) return ''
  // Optional: bidi safety for Arabic UI
  const LRM = '\u200E'
  const items = locale.value.startsWith('ar') ? participants.map(n => `${LRM}${n}${LRM}`) : participants
  return lf.value.format(items)
}


const ChooseTitle = ref("") 
const parentId = ref(null)

function toggleParentId(id) {
  parentId.value = (parentId.value === id ? null : id)
}

const messagesById = computed(() => {
  const map = new Map()
  for (const m of chat.activeMessages) map.set(m.id, m)
  return map
})
const parentMessage = computed(() => messagesById.value.get(parentId.value) || null)


const BASE = 40        
const MAX  = 140 

function checkOverflow() {
  const el = msgInput.value
  if (!el) return

  el.style.boxSizing = 'border-box'
  el.style.height = `${BASE}px`
  el.style.overflowY = 'hidden'

  if (el.scrollHeight > el.clientHeight) {
    const wanted = Math.min(el.scrollHeight, MAX)
    el.style.height = `${wanted}px`
    el.style.overflowY = wanted >= MAX ? 'auto' : 'hidden'
  }
}


function resetTextareaHeight() {
  const el = msgInput.value
  if (!el) return
  el.style.height = `${BASE}px`
  el.style.overflowY = 'hidden'
}


async function send() {

/*
  if (userStore.user?.is_premium === false) {
    
    const result = await Swal.fire({
      title: t('chatdrawervue.subscribe'),
      text: t('chatdrawervue.subscription_message'),
      iconHtml: '<i class="bi bi-pen"></i> ',
      allowOutsideClick: false,
      allowEscapeKey: false,
      showCancelButton: true,
      confirmButtonText: t('chatdrawervue.subscribe_button'),
      cancelButtonText: t('homevue.cancel'),
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
    })
    
    if ((result.isConfirmed)) { 
      try {
        if (platform.value == "web"){
        {
          const res = await api.post('/billing/create-checkout-session')
          window.location.href = res.data.url;
          
        } else if ( platform.value == "ios" || platform.value == "android") {
          
          await Purchases.configure({ apiKey: "appl_xxx" })
          const offerings = await Purchases.getOfferings()
          const packageToBuy = offerings.current.availablePackages[0]
          const purchase = await Purchases.purchasePackage(packageToBuy)
          const entitlements = purchase.customerInfo.entitlements.active
          await api.post('/billing/validate-apple-google', { receipt })
          
        }
          
      } catch(err) {
        await Swal.fire({
          title: t('appvue.swall_error_title'),
          text: t('deleteconfirmationvue.swall_error_general'),
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
    } else {
      return
    } 
  }
*/
  if (!canSend.value) return
  
  const text = draft.value.trim()
  const attachment_ids = attachments.value.map(a => a.id)
  
  if (users_chat.value.length > 0 || !chat.activeThreadId) {
    const participantIds = users_chat.value.map(u => u.id)
    const title = ChooseTitle.value || ""
    chat.createThreadAndSend({ participantIds, text, title, attachment_ids })
    users_chat.value = []
    searchText.value = ''
    users.value = []
    ChooseTitle.value = ''
    
  } else {
    const pId = parentId.value
    chat.sendMessage({ text, pId, attachment_ids })
    parentId.value = null
    if (parentId){
      showActions.value[pId] = false
    }
  }
  draft.value = ''
  attachments.value = []
  resetTextareaHeight()
  
}


function changeTitle() {
  const title = ChooseTitle.value || ""
  chat.changeTitle({ title })
  ChooseTitle.value= ""
}


function scrollToBottom() {
  if (!listEl.value) return
  listEl.value.scrollTop = listEl.value.scrollHeight
}


function formatTime(ts) {
  try { return new Date(ts).toLocaleString() } catch { return '' }
}


watch(
  () => chat.activeMessages.length,
  async () => {
    await nextTick()        
    scrollToBottom()
  },
  { flush: 'post' }         
)


watch(() => chat.drawerOpen, (open) => {
  ensureInstance()
  if (!instance) return
  if (open) {
    instance.show()
    setTimeout(scrollToBottom, 0)
  } else {
    instance.hide()
    users.value = []
    searchText.value = ''
    users_chat.value = []
  }
})


const ActiveThread = computed(() =>
  chat.threads.find(x => x.id === chat.activeThreadId) || null
)

const ThreadParticipants = computed(() =>
  ActiveThread.value ? ActiveThread.value.participants : []
)
  

function onShown()  { chat.setDrawerOpen(true) }   
function onHidden() {
  attachments.value = [];
  chat.setDrawerOpen(false)  
}

async function leaveGroupChat() {
  
  const el = drawerEl.value
  if (!el) return
  
  const preventHide = (e) => e.preventDefault()
  el.addEventListener('hide.bs.offcanvas', preventHide)
  
  try{
    const result = await Swal.fire({
      title: t('chatdrawervue.leave_chat'),
      text: t('chatdrawervue.leave_chat_message'),
      iconHtml: '<i class="bi bi-door-open"></i> ',
      allowOutsideClick: false,
      allowEscapeKey: false,
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
    })

    if (!(result.isConfirmed && chat.activeThreadId)) {
      chat.setDrawerOpen(false) 
      return 
    }   
    const ok = await chat.leaveGroupChat({ ThreadParticipants })
    if (!ok) return;
    
    const next = chat.threads[0]?.id ?? null;
    if (next) {
      chat.setActiveThread(next);
    } else {
      chat.setActiveThread(null);
      chat.setDrawerOpen(false)
    }
  } finally {
    el.removeEventListener('hide.bs.offcanvas', preventHide)
  }
} 


watch(() => chat.activeThreadId, (newId, oldId) => {
  if (newId && newId !== oldId) {
    chat.setActiveThread(newId)
    resetUserChat()
  }
})


const showActions = ref({})

function toggleActions(id) {
  showActions.value[id] = !showActions.value[id]
}

const showPicker = ref(false)
const openEmoji = ref(null)
const openMeassage = ref(null)
const activePickerId = ref(null)
const msgInput = ref(null)


function toggleEmojiUsers(emoji, message) {
  if (openEmoji.value === emoji && openMeassage.value === message) {
    openEmoji.value = null
    openMeassage.value = null
  } else {
    openEmoji.value = emoji
    openMeassage.value = message
  }
}


function togglePickerMes(id) {
  activePickerId.value = (activePickerId.value === id) ? null : id
}

function closePicker(id) {
  if (activePickerId.value === id) activePickerId.value = null
}


async function onEmojiClickMes(event, id) {
  const emoji = event.detail.unicode
  await chat.AddMessageReact({ messageId: id, emoji })
  closePicker(id)
  showActions.value[id] = false
}


async function deleteMessage(id) {

  const el = drawerEl.value
  if (!el) return
  
  const preventHide = (e) => e.preventDefault()
  el.addEventListener('hide.bs.offcanvas', preventHide)
  
  try{
    const result = await Swal.fire({
      title: t('chatdrawervue.delete_message'),
      text: t('chatdrawervue.delete_message_message'),
      iconHtml: '<i class="bi bi-trash"></i> ',
      allowOutsideClick: false,
      allowEscapeKey: false,
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
    })

    if (!(result.isConfirmed && chat.activeThreadId)) {
      return 
    }

    await chat.deleteMessage({ messageId: id})
    showActions.value[id] = false
    
  } finally {
    el.removeEventListener('hide.bs.offcanvas', preventHide)
  }
}


async function ToggleAddUser() {

  const el = drawerEl.value
  const userId = userStore.user?.id
  if (!el) return
  
  const preventHide = (e) => e.preventDefault()
  el.addEventListener('hide.bs.offcanvas', preventHide)
  
  try{
    const picked = await openSearchUsersToAdd( { target: el, userId: userId } );
    if (picked && picked.length) {
    const users_id = picked.map(u => u.id)
    
    await chat.addUsersToThread({users_id: users_id});
    }
  } catch {
    el.removeEventListener('hide.bs.offcanvas', preventHide)
  } finally {
    el.removeEventListener('hide.bs.offcanvas', preventHide)
  }
}


function waitForStablePosition(el, { quiet = 200, timeout = 2000, threshold = 1 } = {}) {
  return new Promise((resolve) => {
    let lastTop = null;
    let lastHeight = null;
    let quietTimer = null;
    let hardTimer = null;
    let rafId = null;

    const done = () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (quietTimer) clearTimeout(quietTimer);
      if (hardTimer) clearTimeout(hardTimer);
      resolve();
    };

    const tick = () => {
      const rect = el.getBoundingClientRect();
      const top = rect.top;
      const h = rect.height;

      const moved =
        lastTop === null ||
        Math.abs(top - lastTop) > threshold ||
        Math.abs(h - lastHeight) > threshold;

      lastTop = top;
      lastHeight = h;

      if (moved) {
        if (quietTimer) clearTimeout(quietTimer);
        quietTimer = setTimeout(done, quiet);
      }
      rafId = requestAnimationFrame(tick);
    };

    hardTimer = setTimeout(done, timeout);
    tick();
  });
}



function goToParent(parentId) {
  if (!parentId) return
  const el = document.getElementById(`message-${parentId}`)
  if (!el) return  
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  waitForStablePosition(el, { quiet: 200, timeout: 2000, threshold: 1 })
    .then(() => {
      el.scrollIntoView({ behavior: 'smooth', block: 'center', });
    }); 
}


function onEmojiClick(event) {
  const char = event.detail.unicode
  insertAtCursor(char)
  showPicker.value = false
}


function insertAtCursor(char) {
  const el = msgInput.value
  const start = el.selectionStart ?? draft.value.length
  const end   = el.selectionEnd ?? draft.value.length
  draft.value = draft.value.slice(0, start) + char + draft.value.slice(end)
  requestAnimationFrame(() => {
    el.focus()
    const pos = start + char.length
    el.setSelectionRange(pos, pos)
  })
}


onMounted(async () => {
  chat.ensureConnected()
  ensureInstance()
  if (drawerEl.value) {
    drawerEl.value.addEventListener('shown.bs.offcanvas', onShown)
    drawerEl.value.addEventListener('hidden.bs.offcanvas', onHidden)
  }
  if (import.meta.env.SSR) return
  const { Purchases } = await import('@revenuecat/purchases-capacitor')
  if (!Offcanvas) {
    const module = await import('bootstrap/js/dist/offcanvas')
    Offcanvas = module.default
  }
  await import('emoji-picker-element')
})


onBeforeUnmount(() => {
  if (drawerEl.value) {
    drawerEl.value.removeEventListener('shown.bs.offcanvas', onShown)
    drawerEl.value.removeEventListener('hidden.bs.offcanvas', onHidden)
  }
})

</script>

<template>
  <div class="offcanvas offcanvas-end bg-black-custom border border-1 border-warning" tabindex="-1"  id="chatDrawer" aria-labelledby="chatLabel" ref="drawerEl">
    <div class="offcanvas-header mt-3 mb-1 py-0 xs-limited-width-canvass sticky-top">
      <h5 id="chatLabel" class="mb-0 text-warning" style="font-size:1.2rem;">Chat</h5>
      <button type="button" class="btn rounded-circle btn-outline-warning fw-bold d-flex align-items-center justify-content-center ms-auto" @click="onHidden" style="font-size:1.2rem; width:30px; height:30px;"><span class="mb-1">x</span></button>                     
    </div>

    <div class="offcanvas-body d-flex flex-column p-0 pt-0 xs-limited-width-canvass">
      <div class="border-bottom border-warning p-2">
        
        <v-select v-model="chat.activeThreadId" :options="chat.threads" :get-option-label="t => (chat.unreadByThread.get(t.id) || 0) > 0 ? `${t.title || formatParticipants(t.participants)} (${chat.unreadByThread.get(t.id)})` : (t.title || formatParticipants(t.participants))" :reduce="t => t.id" :placeholder="t('chatdrawervue.select_a_chat')" style="cursor: pointer;" class="form-control rounded-1 my-sm border-focus border border-1 xs-limited-width-canvass text-secondary" :clearable="false" :searchable="false"/>
        
        <div class="input-group mt-3 xs-limited-width-canvass">
          <input v-model="ChooseTitle" id="title-input" type="text" class="form-control my-sm border-focus border border-1  " :placeholder="t('chatdrawervue.choose_a_title')" autocomplete="off">
          <button class="btn btn-outline-warning-onblack fw-bold my-button-dim" :disabled="(users_chat.length===0 && !chat.activeThreadId)" @click="changeTitle">{{ t('chatdrawervue.apply') }}</button>
        </div>
        <input v-model="searchText" @input="searchUser" id="search-input" class="form-control my-sm rounded-1 xs-limited-width-canvass w-100 border-focus border border-1 mt-3 mb-2"  :placeholder="t('searchjs.search_user')" autocomplete="off">
        <div v-for="user in users" :key="user.id">
          <button v-if="user.id !== userStore.user.id && !users_chat.some(u => u.id === user.id)" class="btn btn-sm btn-outline-warning w-100 text-start" @click="addUserToChat(user)">+ {{user.username}}</button>
          <button v-if="user.id !== userStore.user.id && users_chat.some(u => u.id === user.id)" class="btn btn-sm btn-outline-warning w-100 text-start" @click="remUserFromChat(user)">- {{user.username}}</button>
        </div>
      </div>
      
      <span v-if="users_chat.length>0 && !chat.activeThreadId" class="text-warning ms-2 mt-2 w-75 font-size-chat">{{ t('chatdrawervue.chatting_to') }} {{usersChatNames}}</span>
      
      <div v-if="chat.activeThreadId" class="d-flex justify-content-between">
        <span class="text-warning ms-2 mt-2 w-75 font-size-chat">{{ t('chatdrawervue.in_chat') }}: {{formatParticipants(ThreadParticipants)}}</span>
        <span @click="ToggleAddUser" class="text-warning text-end mt-2 me-1" style="cursor: pointer; margin-left: 2.5rem"><i class="bi bi-plus-circle me-0" style="font-size:1.3rem;"></i></span>
        <span @click="leaveGroupChat" class="text-danger text-end mt-1 me-1" style="cursor: pointer;"><i class="bi bi-door-open" style="font-size:1.7rem;"></i></span>
      </div>
              
      <div class="flex-grow-1 overflow-auto p-2" ref="listEl">
        <div v-for="m in chat.activeMessages" :key="m.id" class="mb-3">
          <div v-if="m.isFirstUnread" class="separator d-flex align-items-center text-danger my-3">
            <div class="small flex-grow-1 border-top border-danger"></div>
              <span class="font-size-chat mx-2">{{ t('chatdrawervue.last_read') }}</span>
            <div class="small flex-grow-1 border-top border-danger"></div>
          </div> 
          <div v-if="userStore?.user && m.sender!==userStore?.user.username">
            <div v-if="m.parent_id" class="w-50 small bg-dark border border-secondary rounded rounded-2 px-1 py-1" style="font-size:0.7rem; cursor: pointer;" @click="goToParent(m.parent_id)">
              <span class="text-danger">{{ t('chatdrawervue.answer_to') }}: </span>
              {{messagesById.get(m.parent_id).sender}}>{{ messagesById.get(m.parent_id).text.length > 50 ? messagesById.get(m.parent_id).text.slice(0, 50) + '…' : messagesById.get(m.parent_id).text }}
              <span v-if="messagesById.get(m.parent_id).attachments" v-for="att in messagesById.get(m.parent_id).attachments" class="me-1">
                {{ att.mime?.startsWith('image/') ? '🖼️' : att.mime?.startsWith('video/') ? '🎬' : att.mime==='application/pdf' ? '📄' : '📎' }}
              </span>
            </div>
            <div class="flex-grow-1" :id="`message-${m.id}`"> 
              <span v-if="m.senderId !== 0" class="text-danger me-1 font-size-chat text-break" @click="m.text !== 'This message has been deleted...' && toggleActions(m.id)" style="cursor: pointer;" >{{ m.sender }}></span>
              <span v-if="m.senderId !== 0 && m.text !== 'This message has been deleted...'" class="text-break font-size-chat color-chat-p" style="margin-top: -9px; cursor: pointer;" @click="toggleActions(m.id)">{{ m.text }}</span>
              <span v-if="m.senderId !== 0 && m.text === 'This message has been deleted...'" class="text-break font-size-chat color-chat-p" style="margin-top: -9px;">{{ t('chatdrawervue.message_deleted') }}</span>
              <span v-if="m.senderId === 0" class="text-break font-size-chat color-chat-p" style="margin-top:-9px;">{{ systemText(m) }}</span> 
            </div>
            <div v-for="att in m.attachments" :key="att.id" class="attachment mb-1">
              <img v-if="att.mime?.startsWith('image/')" :src="att.variants?.md ? `${att.variants.md}` : `${att.url}`" class="rounded border border-warning enhanced-img" loading="lazy" decoding="async" style="cursor: pointer;" @click="m.senderId !== 0 && m.text !== t('chatdrawervue.message_deleted') && toggleActions(m.id)"/>
              <video v-else-if="att.mime?.startsWith('video/')" :src="`${att.url}`" :poster="`${att.thumbnail}`" controls playsinline preload="metadata" class=" rounded border border-warning enhanced-video" style="margin-left: 0rem;" ></video>
              <a v-else :href="`${att.url}`" class="font-size-chat text-break" target="_blank" rel="noopener noreferrer">📎 {{ att.name || 'attachment' }}</a>
            </div>            
            <div v-if="showActions[m.id]">
              <div class="position-relative">
                <i class="bi bi-emoji-smile btn-like border-0 bg-transparent me-0" @click="togglePickerMes(m.id)" style="cursor: pointer;"></i>
                <emoji-picker v-if="activePickerId === m.id" data-source="/emoji/data.json" @emoji-click="(e) => onEmojiClickMes(e, m.id)" class="position-absolute z-3 bg-dark border rounded p-2" style="top: 100%; left: 0;"> </emoji-picker>      
                <i class="bi bi-reply btn-like border-0 bg-transparent me-0" @click="toggleParentId(m.id)" style="cursor: pointer;"></i>
              </div>
            </div>
            <div v-for="r in m.reactionCounts" class="d-inline-flex align-items-center position-relative" :key="r.emoji">
              <span class="btn-like-emoji" @click="toggleEmojiUsers(r.emoji, m)" style="cursor: pointer;" >{{ r.emoji }}</span>
              <span class="me-2" @click="" style="cursor: pointer; font-size: 0.7rem;" >{{ r.count }}</span>
              <div v-if="openEmoji === r.emoji && openMeassage === m" class="position-absolute bg-dark border border-warning rounded shadow-sm px-2" style="top: 100%;"> 
                <div v-for="user in m.reactions.filter(u => u.emoji === r.emoji)" :key="user.userId" class="" >                  
                  <span v-if="user.username === userStore.user.username" @click="chat.AddMessageReact({ messageId: m.id, emoji: r.emoji })" style="cursor: pointer;" class="text-danger ">{{ user.username }} </span>                  
                  <span v-else> {{ user.username }} </span>
                </div>
              </div> 
            </div>
            <div class="small text-danger font-size-date">{{formatTime(m.ts) }}</div>
          </div>
          <div v-else>
            <div v-if="m.parent_id" class="w-50 small mx-2 bg-dark border border-secondary rounded rounded-2 px-1 mb-2 py-1 ms-auto" style="font-size:0.7rem; cursor: pointer;" @click="goToParent(m.parent_id)">
              <span class="text-danger">{{ t('chatdrawervue.answer_to') }}: </span>
              {{messagesById.get(m.parent_id).sender}}>{{ messagesById.get(m.parent_id).text.length > 50 ? messagesById.get(m.parent_id).text.slice(0, 50) + '…' : messagesById.get(m.parent_id).text }}
              <span v-if="messagesById.get(m.parent_id).attachments" v-for="att in messagesById.get(m.parent_id).attachments" class="me-1">
                {{ att.mime?.startsWith('image/') ? '🖼️' : att.mime?.startsWith('video/') ? '🎬' : att.mime==='application/pdf' ? '📄' : '📎' }}
              </span>
            </div>
            <div class="text-end flex-grow-1" style="gap: 8px;" :id="`message-${m.id}`">   
              <span class="text-danger float-end ms-1 font-size-chat" @click="m.senderId !== 0 && m.text !== 'This message has been deleted...' && toggleActions(m.id)" style="cursor: pointer;"><{{ m.sender }}</span>
              <span v-if="m.text !== 'This message has been deleted...'" class="text-break font-size-chat color-chat-p" style="margin-top: -9px; cursor: pointer;" @click="m.senderId !== 0 && m.text !== 'This message has been deleted...' && toggleActions(m.id)">{{ m.text }}</span>
              <span v-if="m.text === 'This message has been deleted...'" class="text-break font-size-chat color-chat-p" style="margin-top: -9px; " @click="m.senderId !== 0 && m.text !== 'This message has been deleted...' && toggleActions(m.id)">{{ t('chatdrawervue.message_deleted') }}</span>       
                     
              <div v-if="!m.text && m.attachments.length" class="d-block w-100">
                <div style="height:29px;"></div>
              </div>  
            </div>  
            <div v-for="att in m.attachments" :key="att.id" class=" mb-1 text-end ">
              <img v-if="att.mime?.startsWith('image/')" :src="att.variants?.md ? `${att.variants.md}` : `${att.url}`" class="rounded border border-warning enhanced-img" loading="lazy" decoding="async" style="cursor: pointer;" @click="m.senderId !== 0 && m.text !== t('chatdrawervue.message_deleted') && toggleActions(m.id)"/>
              <video v-else-if="att.mime?.startsWith('video/')" :src="`${att.url}`" :poster="`${att.thumbnail}`" controls playsinline preload="metadata" class=" rounded border border-warning enhanced-video" > </video>
              <a v-else :href="`${att.url}`" class="font-size-chat text-break" target="_blank" rel="noopener noreferrer">📎 {{ att.name || 'attachment' }}</a>
            </div>         
            <div v-if="showActions[m.id]" class="text-end">
              <i class="bi bi-trash btn-like border-0 bg-transparent me-2" @click="deleteMessage(m.id)" style="cursor: pointer;"></i>
            </div>                         
            <div class="d-flex justify-content-end text-end">
              <div v-for="r in m.reactionCounts" class="d-inline-flex align-items-center position-relative" :key="r.emoji">
                <span class="btn-like-emoji" @click="toggleEmojiUsers(r.emoji, m)" style="cursor: pointer;" >{{ r.emoji }}</span>
                <span class="me-2" @click="" style="cursor: pointer; font-size: 0.7rem;" >{{ r.count }}</span>
                <div v-if="openEmoji === r.emoji && openMeassage === m" class="position-absolute bg-dark border border-warning rounded shadow-sm px-2" style="top: 100%;  left: -2.5rem;">
                  <div v-for="user in m.reactions.filter(u => u.emoji === r.emoji)" :key="user.userId" class="">
                    {{ user.username }}
                  </div>
                </div>
              </div>
            </div>
            <div class=" text-danger text-end font-size-date" >{{formatTime(m.ts) }}</div>       
          </div>
        </div>
        </div>
        <div>
      </div>
      
      <div v-if="parentMessage" class="mx-3 bg-dark border border-danger rounded rounded-2 px-3 py-3 mt-n2">
        <span class="text-danger mx-2">{{ t('chatdrawervue.answering_to') }}: </span>
        {{parentMessage.sender}}>{{ parentMessage.text.length > 50 ? parentMessage.text.slice(0, 50) + '…' : parentMessage.text }}
        <span v-if="parentMessage.attachments" v-for="att in parentMessage.attachments" class="me-1">
          {{ att.mime?.startsWith('image/') ? '🖼️' : att.mime?.startsWith('video/') ? '🎬' : att.mime==='application/pdf' ? '📄' : '📎' }}
        </span>
      </div>
      
      <span class="mt-1"></span>
      
      <div class="border-top border-warning p-2">
        <div class="input-group position-relative align-items-center">
          <emoji-picker v-if="showPicker" data-source="/emoji/data.json" @emoji-click="onEmojiClick" class="position-absolute z-3 bg-dark border rounded p-2" style="top: 100%; left: 0;"> </emoji-picker>
          <button class="btn-like border border-1 bg-dark rounded-top-left-e rounded-bottom-left-e" @click="showPicker = !showPicker"  :class="{ 'btn-active': draft.length > 0 }" id="chat_emoji_btn">🙂</button>
          
          <input id="chat-file" type="file" accept="image/*,video/*,application/pdf" hidden @change="onFileChange" />
          <label for="chat-file" class="btn-like border border-1 bg-dark" :class="{ 'btn-active':  draft.length > 0}" title="Attach" style="cursor:pointer" id="chat_attach_label">📎</label>
          
          <div class="flex-grow-1">
          <textarea ref="msgInput" v-model="draft" class="form-control border-focus border border-1 rounded-0 xs-form-fields" :class="{ 'border-focus-always': draft.length > 0 }" :placeholder="t('chatdrawervue.type_a_message')"  @paste="onPaste" @drop.prevent="onDrop" @keydown.enter.exact.prevent="send" @input="checkOverflow" @keydown.enter.shift.exact.stop style="resize:none" id="chat_textarea"></textarea>
          </div>
          <button class="btn btn-outline-warning-onblack fw-bold btn-like-send my-button-dim" @click="send" :disabled="!canSend">{{ t('forgotpasswordvue.send') }}</button>
        </div>
        <div class="d-flex small text-muted mt-1 px-1 align-items-center">
          <div v-if="attachments.length" class="d-flex flex-wrap small">
            <span v-for="a in attachments" :key="a.id" class="badge" style="font-size: 1rem;">
               <span style="cursor:pointer" @click="removeAtt(a.id)">{{ a.mime?.startsWith('image/') ? '🖼️' : a.mime?.startsWith('video/') ? '🎬' : a.mime==='application/pdf' ? '📄' : '📎' }}</span>
            </span>
          </div>
          <span v-if="chat.isConnecting">{{ t('chatdrawervue.connecting') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>



<style scoped>
@media (max-width: 450px) {

  .vselect-anchor {
  position: relative;
  overflow: visible;  /* critical: don't clip the menu */
  }
  .v-select-drawer { max-width: 89vw; }

  :deep(.v-select-drawer .vs__dropdown-toggle) {
    max-width: 100%;
  }

  :deep(.v-select-drawer .vs__dropdown-menu) {
    /* keep dropdown inside the viewport */
    max-width: 100%;
  }

  :deep(.v-select-drawer .vs__dropdown-option) {
    white-space: normal;
    word-break: break-word;     /* wrap long labels instead of overflowing */
  }
}
</style>

