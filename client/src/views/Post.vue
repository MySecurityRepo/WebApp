<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useUserStore } from '@/stores/user'
import { useRouter, useRoute } from 'vue-router'
import api from '@/lib/api'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import OrderedList from '@tiptap/extension-ordered-list'
import { Video } from '@/extensions/Video.js'
import Swal from 'sweetalert2'
import CommentNode from '@/components/CommentNode.vue'
import { Attachment } from '@/lib/Attachment'
import { useNotificationsStore } from '@/stores/notifications'
import Mention from '@tiptap/extension-mention'
import suggestion from '@tiptap/suggestion'
import tippy from 'tippy.js'
import { useI18n } from 'vue-i18n'



const { t } = useI18n() 
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const notification = useNotificationsStore()
const sleep = (ms) => new Promise(r => setTimeout(r, ms))
const likes = ref(0)
const liked = ref(false)
const isLiking = ref(false)
const dislikes = ref(0)
const disliked = ref(false)
const isDisliking = ref(false)

const post = ref(null)

const options = [
  { label: t('postvue.options_personal'), value: 0 },
  { label: t('postvue.options_book'), value: 1 },
  { label: t('postvue.options_tech'), value: 2 },
  { label: t('postvue.options_series'), value: 3 },
  { label: t('postvue.options_art'), value: 4 },
  { label: t('postvue.options_sport'), value: 5 },
  { label: t('postvue.options_social'), value: 6 }
]

const categoryLabel = computed(() => {
  return options.find(o => o.value === post.value?.category)?.label || 'Uncategorized'
})

const rawPostId = computed(() => route.params.id)
const isCreating = computed(() => rawPostId.value === 'new')
const postId = computed(() => isCreating.value ? null : Number(rawPostId.value))
const postSlug = computed(() => route.params.slug)
const notCommId = computed(() => route.params.commentId)

const loading = ref(true)



watch(
  () => [route.params.id, route.params.slug],   
  ([newId, newSlug], [oldId, oldSlug]) => {
    if (newId === oldId && newSlug === oldSlug) return;
    if (newId === 'new') {
      editablePost.value = {
        created: "",
        title: "",
        body: "",
        category: 0,
        is_modified: 0,
        likes: 0,
      }
      postEditor.value.commands.setContent('')
      post.value = null
      return;
    }
    const n = Number(newId);
    if (!Number.isFinite(n)) return;
    reloadPost(n, newSlug)  
  }
)

watch (
  () => [route.params.id, route.params.slug, route.params.commentId],
  async ([newId, newSlug, newCommId], [oldId, oldSlug, oldCommId]) => {
    if (newId === oldId && newSlug === oldSlug && newCommId === oldCommId) return;
    if (newCommId && postId.value && notCommId.value) await showThreadFromNotification(postId.value, notCommId.value)
  }
)


watch(() => userStore.user, (newId, oldId) => {
  if (newId !== oldId && editing.value) router.push("/")
})

async function reloadPost(id, slug) {
  await fetchPost_by_id(Number(id), slug)
}



function enhanceMediaHTML(rawHTML, attachments = []) {
  const map = new Map(attachments.map(a => [String(a.id), a]));
  const doc = new DOMParser().parseFromString(rawHTML, 'text/html');
  
  doc.querySelectorAll('attachment').forEach(node => {
    const id = String(node.getAttribute('data-id') || '');
    const kind = (node.getAttribute('data-kind') || 'file').toLowerCase();
    const att = map.get(id);
    if (!att) { node.replaceWith(doc.createTextNode('[missing attachment]')); return; }

    if ((kind === 'image') || (att.mime && att.mime.startsWith('image/'))) {
      const img = doc.createElement('img');
      if (att.variants) {
        const sm = att.variants.sm;
        const md = att.variants.md;
        const lg = att.variants.lg;
        img.setAttribute('src', md);
        img.setAttribute('srcset', `${sm} 600w, ${md} 900w, ${lg} 1200w`);
        img.setAttribute('sizes', '100vw');
      } else {
        img.setAttribute('src', att.url);
      }
      img.setAttribute('loading', 'lazy');
      img.setAttribute('decoding', 'async');
      img.classList.add('img-fluid', 'rounded');
      node.replaceWith(img);
      return;
    }

    if ((kind === 'video') || (att.mime && att.mime.startsWith('video/'))) {
      const v = doc.createElement('video');
      v.setAttribute('controls', '');
      v.setAttribute('playsinline', '');
      v.setAttribute('preload', 'metadata');
      v.style.maxWidth = '100%';
      v.setAttribute('src', att.url);
      v.setAttribute('poster', att.thumbnail);
      node.replaceWith(v);
      return;
    }

    const a = doc.createElement('a');
    a.setAttribute('href', att.url);
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
    a.textContent = att.mime === 'application/pdf' ? `📄 ${att.name || 'PDF'}` : `📎 ${att.name || 'attachment'}`;
    node.replaceWith(a);
  });

  return doc.body.innerHTML;
}


async function fetchPost_by_id(postId, postSlug) {
  try {
    const res = await api.get(`/get-post/${postId}/${postSlug}`)
    post.value = res.data,
    post.value.enhancedBody = enhanceMediaHTML(res.data.body || '<p><em>Write something here...</em></p>', res.data.attachments || []),
        
    
    post.value.created = new Date(post.value.created).toLocaleString();
    
    editablePost.value = {
    created: post.value?.created ?? "",
    title: post.value?.title ?? "",
    body: post.value?.body ?? "",
    category: post.value?.category ?? 0,
    is_modified: post.value?.is_modified ?? 0,
    likes: post.value?.likes ?? 0,
    }   
    
    attachments.value = Array.isArray(post.value.attachments) ? post.value.attachments : []
    
    const ed = postEditor.value
    if (ed) ed.commands.setContent(editablePost.value.body || '', false)
    
  } catch(err) {
  
    post.value = null
    router.push('/')
    
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'USER_IS_BLOCKED') text = t('userprofilevue.need_unblock_user')
    else if (message === 'IM_BLOCKED') text = t('postvue.account_blocked_message')
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
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
    router.push('/')
  }
}


const editing = ref(false)

