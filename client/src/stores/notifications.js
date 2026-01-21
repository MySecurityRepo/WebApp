// notifications.js (Pinia, plain JS)
import { defineStore } from 'pinia'
import { useChatStore } from './chat'
import { useLangStore } from './lang'


export const useNotificationsStore = defineStore('notifications', {
  state: () => ({ items: [], unread: 0, attached: false }),
  actions: {
    attach() {
      if (this.attached) return
      const langStore = useLangStore()
      const lang = langStore.lang
      const chat = useChatStore()
      chat.ensureConnected()
      const s = chat.socket
      if (!s) return
      s.on('notifications:sync', ({ items, unread}) => {
        this.items = mergeById([], items)
        this.unread = unread
      })
      s.on('notifications:new', (n) => {
        upsert(this.items, n)
        if (!n.isRead) this.unread++
      })
      const request = () => s.emit('notifications:sync_request', {lang})
      s.connected ? request() : s.once('connect', request)
      this.attached = true
    },
    detach(){
      if (!this.attached) return
      this.items = []
      this.unread = 0
      this.attached = false
    },
    sendNotification(commentId) {
      const langStore = useLangStore()
      const lang = langStore.lang
      const chat = useChatStore()
      const s = chat.socket
      if (!s) return
      s.emit('send_notification', { comment_id: commentId, lang: lang },)
    },
    markAllRead() {
      const s = useChatStore().socket
      if (!s || !this.items) return
      const ids = this.items.filter(n => !n.isRead).map(n => n.id)
      if (ids.length === 0) return
      s.emit('notifications:opened', { ids }, (res) => {
        if (!res || !res.ok) return
        const idSet = new Set(ids)
        for (const n of this.items) {
          if (idSet.has(n.id)) n.isRead = true
        }
        this.unread = 0
      })
    },
  }
})

function upsert(arr, n){ const i=arr.findIndex(x=>x.id===n.id); i===-1?arr.unshift(n):arr.splice(i,1,n) }
function mergeById(oldItems, newItems){ const m=new Map(oldItems.map(n=>[n.id,n])); for(const n of newItems) m.set(n.id,{...(m.get(n.id)||{}),...n}); return [...m.values()].sort((a,b)=>b.id-a.id) }
