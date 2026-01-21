<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, reactive, } from 'vue'
import { useUserStore } from '@/stores/user' 
import api from '@/lib/api'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import OrderedList from '@tiptap/extension-ordered-list'
import { Video } from '@/extensions/Video.js'
import CommentNode from '@/components/CommentNode.vue'
import AdCard from '@/components/AdCard.vue'
import Swal from 'sweetalert2'
import { Attachment } from '@/lib/Attachment'
import { useNotificationsStore } from '@/stores/notifications'
import Mention from '@tiptap/extension-mention'
import suggestion from '@tiptap/suggestion'
import tippy from 'tippy.js'
import 'tippy.js/dist/tippy.css'
import { useI18n } from 'vue-i18n'
import { useLangStore } from '@/stores/lang'
import { useHead } from '@vueuse/head'


const { t } = useI18n() 
const userStore = useUserStore()
const notification = useNotificationsStore()
const langStore = useLangStore()
const likes = ref(0)
const liked = ref(false)
const isLiking = ref(false)
const dislikes = ref(0)
const disliked = ref(false)
const isDisliking = ref(false)
const ad = ref(null)
const slot = ref('movies_tablet_320x400')
const ad_type = "movies"


useHead({
  title: "The Books Club",
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/movies-series"
    }
  ]
})


const pickResponsiveSlot = () => {
  const w = window.innerWidth
  if (w <= 450) slot.value = 'movies_mobile_224x150'
  else if (w <= 1024) slot.value = 'movies_tablet_320x400'
  else slot.value = 'movies_desktop_500x630'
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


const attachments = ref([]);

function getEditor(ed) {
  
  if (ed && typeof ed.commands === 'object') return ed
  return ed?.value ?? null
  
}

function extractAttachmentIdsFromEditor(ed) {
  const ids = new Set()
  ed.state.doc.descendants(node => {
    if (node.type?.name === 'attachment' && node.attrs?.id) ids.add(node.attrs.id)
  })
  return [...ids]
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



let observer
const items = ref([])
const page = ref(1)
const loading = ref(false)
const hasMore = ref(true)
const sentinelRef = ref(null)

async function setupObserver() {
  await nextTick() 
  if (!sentinelRef.value) return

  observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !loading.value) loadMore() 
    },
    { root: null, rootMargin: '300px 0px', threshold: 0 }
  ) 							  
  observer.observe(sentinelRef.value)
}



async function loadMore() {
  if (loading.value || !hasMore.value) return
  loading.value = true

  try{
    const res = await api.get(`/retrieve-serie-posts/${page.value}`)
    const rows = (res.data.items || []).map(row => ({
      ...row,
      enhancedBody: enhanceMediaHTML(row.body || '<p><em>Write something here...</em></p>', row.attachments || []),
      created: row.created = new Date(row.created).toLocaleString(),
    }))
    
    hasMore.value = !!res.data.has_more 
    
    if (rows.length) {
      items.value.push(...rows)
      if (hasMore.value) page.value++
      else observer?.disconnect()
    } else {
      hasMore.value = false
      observer?.disconnect()
    }
  } catch (e) {
    hasMore.value = false
  } finally {
    loading.value = false
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
      items.value = items.value.filter(p => p.post_id !== postId)
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
  }
}




const editor = ref(null)
const editorLoading = ref(false)
const editorError = ref(null)
const isFocused = ref(false)
const showPicker = ref(false)
const imageInput = ref(null)

const editableComment = ref({created: "", content: ""})


let initToken = 0


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


const sleep = (ms) => new Promise(r => setTimeout(r, ms))
let mentionReq = 0

async function initEditor() {
  
  if (editor.value || editorLoading.value) return
  editorLoading.value = true
  editorError.value = null
  const token = ++initToken
  
   try {
    
    if (token !== initToken) return

    editor.value = new Editor({
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
            handleFileUpload(file, editor)
            return true
          }
          return false
        }, 
      },
    })
  } catch (e) {
    editorError.value = e instanceof Error ? e.message : String(e)
    destroyEditor()
  } finally {
    if (token === initToken) editorLoading.value = false
  }
}


function destroyEditor() {
  editor.value?.destroy()
  editor.value = null
  editorLoading.value = false
  editorError.value = null
}