const isAuthor = computed(() =>  { 
  if (!post.value || !userStore.user) return false;
  return userStore.user.id === post.value.author_id;
  });

const editablePost = ref({
    created: "",
    title: "",
    body: "",
    slug: "",
    category: 0,
    is_modified: 0,
    likes: 0,
})


function extractAttachmentIdsFromEditor(ed) {
  const ids = new Set()
  ed.state.doc.descendants(node => {
    if (node.type?.name === 'attachment' && node.attrs?.id) ids.add(node.attrs.id)
  })
  return [...ids]
}


async function saveChanges() {
  try {
    const ed = getEditor(postEditor)
    const payload = {
      ...editablePost.value,                              
      attachment_ids: extractAttachmentIdsFromEditor(ed),
    };
    
    const res = await api.put(`/modify-post/${postId.value}`, payload)
    const post_id = res.data.post_id
    const post_slug = res.data.post_slug

    post.value = res.data.serialized
    post.value.created = new Date(post.value.created).toLocaleString();
    
    editing.value = false
    router.push(`/post/${post_id}/${post_slug}`)
    await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('postvue.post_modified_message'),
      iconHtml: '<i class="bi bi-pencil"></i>',
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
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'TITLE_REQUIRED') text = t('errors.title_is_required')
    else if (message === 'CONTENT_REQUIRED') text = t('errors.content_is_required')
    else if (message === 'TITLE_NOT_ALLOWED') text = t('errors.title_not_allowed')
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
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
  }
}


async function createPost() {
  try {
    
    const ed = getEditor(postEditor)
    const payload = {
      ...editablePost.value,                              
      attachment_ids: extractAttachmentIdsFromEditor(ed),
    };
    
    const res = await api.post(`/create-post`, payload)
    const newPostId = res.data.post_id
    const newPostSlug = res.data.post_slug
    post.value = res.data.serialized
    post.value.created = new Date(post.value.created).toLocaleString();
    
    router.push(`/post/${newPostId}/${newPostSlug}`)
    ensurePostState(newPostId) 
    await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('postvue.post_modified_created'),
      iconHtml: '<i class="bi bi-book-half"></i>',
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
  
  } catch (err) {
  
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'TITLE_REQUIRED') text = t('errors.title_is_required')
    else if (message === 'CONTENT_REQUIRED') text = t('errors.content_is_required')
    else if (message === 'TITLE_NOT_ALLOWED') text = t('errors.title_not_allowed')
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
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
  }
}


const postEditor = ref(null)
const commentEditor = ref(null)
const editorLoading = ref(false)
const editorError = ref(null)
const isFocused = ref(false)
const showPicker = ref(false)
const imageInput = ref(null)


function insertEmojipost(event) {
  const emoji = event.detail.unicode
  postEditor.value?.commands.insertContent(emoji)
  showPicker.value = false
}


function insertEmojicomment(event) {
  const emoji = event.detail.unicode
  commentEditor.value?.commands.insertContent(emoji)
  showPicker.value = false
}


const attachments = ref([]);

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


function getEditor(ed) {
  
  if (ed && typeof ed.commands === 'object') return ed
  return ed?.value ?? null
  
}


let uploadModalOpen = false;
async function handleFileUpload(file, editorLike) {

  const ed = getEditor(editorLike)
  if (!ed) return
  const formData = new FormData()
  formData.append('file', file)

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
    
    const res = await api.post('/upload', formData)
    const uploadId = res.data.upload_id;
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
      const kind = att.mime.startsWith('image/') ? 'image' : att.mime.startsWith('video/') ? 'video' : att.mime === 'application/pdf' ? 'pdf' : 'file'     
      if (!attachments.value.some(a => a.id === att.id)) attachments.value.push(att)
      ed.chain().focus().insertContent({ type: 'attachment', attrs: { id: att.id, kind } }).run()     
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
        confirmButtonText: t('appvue.ok'),
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
      confirmButtonText: t('appvue.ok'),
      customClass: {
        popup: 'swal2-dark-popup',
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
  }
}



const MAX_FILE_MB = 40
const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
const isFileActive = ref(false)
const onFileChange = async (editorLike, e) => {
  const file = e.target.files?.[0]
  try {
    if (!file) return
    isFileActive.value = true
    if (file.size > MAX_FILE_BYTES) {
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
    await handleFileUpload(file, editorLike)
  } finally {
    isFileActive.value = false
    e.target.value = ''
  }
}




function inFlight(item) {
  return item.isliking || item.isdisliking;
}

async function toggleLike(item){

  if (inFlight(item)) return;
  item.isliking = true;
  
  const prevLiked = !!item.is_liked;
  const prevDisliked = !!item.is_disliked;
  const prevLikes    = Number(item.likes) || 0;
  const prevDislikes = Number(item.dislikes) || 0;
  
  item.is_liked = !prevLiked;
  item.is_disliked = false;
  
  item.likes    = Math.max(0, prevLikes + (item.is_liked ? 1 : -1));
  if (prevDisliked && item.is_liked) {
    item.dislikes = Math.max(0, prevDislikes - 1);
  }
  
  try{
    const res = await api.post(`/like-post/${item.post_id}`);
    
    item.is_liked = !!res.data?.liked;
    item.is_disliked = !!res.data?.disliked;
    item.likes    = Number(res.data?.likes ?? item.likes);
    item.dislikes = Number(res.data?.dislikes ?? item.dislikes);
  
  }catch (err) {
    item.is_liked = prevLiked;
    item.is_disliked = prevDisliked;
    item.likes    = prevLikes;
    item.dislikes = prevDislikes;
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('homevue.update_failed'),
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
  }finally {
    item.isliking = false;
  }
}


async function toggleDislike(item){

  if (inFlight(item)) return;
  item.isdisliking = true;
  
  const prevLiked = !!item.is_liked;
  const prevDisliked = !!item.is_disliked;
  const prevLikes    = Number(item.likes) || 0;
  const prevDislikes = Number(item.dislikes) || 0;
  
  item.is_disliked = !prevDisliked;
  item.is_liked    = false
  
  item.dislikes    = Math.max(0, prevDislikes + (item.is_disliked ? 1 : -1));
  if (prevLiked && item.is_disliked) {
    item.likes = Math.max(0, prevLikes - 1);
  }
  
  try{
    const res = await api.post(`/dislike-post/${item.post_id}`);
    
    item.is_liked = !!res.data?.liked;
    item.is_disliked = !!res.data?.disliked;
    item.likes    = Number(res.data?.likes ?? item.likes);
    item.dislikes = Number(res.data?.dislikes ?? item.dislikes);
  
  }catch (err) {
    item.is_liked = prevLiked;
    item.is_disliked = prevDisliked;  
    item.likes    = prevLikes;
    item.dislikes = prevDislikes;
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('homevue.update_failed'),
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
  }finally {
    item.isdisliking = false;
  }
}


function updateList(el, { items = [], command } = {} ) {
  el.innerHTML = ''
  el.__items = items
  items.slice(0, 8).forEach((item, idx) => {
    const row = document.createElement('button')
    row.type = 'button'
    row.className = 'mention-item'
    row.dataset.index = String(idx)
    row.innerHTML = `
      <div class="mi">
        <span class="mi-label">@${item.label ?? item.username ?? item.id}</span>
      </div>`
    row.onclick = () => command(item)
    el.appendChild(row)
  })
  const first = el.querySelector('.mention-item')
  first?.classList.add('is-active')
}


function handleKeys(el, event, props) {
  const items = [...el.querySelectorAll('.mention-item')]
  if (!items.length) return false

  const current = el.querySelector('.mention-item.is-active')
  let idx = current ? items.indexOf(current) : 0

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    items[idx]?.classList.remove('is-active')
    idx = (idx + 1) % items.length
    items[idx].classList.add('is-active')
    items[idx].scrollIntoView({ block: 'nearest' })
    return true
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    items[idx]?.classList.remove('is-active')
    idx = (idx - 1 + items.length) % items.length
    items[idx].classList.add('is-active')
    items[idx].scrollIntoView({ block: 'nearest' })
    return true
  } 
  if (event.key === 'Enter') {
    event.preventDefault()
    const active = el.querySelector('.mention-item.is-active')
    if (active) {
      const i = Number(active.dataset.index)
      const item = (el.__items || [])[i]
      if (item) {
        props.command(item)
        return true
      }
    }
  }
  return false
}


async function fetchUsers(query) {
  
  const url = '/search/users';
  try {
    const res = await api.get(url, { params: { query , limit: 10 } });
    const data = res.data
    if (!data?.items) return []
    return data.items.map(u => ({ id: u.id, label: u.username }))
  } catch (e) {
    return []
  }
}



let mentionReq = 0
const editableComment = ref({created: "", content: ""})
async function initEditor() {
  
  if (commentEditor.value || editorLoading.value) return
  editorLoading.value = true
  editorError.value = null
  
   try {
     commentEditor.value = new Editor({
       content: '',
       extensions: [
         StarterKit.configure({bulletList: true, orderedList: true}),
         Attachment.configure({
           resolve: (id) => attachments.value.find(a => String(a.id) === String(id)) || null,
         }),
         Mention.extend({
            addAttributes() {
              return {
                id: { default: null },        
                label: { default: null },        
                customClass: { default: null },  
              }
           },
           renderHTML({ node }) {
             const label = node.attrs.label ?? node.attrs.username ?? node.attrs.id
             const classes = new Set(['mention'])
             if (node.attrs.customClass && node.attrs.customClass !== 'mention') { classes.add(node.attrs.customClass) }
             return [
               'span',
               { class: Array.from(classes).join(' '), 'data-id': node.attrs.id },
               `@${label}`,
             ]
           },
           parseHTML() {
             return [
               {
                 tag: 'span.mention',
                 getAttrs: el => {
                   const cls = (el.getAttribute('class') || '').split(/\s+/).filter(Boolean)
                   const custom = cls.find(c => c !== 'mention') || null
                   return { customClass: custom }
                 },
               },
             ]
           },           
         }).configure({
           suggestion: {
             char: '@',
             startOfLine: false,
             allowSpaces: false,
             items: async ({ query }) => {
               if (!query) return []
               const token = ++mentionReq
               await sleep(180) 
               const list = await fetchUsers(query)
               return token === mentionReq ? list : []
             },
             render: () => {
               let popup, listEl
               return {
                 onStart: (props) => {
                   listEl = document.createElement('div')
                   listEl.className = 'mention-list'
                   updateList(listEl, props)        
                   popup = tippy('body', {
                     getReferenceClientRect: props.clientRect,
                     appendTo: () => document.body,
                     content: listEl,
                     showOnCreate: true,
                     interactive: true,
                     trigger: 'manual',
                     placement: 'bottom-start',
                     theme: 'mentions',
                     arrow: true,
                   })[0]
                   if (!props.items?.length) popup.hide()
                 },
                 onUpdate: (props) => {
                   popup.setProps({ getReferenceClientRect: props.clientRect })
                   updateList(listEl, props)
                   if (!props.items?.length) popup.hide()
                   else popup.show()
                 },
                 onKeyDown: (props) => {
                   const { event } = props
                   if (event.key === 'Escape') {
                     popup.hide()
                     return true
                   }
                   return handleKeys(listEl, event, props)
                 },
                 onExit: () => {
                   popup?.destroy()
                   popup = null; 
                   listEl = null
                 },
               }
             },
             command: ({ editor, range, props }) => { editor.chain().focus().insertContentAt(range, [{ type: 'mention', attrs: { id: props.id, label: props.label } }, { type: 'text', text: ' ' }, ]).run() },
           },
         }),    
       ],
       onUpdate({ editor: ed }) { editableComment.value.content = ed.getHTML() },
       editorProps: {
         handleDOMEvents: {
           focus: () => { isFocused.value = true; return false },
           blur:  () => { isFocused.value = false; return false },
         },
         handleDrop(view, event) {
           const file = event.dataTransfer?.files?.[0]
           if (file && (file.type.startsWith('image/') || file.type.startsWith('video/') || file.type === 'application/pdf')) {
             handleFileUpload(file, commentEditor)
             return true
           }
           return false
         }, 
       },
     })
   } catch (e) {
     editorError.value = e instanceof Error ? e.message : String(e)
     destroyCommentEditor()
   } finally {
     editorLoading.value = false
   }
}