function insertEmoji(event) {
  const emoji = event.detail?.unicode
  if (!emoji) return
  editor.value?.commands.insertContent(emoji)
  showPicker.value = false
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


async function showParentComments(item) {
  const postId = item.post_id
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


async function showChildComments(parent, post){
  const postId = post.post_id
  const parentId = parent.comment_id
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
    destroyEditor()
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


const isreplying = ref(false)

async function replyPost(item){

  isreplying.value = true
  const prevN = Number(item.n_comments) || 0
  const content = editableComment.value.content
  
  const ed = getEditor(editor)
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
    editor.value?.commands.clearContent(true)
    editableComment.value.content = ''
    destroyEditor()
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
    
    await showParentComments(item)
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
    item.isreplying = false;
    isreplying.value = false
  }
}

async function replyComment(comment, post){
  
  isreplying.value = true
  const prevN_comments = Number(post.n_comments) || 0
  const prevN_replies = Number(comment.n_replies) || 0
  const content = editableComment.value.content
  
  const ed = getEditor(editor)
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
      if (node) {
        node.showchildren = true
      }
    }
    
    const comment_id = newReply.comment_id;
    notification.sendNotification(comment_id)
    editor.value?.commands.clearContent(true)
    editableComment.value.content = ''
    destroyEditor()
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
    
    await showChildComments(comment, post)
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
    isreplying.value = false
    comment.isreplying = false;
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


const enabled = ref(false)
async function adEnabled(){
  const lang = userStore.user?.lang ?? langStore.lang
  try {
    const res = await api.get(`/ad-enabled`, { params: { ad_type: ad_type, lang:lang }});
    enabled.value = !!res.data.enabled;
  }catch(e){
    enabled.value = false
  }
}


onMounted(async () => {
  
  await setupObserver()
  loadMore()
  pickResponsiveSlot()
  window.addEventListener('resize', pickResponsiveSlot)
  if (import.meta.env.SSR) return
  await import('emoji-picker-element')
  adEnabled()
})


onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  destroyEditor()
})

</script>