function destroyCommentEditor() {
  commentEditor.value?.destroy()
  commentEditor.value = null
  editorLoading.value = false
  editorError.value = null
}


const commentsByPost = reactive({})
function ensurePostState(postId) {
  if (!commentsByPost[postId]) {
    commentsByPost[postId] = {
      items: [],
      tree: [],
      page: 1,
      loading: false,
      hasMore: false,
      ids: new Set()
    }
  }
  return commentsByPost[postId]
}


const childrenByParent = reactive({})
function childKey(postId, parentId) {
  return `${postId}:${parentId}`
}


function ensureParentState(postId, parentId) {
  const key = childKey(postId, parentId)
  if (!childrenByParent[key]) {
    childrenByParent[key] = {
      items: [],
      page: 1,
      loading: false,
      hasMore: false,
    }
  }
  return childrenByParent[key]
}


function buildCommentTree(items) {
  const byId = new Map(items.map(c => [c.comment_id, c]))
  for (const c of byId.values()) {
    if (!Array.isArray(c.children)) c.children = []
    else c.children.length = 0
  }

  const roots = []
  for (const c of byId.values()) {
    if (c.parent_id && byId.has(c.parent_id)) {
      byId.get(c.parent_id).children.push(c)
    } else {
      roots.push(c)
    }
  }
  return roots
}


async function showParentComments(postId) {

  const s = ensurePostState(postId)
  if (s.loading) return
  s.loading = true

  try {
    const res = await api.get(`/retrieve-parent-comments/${postId}/${s.page}`)
    const rows = (res.data.comment_items || []).map(r => ({
      ...r,
      enhancedBody: enhanceMediaHTML(r.content || '', r.attachments || []),
    }))

    const idxById = new Map(s.items.map((it, i) => [it.comment_id, i]))

    for (const r of rows) {
      if (idxById.has(r.comment_id)) {
        const i = idxById.get(r.comment_id)
        const node = s.items[i]
        const keepChildren = node.children
        Object.assign(node, r)       
        node.children = keepChildren 
      } else {
        // brand-new parent
        s.items.push({ ...r, children: [] })
        s.ids.add(r.comment_id)
      }
    }

    s.tree = buildCommentTree(s.items)
    s.hasMore = !!res.data.has_more && rows.length === 10
    if (s.hasMore) s.page += 1

  } catch (err) {
    
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
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
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })   
    
  } finally {
    s.loading = false
  }
}


async function showChildComments(parentId, postId){
  const s = ensurePostState(postId)
  const p = ensureParentState(postId, parentId)

  if (p.loading) return
  p.loading = true

  try {
    const res = await api.get(`/retrieve-child-comments/${postId}/${parentId}/${p.page}`)
    const rows = (res.data.comment_items || []).map(r => ({
      ...r,
      enhancedBody: enhanceMediaHTML(r.content || '', r.attachments || []),
    }))

    const start = (p.page - 1) * 15
    p.items.splice(start, rows.length, ...rows)

    let merged = false
    for (const r of rows) {
      if (!s.ids.has(r.comment_id)) {
        s.items.push({ ...r, children: [] })
        s.ids.add(r.comment_id)
        merged = true
      }
    }

    if (merged) s.tree = buildCommentTree(s.items)

    p.hasMore = !!res.data.has_more && rows.length === 15
    if (p.hasMore) p.page += 1
  } catch (err) {
    
    const message = err.response?.data?.message ?? ''
    let text
    
    if (message === 'LIMIT_EXCEEDED') text = t('errors.limit_exceeded')
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
        icon: 'my-swal-icon',
        confirmButton: 'my-swal-btn'
      }
    })
    
  } finally {
    p.loading = false
  }
}


async function showThreadFromNotification(postId, commentId) {
  const s = ensurePostState(postId)
  await showParentComments(postId)
  if (s.loading) return
  s.loading = true
  
  try {
    const res = await api.get(`/retrieve-notification-comments/${postId}/${commentId}`)

    const mapRow = r => ({
      ...r,
      enhancedBody: enhanceMediaHTML(r?.content || '', r?.attachments || []),
      children: []
    })

    const ancestors = (res.data.ancestors || []).map(mapRow)
    const target    = mapRow(res.data.target)

    function upsert(row) {
      if (!row || !row.comment_id) {
        return
      }
      if (!s.ids.has(row.comment_id)) {
        s.items.push(row)
        s.ids.add(row.comment_id)
      } else {
        const i = s.items.findIndex(it => it.comment_id === row.comment_id)
        if (i !== -1) {
          const keepChildren = s.items[i].children
          s.items[i] = { ...s.items[i], ...row, children: keepChildren }
        }
      }
    }

    for (const a of ancestors) {
      upsert(a)
      showChildComments(a.comment_id, postId)
    }
      
    upsert(target)
    s.tree = buildCommentTree(s.items)
    await nextTick();
    s.loading = false
    
    goToComment_highlight(postId, commentId)
    
  } catch (err) {
    s.loading = false
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('deleteconfirmationvue.swall_error_general'),
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
    
  } finally {
    
  }
}
    
    

function resetComments(postId) {
  const state = ensurePostState(postId)
  state.items = []
  state.tree = []
  state.page = 1
  state.loading = false
  state.hasMore = false
  state.ids = new Set()
  
  Object.keys(childrenByParent).forEach(k => {
    if (k.startsWith(`${postId}:`)) delete childrenByParent[k]
  })
  
}



async function toggleCommentLike(comment){

  if (inFlight(comment)) return;
  comment.isliking = true;
  
  const prevLiked = !!comment.is_liked;
  const prevDisliked = !!comment.is_disliked;
  const prevLikes    = Number(comment.likes) || 0;
  const prevDislikes = Number(comment.dislikes) || 0;
  
  comment.is_liked = !prevLiked;
  comment.is_disliked = false;
  
  comment.likes    = Math.max(0, prevLikes + (comment.is_liked ? 1 : -1));
  if (prevDisliked && comment.is_liked) {
    comment.dislikes = Math.max(0, prevDislikes - 1);
  }
  
  try{
    const res = await api.post(`/like-comment/${comment.comment_id}`);
    
    comment.is_liked = !!res.data?.liked;
    comment.is_disliked = !!res.data?.disliked;
    comment.likes    = Number(res.data?.likes ?? comment.likes);
    comment.dislikes = Number(res.data?.dislikes ?? comment.dislikes);
  
  }catch (err) {
    comment.is_liked = prevLiked;
    comment.is_disliked = prevDisliked;
    comment.likes    = prevLikes;
    comment.dislikes = prevDislikes;
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('homevue.update_failed'),
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
  }finally {
    comment.isliking = false;
  }
}



async function toggleCommentDislike(comment){

  if (inFlight(comment)) return;
  comment.isdisliking = true;
  
  const prevLiked = !!comment.is_liked;
  const prevDisliked = !!comment.is_disliked;
  const prevLikes    = Number(comment.likes) || 0;
  const prevDislikes = Number(comment.dislikes) || 0;
  
  comment.is_disliked = !prevDisliked;
  comment.is_liked    = false
  
  comment.dislikes    = Math.max(0, prevDislikes + (comment.is_disliked ? 1 : -1));
  if (prevLiked && comment.is_disliked) {
    comment.likes = Math.max(0, prevLikes - 1);
  }
  
  try{
    const res = await api.post(`/dislike-comment/${comment.comment_id}`);
    
    comment.is_liked = !!res.data?.liked;
    comment.is_disliked = !!res.data?.disliked;
    comment.likes    = Number(res.data?.likes ?? comment.likes);
    comment.dislikes = Number(res.data?.dislikes ?? comment.dislikes);
  
  }catch (err) {
    comment.is_liked = prevLiked;
    comment.is_disliked = prevDisliked;  
    comment.likes    = prevLikes;
    comment.dislikes = prevDislikes;
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('homevue.update_failed'),
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
  }finally {
    comment.isdisliking = false;
  }
}

const replyingId = ref(null) 
let prevTarget = null    

async function toggleReply(target) {
  const id = target.comment_id ?? target.post_id

  if (replyingId.value === id) {
    if (prevTarget) prevTarget.isreplying = false
    replyingId.value = null
    prevTarget = null
    destroyCommentEditor()
    editableComment.value.content = ''
    return
  }

  if (prevTarget) prevTarget.isreplying = false 
  target.isreplying = true     
  replyingId.value = id
  prevTarget = target

  await nextTick()
  await initEditor()
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



function goToComment(commentId) {
  
  if (!commentId) return
  const el = document.getElementById(`comment-${commentId}`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
  waitForStablePosition(el, { quiet: 200, timeout: 2000, threshold: 1 })
    .then(() => {
      el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'nearest' });
    });  
}



function goToComment_highlight(postId, commentId) {

  if (!commentId) return
  requestAnimationFrame(() => {
    const el = document.getElementById(`comment-${commentId}`)
    if (!el) return
    el.classList.add('comment-highlight')
    el.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
    waitForStablePosition(el, { quiet: 200, timeout: 2000, threshold: 1 })
    .then(() => {
      el.scrollIntoView({ behavior: 'auto', block: 'start', inline: 'nearest' });
    });  
  });
}



const isreplying = ref(false)
async function replyPost(item){
  
  isreplying.value = true
  const prevN = Number(item.n_comments) || 0
  const content = editableComment.value.content
  
  const ed = getEditor(commentEditor)
  const payload = {
    ...editableComment.value,                              
    attachment_ids: extractAttachmentIdsFromEditor(ed),
  };
  
  try {
    const res = await api.post(`/create-comment/${item.post_id}`, payload)
    if (res?.data?.n_comments != null) {
      item.n_comments = Number(res.data.n_comments)
    }  
    const newComment = res?.data?.comment
    if (newComment) {
    
      const s = ensurePostState(item.post_id)
      newComment.post_id = item.post_id
      newComment.parent_id = null
      newComment.enhancedBody = enhanceMediaHTML(newComment.content || '', newComment.attachments || [])
      
      let changed = false
      if (!s.ids.has(newComment.comment_id)){
        s.ids.add(newComment.comment_id)
        s.items.push(newComment)
        changed = true
      } else {
        const i = s.items.findIndex(c => c.comment_id === newComment.comment_id)
        if (i !== -1) {
          s.items[i] = { ...s.items[i], ...newComment }
          changed = true
        }
      }
    if (changed) s.tree = buildCommentTree(s.items)
    }
    const comment_id = newComment.comment_id;
    notification.sendNotification(comment_id)
    commentEditor.value?.commands.clearContent(true)
    editableComment.value.content = ''
    destroyCommentEditor()
    replyingId.value = null
    prevTarget = null
    Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('homevue.created_comment_message'),
      iconHtml: '<i class="bi bi-book-half"></i>',
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
    
    await showParentComments(item.post_id)
    goToComment(newComment.comment_id)
    
  }catch (err) {
    item.n_comments = prevN
    Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('deleteconfirmationvue.swall_error_general'),
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
  }finally{
    post.isreplying = false;
    isreplying.value = false
  }
}