<template>
  <div class="container-fluid mt-3 mx-0 px-0">
    <h1 class="text-warning fw-bold">{{ t('serievue.title') }} 📽️</h1>
    <h1 class="text-warning fw-bold mt-5 text-center">{{ (userStore.user?.username?.slice(-1)?.toLowerCase() === 'a' ? t('homevue.welcome2') : t('homevue.welcome')) }} {{userStore.user?.username}}</h1>
    
    <p class="text-center mt-4 p-outside-large"> {{ t('serievue.header') }}</p>
    
    <div v-for="(item, idx) in items" :key="item.post_id" class="post-item mt-4 mx-0 p-0">
      
      <div class="card card-width mx-auto border border-2 border-warning rounded-2 mb-5" >
        <div class="card-body"> 
        
          <RouterLink :to="`/post/${item.post_id}/${item.slug}`" class="text-decoration-none"><h2 class="card-title text-warning text-center fw-bold mb-4">{{ item?.title}}</h2></RouterLink>
            
          <div class="text-secondary text-center enhanced-post" v-html="item.enhancedBody"></div> 
          <div class="d-flex flex-column flex-sm-row justify-content-between align-items-center">
            <div class="margin-post-buttons order-2 order-sm-1">
            
              <button class="btn-like-post border-0 bg-transparent me-0" :disabled="item.isliking || item.isdisliking || !userStore.user || userStore.user.id === item.author_id" @click="toggleLike(item)" :aria-pressed="item.is_liked ? 'true' : 'false'">
                <i class="bi i-post-buttons" :class="item.is_liked ? 'bi-hand-thumbs-up-fill text-danger' : 'bi-hand-thumbs-up text-danger'"></i>
                <span v-if="Number(item.likes) > 0" class="text-danger post-numbers"> {{ item?.likes }} </span>
              </button> 
              
        
              <button class="btn-like-post border-0 bg-transparent me-0" :disabled="item.isliking || item.isdisliking || !userStore.user || userStore.user.id === item.author_id" @click="toggleDislike(item)" :aria-pressed="item.is_disliked ? 'true' : 'false'">
                <i class="bi i-post-buttons" :class="item.is_disliked ? 'bi-hand-thumbs-down-fill text-danger' : 'bi-hand-thumbs-down text-danger'"></i>
                <span v-if="Number(item.dislikes) > 0" class="text-danger post-numbers"> {{ item?.dislikes }} </span>
              </button>
              
              
              <button class="btn-like-post border-0 bg-transparent" :disabled="!userStore.user" @click="toggleReply(item)">
                <i class="bi bi-chat-dots text-danger i-post-buttons"></i>
                <span v-if="Number(item.n_comments) > 0" class="text-danger post-numbers"> {{ item?.n_comments }} </span>
              </button>
              
              
              <button class="btn-like-post border-0 bg-transparent" @click="commentsByPost[item.post_id]?.items.length ? resetComments(item.post_id) : showParentComments(item)" :disabled="commentsByPost[item.post_id]?.loading">
                <i class="bi text-danger i-post-buttons" :class="commentsByPost[item.post_id]?.items.length ? 'bi-dash-circle' : 'bi-plus-circle'"></i>
              </button>
            
              <button v-if="userStore.user?.id===item.author_id" class="btn-like-post border-0 bg-transparent" @click="deletePost(item.post_id)">
                <i class="bi bi-x-circle text-danger i-post-buttons"></i>
              </button>
            </div>
            <RouterLink :to="`/user/${item.author_id}`" class="mt-2 order-1 order-sm-2 text-decoration-none">
              <p class="text-danger order-1 order-sm-2 text-start font-size-created">{{ item?.is_modified ? t('homevue.modified_by') : t('homevue.created_by') }} {{ item?.author_username }} {{ t('homevue.at') }} {{ item?.created }}</p>
            </RouterLink>
          </div>
          
          <div class="separator d-flex align-items-center text-danger my-3">
            <div class="flex-grow-1 border-top border-danger"></div>
            <span class="mx-2">{{ t('homevue.comments') }}</span>
            <div class="flex-grow-1 border-top border-danger"></div>
          </div>
          
          <div v-if="item.isreplying && (replyingId === item.post_id)" class="mb-4">
            <div class="w-50 comment-toolbar"> 
              <div class="comment-toolbar bg-dark border border-2 rounded-top xs-limited-width-alert position-relative d-flex align-items-stretch">
                <button class="rounded-top-left btn-like border border-1 bg-dark text-toolbar" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleBold().run()" :class="{ 'btn-active': editor?.isActive('bold') }"><strong>B</strong></button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleItalic().run()" :class="{ 'btn-active': editor?.isActive('italic') }"><i>I</i></button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleUnderline().run()" :class="{ 'btn-active': editor?.isActive('underline') }"><u>U</u></button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleBulletList().run()" :class="{ 'btn-active': editor?.isActive('bulletList') }">•</button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleOrderedList().run()" :class="{ 'btn-active': editor?.isActive('orderedList') }">1.</button>
                <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="showPicker = !showPicker" :class="{ 'btn-active': showPicker }">💫</button>
                <emoji-picker v-if="showPicker" data-source="/emoji/data.json" @emoji-click="insertEmoji" class="position-absolute z-3 bg-dark border border-2 border-warning rounded p-2" style="top: 100%; left: 0;"> </emoji-picker>
                
                <input id="uploader" type="file" accept="image/*,video/*,application/pdf" @change="onFileChange(editor, $event)" aria-hidden="true" style="display: none"/>
                <button type="button" class="btn-like border btn-attch bg-dark text-toolbar1" :class="{'btn-active': isFileActive}" :disabled="!editor || editorLoading">
                  <label for="uploader" class="btn-like-label p-2 bg-dark text-secondary">📎</label>
                </button>
              </div> 
            </div>
            <div v-if="editorLoading" class="text-secondary small">{{ t('homevue.loading_editor') }}</div>
            <div v-else-if="editorError" class="text-danger small">{{ editorError }}</div>   
            
            <EditorContent v-else :editor="editor" class="my-editor-comment w-50 xs-limited-width-alert text-center border border-2 p-2 border-focus bg-dark rounded-bottom" :class="{ 'border-warning': isFocused }"/>
            <button class="btn btn-outline-warning fw-bold mt-2 me-1 my-button-dim" :disabled="editorLoading || !editor || editor.isEmpty || isreplying" @click="replyPost(item)">{{ t('homevue.comment') }}</button>
            <button class="btn btn-outline-warning fw-bold mt-2 my-button-dim" :disabled="editorLoading || !editor" @click="toggleReply(item)">{{ t('homevue.cancel') }}</button>
          </div>
            
          <template v-if="commentsByPost[item.post_id]?.tree?.length">
             <CommentNode v-for="root in commentsByPost[item.post_id].tree" :key="root.comment_id" :node="root" :depth="0" :editor="editor" :replyingId="replyingId" :isreplying="isreplying" :editorLoading="editorLoading" :editorError="editorError" :isFocused="isFocused" :isFileActive="isFileActive" :user="userStore.user || null"  :getChildState="(postId, parentId) => ensureParentState(postId, parentId)" @like="(node) => toggleCommentLike(node)" @dislike="(node) => toggleCommentDislike(node)" @toggle-reply="(node) => toggleReply(node)" @reply="(node) => replyComment(node, item)" @file-change="onFileChange(editor, $event)" @fetch-children="(node) => showChildComments(node, item)" @delete-comment="(node) => deleteComment(node, item)"/>
          </template> 
          
          <button class="border-0 bg-transparent text-danger mt-1 w-100 text-center class-show-post fw-bold" style="white-space: nowrap;" :disabled="commentsByPost[item.post_id]?.loading" v-if="commentsByPost[item.post_id]?.hasMore && commentsByPost[item.post_id]?.page>1" @click="showParentComments(item)">
             {{ t('homevue.show_more') }}
          </button>
        </div>
      </div>
      <AdCard v-if="(idx + 1) % 7 === 0 && enabled" :slot="slot" :index="idx" :ad_type="ad_type" :lang="userStore.user?.lang ?? langStore.lang"/>
    </div>
    <div id="sentinel" ref="sentinelRef" class="text-center" v-show="hasMore" style="height:1px"></div> 
  </div>                                                                  
</template>