async function replyComment(comment, post){

  isreplying.value = true  
  const prevN_comments = Number(post.n_comments) || 0
  const prevN_replies = Number(comment.n_replies) || 0
  const content = editableComment.value.content
  
  const ed = getEditor(commentEditor)
  const payload = {
    ...editableComment.value,                              
    attachment_ids: extractAttachmentIdsFromEditor(ed),
  };
  
  try {
    
    const res = await api.post(`/reply-comment/${comment.comment_id}`, payload )
    
    if (res?.data?.n_replies != null) {
      comment.n_replies = Number(res.data.n_replies)
      post.n_comments = Number(res.data.n_comments)
    }
    
    const newReply     = res?.data?.reply
    const ancestorIds  = res?.data?.ancestors || []
    const parent_username = res?.data?.parent_username || ''
    const s = ensurePostState(post.post_id)
    const p = ensureParentState(post.post_id, comment.comment_id)
    
    if (newReply) {
      newReply.enhancedBody = enhanceMediaHTML(newReply.content || '', newReply.attachments || [])
      newReply.showchildren = false
      newReply.parent_username = parent_username
      
      if (!s.ids.has(newReply.comment_id)) s.ids.add(newReply.comment_id)
      
      const i = s.items.findIndex(c => c.comment_id === newReply.comment_id)
      const j = p.items.findIndex(c => c.comment_id === newReply.comment_id)
      
      if (i === -1) s.items.push(newReply)
      else s.items[i] = { ...s.items[i], ...newReply }
      
      if (j === -1) p.items.push(newReply)
      else p.items[j] = { ...p.items[j], ...newReply }
      
    }
    
    s.tree = buildCommentTree(s.items)
    
    for (const id of ancestorIds) {
      const node = s.items.find(c => c.comment_id === id)
      if (node) node.showchildren = true
    }
    
    notification.sendNotification(newReply.comment_id)
    commentEditor.value?.commands.clearContent(true)
    editableComment.value.content = ''
    destroyCommentEditor()
    replyingId.value = null
    prevTarget = null
    
    Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('homevue.created_comment_message'),
      iconHtml: '<i class="bi bi-book-half"></i>',
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
    
    await showChildComments(comment.comment_id, post.post_id)
    goToComment(newReply.comment_id)
    
    
  }catch (err) {
    
    comment.n_replies = prevN_replies
    post.n_comments = prevN_comments
    Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('deleteconfirmationvue.swall_error_general'),
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
    
  }finally{
    comment.isreplying = false;
    isreplying.value = false
  }
}


function collectDescendantIdsFromFlat(items, rootId) {
  const childrenMap = new Map()
  for (const c of items) {
    if (c.parent_id != null) {
      if (!childrenMap.has(c.parent_id)) childrenMap.set(c.parent_id, [])
      childrenMap.get(c.parent_id).push(c.comment_id)
    }
  }
  const toDelete = new Set()
  const stack = [rootId]
  while (stack.length) {
    const id = stack.pop()
    const kids = childrenMap.get(id) || []
    for (const kid of kids) {
      if (!toDelete.has(kid)) {
        toDelete.add(kid)
        stack.push(kid)
      }
    }
  }
  return toDelete
}


async function deleteComment(comment, post) {
  const result = await Swal.fire({
    title: t('homevue.delete_comment_title'),
    text: t('homevue.delete_post_message'),
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
  })

  if (!result.isConfirmed) return

  try {
  
    const res = await api.delete(`/delete-comment/${comment.comment_id}`)
    
    const data = res?.data ?? {}
    if (data.n_comments != null) {
      post.n_comments = Number(data.n_comments)
    } else {
      post.n_comments = Math.max(0, (Number(post.n_comments) || 0) - 1)
    }
    
    const s = ensurePostState(comment.post_id)
    const descendants = collectDescendantIdsFromFlat(s.items, comment.comment_id)
    const idsToDrop = new Set(descendants)
    idsToDrop.add(comment.comment_id)
    
    Object.keys(childrenByParent).forEach(k => {
      if (!k.startsWith(`${comment.post_id}:`)) return
      const [, parentStr] = k.split(':')
      const parentId = Number(parentStr)
      const cache = childrenByParent[k]
      if (!cache) return
      
      if (idsToDrop.has(parentId)) {
        cache.items = []
        cache.page = 1
        cache.hasMore = false
        cache.loading = false
      } else {
        cache.items = cache.items.filter(c => !idsToDrop.has(c.comment_id))
      }
    })
      
    s.items = s.items.filter(c => !idsToDrop.has(c.comment_id))
    for (const id of idsToDrop) s.ids.delete(id)
    
    if (comment.parent_id != null) {
      const parentNode = s.items.find(c => c.comment_id === (data.parent_id ?? comment.parent_id))
      if (parentNode) {
        parentNode.n_replies = (data.parent_n_replies != null) ? Number(data.parent_n_replies) : Math.max(0, Number(parentNode.n_replies || 0) - (1 + descendants.size))
      }
    }
    s.tree = buildCommentTree(s.items)
    
  } catch (err) {
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('deleteconfirmationvue.swall_error_general'),
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
  }
}


async function deletePost(postId) {
    
  const result = await Swal.fire({
    title: t('homevue.delete_post_title'),
    text: t('homevue.delete_post_message'),
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
    })
        
  try{
      if (!result.isConfirmed) return
      const res = await api.delete(`/delete-post/${postId}`)
      router.push('/');
      await Swal.fire({
      title: t('emailconfirmationvue.swall_success_title'),
      text: t('homevue.deleted_post_message'),
      iconHtml: '<i class="bi bi-book-half"></i> ',
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
    
  } catch(err) {
    await Swal.fire({
      title: t('appvue.swall_error_title'),
      text: t('deleteconfirmationvue.swall_error_general'),
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
    router.push('/')
  }
}


onBeforeUnmount(() => {
  postEditor.value?.destroy()
  commentEditor.value?.destroy()
  postEditor.value = null
  commentEditor.value = null
  replyingId.value = null
  prevTarget = null
})


onMounted(async () => {

  if (!isCreating.value && postId.value && postSlug.value) {
  await fetchPost_by_id(postId.value, postSlug.value)
  ensurePostState(post.value.post_id) 
  } else {
    editablePost.value = {
      created: '',
      title: '',
      body: '',
      category: 0,
      is_modified: 0,
      likes: 0,
    };
  }
  if (postId.value && notCommId.value)  await showThreadFromNotification(postId.value, notCommId.value)
  
  loading.value = false
  
  postEditor.value = new Editor({
    content: editablePost.value.body || '',
    extensions: [
      StarterKit.configure({
        bulletList: true,
        orderedList: true,
      }),
      Attachment.configure({
      resolve: (id) => attachments.value.find(a => String(a.id) === String(id)) || null,
      }),
    ],
    onUpdate({ editor }) {
      editablePost.value.body = editor.getHTML()
    },
    editorProps: {
      handleDOMEvents: {
        focus: () => {
          isFocused.value = true
          return false
        },
        blur: () => {
          isFocused.value = false
          return false
        },
      },
      handleDrop(view, event) {
        const file = event.dataTransfer.files?.[0]
        if (file && (file.type.startsWith('image/') || file.type.startsWith('video/') || file.type === 'application/pdf')) {
          handleFileUpload(file, postEditor)
          return true
          }
        return false
      }, 
    },
  })
  if (import.meta.env.SSR) return
  await import('emoji-picker-element')
})

</script>





<template>
  
  <div class="container-fluid margin-top-post mx-0 px-0">
    
    <div v-if="postEditor && ((editing && isAuthor) || isCreating)">
    
      <h2 class="text-warning fw-bold ">{{ post?.title || t('postvue.create_post') }}</h2>
    
      <div class="mb-3 justify-content-center"> 
        <input v-model="editablePost.title" class=" form-control form-control-lg border-2 border-warning xs-form-fields mt-3 editable-post-width border-focus" type="text" :placeholder="t('postvue.title_placeholder')"/>
      </div>
    
      <div class="mb-3"> 
        <v-select v-model="editablePost.category" :options="options" label="label" :reduce="o => o.value" class=" form-control form-control-lg border-2 border-warning xs-form-fields editable-post-width" :clearable="false" :searchable="false"/>
      </div>
      
      <div class="mb-3"> 
        <div class="editor-toolbar bg-dark border border-2 border-warning rounded-top xs-limited-width-alert position-relative d-flex align-items-stretch w-75">
          <button class="rounded-top-left btn-like border border-1 bg-dark text-toolbar" :disabled="!postEditor || editorLoading" @click="postEditor?.chain().focus().toggleBold().run()" :class="{ 'btn-active': postEditor?.isActive('bold') }"><strong>B</strong></button>
          <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!postEditor || editorLoading" @click="postEditor?.chain().focus().toggleItalic().run()" :class="{ 'btn-active': postEditor?.isActive('italic') }"><i>I</i></button>
          <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!postEditor || editorLoading" @click="postEditor?.chain().focus().toggleUnderline().run()" :class="{ 'btn-active': postEditor?.isActive('underline') }"><u>U</u></button>
          <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!postEditor || editorLoading" @click="postEditor?.chain().focus().toggleBulletList().run()" :class="{ 'btn-active': postEditor?.isActive('bulletList') }">•</button>
          <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!postEditor || editorLoading" @click="postEditor?.chain().focus().toggleOrderedList().run()" :class="{ 'btn-active': postEditor?.isActive('orderedList') }">1.</button>
          <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!postEditor || editorLoading" @click="showPicker = !showPicker" :class="{ 'btn-active': showPicker }">💫</button>
          <emoji-picker v-if="showPicker" data-source="/emoji/data.json" @emoji-click="insertEmojipost" class="position-absolute z-3 bg-dark border rounded p-2 border-2 border-warning" style="top: 100%; left: 0;"> </emoji-picker>
          <input id="uploader-post" type="file" accept="image/*,video/*,application/pdf" @change="onFileChange(postEditor, $event)" aria-hidden="true" style="display: none"/>
          <button type="button" class="btn-like border btn-attch bg-dark text-toolbar1" :class="{'btn-active': isFileActive}" :disabled="!postEditor || editorLoading">
            <label for="uploader-post" class="btn-like-label p-2 bg-dark text-secondary">📎</label>
          </button>
        </div>     
        <EditorContent :editor="postEditor" class="my-editor xs-limited-width-alert w-75 text-center border border-2 p-2 border-warning bg-dark rounded-bottom" :class="{ 'border-warning': isFocused }"/>
      </div>
       
      <div class="mb-3">
        <div v-if="isCreating">
          <button class="btn btn-outline-warning fw-bold my-button-dim" @click="createPost">{{ t('postvue.create') }}</button>
        </div>
        <div v-else>
          <button class="btn btn-outline-warning fw-bold my-button-dim" :disabled="!postEditor || editorLoading || postEditor.isEmpty" @click="saveChanges">{{ t('postvue.save') }}</button>
          <button class="ms-2 btn btn-outline-warning fw-bold my-button-dim" @click="deletePost(postId)">{{ t('postvue.delete') }}</button>
          <button class="ms-2 btn btn-outline-warning fw-bold my-button-dim" @click="editing = false">{{ t('homevue.cancel') }}</button>
        </div>
      </div>
    </div> 
    <div v-else>    
      <div v-if="post" class="m-0 p-0">
      
      <div class="card card-width mx-auto border border-2 border-warning rounded-2 mt-5" >
        <div class="card-body">
          <div class="d-flex gap-1 justify-content-center align-items-center"> 
            <h2 class="card-title justify-content-center text-center text-warning fw-bold mb-4">{{ post?.title}}</h2>
          </div>
          
          <div class="text-secondary text-center enhanced-post" v-html="post.enhancedBody"></div>

          <div class="d-flex flex-column flex-sm-row justify-content-between align-items-center">
            <div class=" order-2 order-md-1 margin-post-buttons">
            
              <button class="btn-like-post border-0 bg-transparent me-0" :disabled="post.isliking || post.isdisliking || !userStore.user || userStore.user.id === post.author_id" @click="toggleLike(post)" :aria-pressed="post.is_liked ? 'true' : 'false'">
                <i class="bi i-post-buttons" :class="post.is_liked ? 'bi-hand-thumbs-up-fill text-danger' : 'bi-hand-thumbs-up text-danger'"></i>
                <span v-if="Number(post.likes) > 0" class="text-danger post-numbers"> {{ post?.likes }} </span>
              </button> 
              
        
              <button class="btn-like-post border-0 bg-transparent me-0" :disabled="post.isliking || post.isdisliking || !userStore.user || userStore.user.id === post.author_id" @click="toggleDislike(post)" :aria-pressed="post.is_disliked ? 'true' : 'false'">
                <i class="bi i-post-buttons" :class="post.is_disliked ? 'bi-hand-thumbs-down-fill text-danger' : 'bi-hand-thumbs-down text-danger'"></i>
                <span v-if="Number(post.dislikes) > 0" class="text-danger post-numbers"> {{ post?.dislikes }} </span>
              </button>
              
              
              <button class="btn-like-post border-0 bg-transparent" :disabled="!userStore.user" @click="toggleReply(post)">
                <i class="bi bi-chat-dots text-danger i-post-buttons"></i>
                <span v-if="Number(post.n_comments) > 0" class="text-danger post-numbers"> {{ post?.n_comments }} </span>
              </button>
              
              
              <button class="btn-like-post border-0 bg-transparent" @click="commentsByPost[post.post_id]?.items.length ? resetComments(post.post_id) : showParentComments(post.post_id)" :disabled="commentsByPost[post.post_id]?.loading">
                <i :class="commentsByPost[post.post_id]?.items.length ? 'bi-dash-circle text-danger' : 'bi-plus-circle text-danger'" class="bi i-post-buttons"></i>            
              </button>
            
              <button v-if="isAuthor" class="btn-like-post border-0 bg-transparent" @click="editing = !editing" :disabled="!isAuthor">
                <i class="text-danger bi bi-pencil i-post-buttons"></i>
              </button>
              
            </div>
            <RouterLink :to="`/user/${post.author_id}`" class="mt-2 order-1 order-sm-2 text-decoration-none">
              <p class="text-danger order-1 order-sm-2 text-start font-size-created">{{ post?.is_modified ? t('homevue.modified_by') : t('homevue.created_by') }} {{ post?.author_username }} {{ t('homevue.at') }} {{ post?.created }}</p>
            </RouterLink>
          </div>
          
          <div class="separator d-flex align-items-center text-danger my-3">
            <div class="flex-grow-1 border-top border-danger"></div>
            <span class="mx-2">{{ t('homevue.comments') }}</span>
            <div class="flex-grow-1 border-top border-danger"></div>
          </div>  
          
          <div v-if="post.isreplying && replyingId === post.post_id" class="mb-4">
            <div class="w-50 comment-toolbar"> 
              <div class="comment-toolbar bg-dark border border-2 rounded-top xs-limited-width-alert position-relative d-flex align-items-stretch">
                <button class="rounded-top-left btn-like border border-1 bg-dark text-toolbar" :disabled="!commentEditor || editorLoading" @click="commentEditor?.chain().focus().toggleBold().run()" :class="{ 'btn-active': commentEditor?.isActive('bold') }"><strong>B</strong></button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!commentEditor || editorLoading" @click="commentEditor?.chain().focus().toggleItalic().run()" :class="{ 'btn-active': commentEditor?.isActive('italic') }"><i>I</i></button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!commentEditor || editorLoading" @click="commentEditor?.chain().focus().toggleUnderline().run()" :class="{ 'btn-active': commentEditor?.isActive('underline') }"><u>U</u></button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!commentEditor || editorLoading" @click="commentEditor?.chain().focus().toggleBulletList().run()" :class="{ 'btn-active': commentEditor?.isActive('bulletList') }">•</button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!commentEditor || editorLoading" @click="commentEditor?.chain().focus().toggleOrderedList().run()" :class="{ 'btn-active': commentEditor?.isActive('orderedList') }">1.</button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!commentEditor || editorLoading" @click="showPicker = !showPicker" :class="{ 'btn-active': showPicker }">💫</button>
                <emoji-picker v-if="showPicker" data-source="/emoji/data.json" @emoji-click="insertEmojicomment" class="position-absolute z-3 bg-dark border border-2 border-warning rounded p-2" style="top: 100%; left: 0;"> </emoji-picker>
                <input id="uploader-comment" type="file" accept="image/*,video/*,application/pdf" @change="onFileChange(commentEditor, $event)" aria-hidden="true" style="display: none"/>
                <button type="button" class="btn-like border btn-attch bg-dark text-toolbar1" :class="{'btn-active': isFileActive}" :disabled="!commentEditor || editorLoading"> 
                  <label for="uploader-comment" class="btn-like-label p-2 bg-dark text-secondary">📎</label>
                </button>
              </div> 
            </div>
            <div v-if="editorLoading" class="text-secondary small">{{ t('homevue.loading_editor') }}</div>
            <div v-else-if="editorError" class="text-danger small">{{ editorError }}</div>   
            <EditorContent v-else :editor="commentEditor" class="my-editor-comment w-50 xs-limited-width-alert text-center border border-2 p-2 border-focus bg-dark rounded-bottom" :class="{ 'border-warning': isFocused }"/>
            <button class="btn btn-outline-warning fw-bold mt-2 me-1 my-button-dim" :disabled="editorLoading || !commentEditor || commentEditor.isEmpty || isreplying" @click="replyPost(post)">{{ t('homevue.comment') }}</button>
            <button class="btn btn-outline-warning fw-bold mt-2 my-button-dim" :disabled="editorLoading || !commentEditor" @click="toggleReply(post)">{{ t('homevue.cancel') }}</button>
          </div>
            
          <template v-if="commentsByPost[post.post_id]?.tree?.length">
             <CommentNode v-for="root in commentsByPost[post.post_id].tree" :key="root.comment_id" :node="root" :depth="0" :editor="commentEditor" :replyingId="replyingId" :isreplying="isreplying" :editorLoading="editorLoading" :editorError="editorError" :isFocused="isFocused" :isFileActive="isFileActive" :user="userStore.user || null"  :getChildState="(postId, parentId) => ensureParentState(postId, parentId)" @like="(node) => toggleCommentLike(node)" @dislike="(node) => toggleCommentDislike(node)" @toggle-reply="(node) => toggleReply(node)" @reply="(node) => replyComment(node, post)" @file-change="onFileChange(commentEditor, $event)" @fetch-children="(node) => showChildComments(node.comment_id, post.post_id)" @delete-comment="(node) => deleteComment(node, post)"/>
          </template>  
          <button class="border-0 bg-transparent text-danger mt-1 w-100 text-center class-show-post fw-bold" style="white-space: nowrap;" :disabled="commentsByPost[post.post_id]?.loading" v-if="commentsByPost[post.post_id]?.hasMore && commentsByPost[post.post_id]?.page>1" @click="showParentComments(post.post_id)">
             {{ t('homevue.show_more') }}
          </button>
        </div>
      </div>
      
      </div>
    </div>
  </div>
</template> 





