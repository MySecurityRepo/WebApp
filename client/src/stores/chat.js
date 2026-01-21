import { defineStore } from 'pinia'
import { useNotificationsStore } from './notifications'
import { useLangStore } from './lang'
import { useCSRFStore } from './csrf'
import { useUserStore } from './user'
import { io } from 'socket.io-client'



export const useChatStore = defineStore('chat', {
  state: () => ({
    socket: null,              
    isConnecting: false,       
    drawerOpen: false,         
    threads: [],               
    activeThreadId: null,        
    messagesByThread: new Map(), 
    unreadByThread: new Map(),   
    _listenersBound: false,
  }),
  
  getters: {
    activeMessages(state) {
      if (!state.activeThreadId) return []
      return state.messagesByThread.get(state.activeThreadId) || []
    },
    unreadCount(state) {
      let sum = 0
      for (const [tid, n] of state.unreadByThread) { 
        if (tid !== state.activeThreadId || !state.drawerOpen) sum += n  
      }
      return sum
    },
  }, 
  actions: {
    setDrawerOpen(open) {
      this.drawerOpen = open
      if (open) this.markActiveAsRead()
    },
    setActiveThread(id) {
      this.activeThreadId = id
      if (this.socket && id) this.socket.emit('join_thread', { threadId: id })
      this.loadActiveThread()
    },
    ensureConnected() {
      if (this.socket || this.isConnecting) return
      const userStore = useUserStore()
      if (!userStore.user) return
      const csrfStore = useCSRFStore()
      const token = csrfStore.token
      if (!token) return
      this.isConnecting = true
      const isNative = Capacitor.isNativePlatform(); 
      const s = isNative ? io("https://thebooksclub.com", { path: '/ws', transports: ['websocket'], pingInterval: 30000, pingTimeout: 200000, withCredentials: true, auth: { csrf: token }, reconnection: true, reconnectionAttempts: Infinity, reconnectionDelay: 1000, reconnectionDelayMax: 5000,}, ) : io({ path: '/ws', transports: ['websocket'], pingInterval: 30000, pingTimeout: 200000, withCredentials: true, auth: { csrf: token }, reconnection: true, reconnectionAttempts: Infinity, reconnectionDelay: 1000, reconnectionDelayMax: 5000,})
      this.socket = s                                                  
      s.on('connect', () => {
        this.isConnecting = false
        s.emit('get_threads', (threads) => {
          this.threads = threads || []
          for (const t of this.threads) {
            this.unreadByThread.set(t.id, t.unread || 0)
          }
          if (this.activeThreadId == null && this.threads.length > 0) {
            this.setActiveThread(this.threads[0].id)
          }
        })
        if (this.activeThreadId) {         
          s.emit('join_thread', { threadId: this.activeThreadId })
          this.loadActiveThread()
        }
        if (!this._listenersBound) {
          this._bindSocketListeners(s)
          this._listenersBound = true
        }
      })
      s.on('disconnect', (reason) => {
      })
      s.on('connect_error', (err) => {      
        this.isConnecting = false
      })
    },
    _bindSocketListeners(s) {                            
      s.on('message', (m) => {
        const arr = this.messagesByThread.get(m.threadId) || []
        let handlerId = Math.random().toString(36).slice(2, 8);
        arr.push(m)
        this.messagesByThread.set(m.threadId, arr)
        const tid = this.activeThreadId
        if (!(this.drawerOpen && this.activeThreadId === m.threadId)) {
          const cur = this.unreadByThread.get(m.threadId) || 0
          this.unreadByThread.set(m.threadId, cur + 1)
        }
      })
      s.on("threads_refresh", () => {
        this.socket.emit("get_threads", (threads) => {
          this.threads = threads || this.threads
          if (this.activeThreadId == null && this.threads.length > 0) {
            this.setActiveThread(this.threads[0].id)   
          }
        })
      })
      s.on('thread_updated', ({ id, title }) => {
        const t = this.threads.find(x => x.id === id)
        if (t) t.title = title
      })
      s.on('added_reaction', ({ threadId }) => {
        const t = this.threads.find(x => x.id === threadId)
        if (!t) return
        this.socket?.emit('get_threads', (threads) => {
          this.threads = threads || this.threads
        })
        this.loadActiveThread()
      })
      s.on('message_deleted', ({ threadId }) => {
        const t = this.threads.find(x => x.id === threadId)
        if (!t) return
        this.socket?.emit('get_threads', (threads) => {
          this.threads = threads || this.threads
        })
        this.loadActiveThread()
      })
      s.on('thread_invited', () => {
        this.socket?.emit('get_threads', (threads) => {
          this.threads = threads || this.threads
        })
      })
    }, 
    loadActiveThread() {
      if (!this.socket || this.activeThreadId == null) return
      this.socket.emit('load_thread', { threadId: this.activeThreadId }, (messages) => { 
        this.messagesByThread.set(this.activeThreadId, messages || [])   
        if (this.drawerOpen) this.markActiveAsRead()
      })
    },
    sendMessage({ text = '', pId = null, attachment_ids = [] }) {
      if (!this.socket || this.activeThreadId == null) return
      const payload = { threadId: this.activeThreadId, text, pId, attachment_ids}
      this.socket.emit('send', payload)
    },
    markActiveAsRead() {
      if (this.activeThreadId == null) return
      const prev = this.unreadByThread.get(this.activeThreadId)
      this.unreadByThread.set(this.activeThreadId, 0)
      const tid = this.activeThreadId
      this.socket.emit('update_last_message_read', { tid }, (res) => {
        if (!res || !res.ok) {
          this.unreadByThread.set(tid, prev)
        }
      })
    },
    createThreadAndSend({ participantIds, text, title, attachment_ids = [] }) {
      if (!this.socket) return
      const t = (text || '').trim()
      const shouldSend = t.length > 0 || (Array.isArray(attachment_ids) && attachment_ids.length > 0)
      this.socket.emit('create_thread', { participantIds, title }, (thread) => {
        if (!thread || !thread.id) return
        if (!this.threads.find(t => t.id === thread.id)) {
          this.threads = [thread, ...this.threads]
        }
        this.setActiveThread(thread.id)
        if (shouldSend) this.sendMessage({ text: t, pId: null, attachment_ids : attachment_ids })
      })
    },
    searchThreadById({participantIds}) {
      if (!this.socket) return
      this.socket.emit('search_thread', { participantIds }, (thread) => {
        if (!thread || !thread.id) {
          this.setActiveThread(null)
          return
        }
        this.setActiveThread(thread.id)
      })
    },
    changeTitle({ title }) {
      if (!this.socket || !this.activeThreadId) return
      const tid = this.activeThreadId
      const t = this.threads.find(x => x.id === tid)
      const prev = t?.title
      if (t) t.title = title
      const langStore = useLangStore()
      const lang = langStore.lang 
      this.socket.emit("change_thread_title", { threadId: tid, title, lang }, (res) => {
        if (!res?.ok) {
          if (t) t.title = prev 
        }
      })  
    },
    leaveGroupChat({ }) {
      if (!this.socket || !this.activeThreadId) return Promise.resolve(false);
      const tid = this.activeThreadId
      const langStore = useLangStore()
      const lang = langStore.lang
      return new Promise((resolve) => {
        this.socket.emit("leave_group_thread", { threadId: tid, lang }, (res) => {
          if (res?.ok) {
            this.threads = this.threads.filter(t => t.id !== tid)
            this.messagesByThread.delete(tid)
            this.unreadByThread.delete(tid)
            resolve(true);
          } else {
            resolve(false);
          }
        })
      })
    },
    AddMessageReact({ messageId, emoji}) {
      if (!this.socket || !this.activeThreadId) return Promise.resolve(false);
      const tid = this.activeThreadId
      return new Promise((resolve) => {
        this.socket.emit("add_message_emoji", { threadId: tid, messageId: messageId, emoji:emoji }, (res) => {
          if (res?.ok) {
            resolve(true)
            this.loadActiveThread()
          } else {
            resolve(false)
          }
        })
      })
    },
    deleteMessage({ messageId }) {
      if (!this.socket || !this.activeThreadId) return Promise.resolve(false);
      const tid = this.activeThreadId
      const langStore = useLangStore()
      const lang = langStore.lang
      return new Promise((resolve) => {
        this.socket.emit("delete_message", { threadId: tid, messageId: messageId, lang:lang }, (res) => {
          if (res?.ok) {
            resolve(true)
            this.loadActiveThread()
          } else {
            resolve(false)
          }
        })
      })
    },
    addUsersToThread({ users_id }) {
      if (!this.socket || !this.activeThreadId) return Promise.resolve(false);
      const tid = this.activeThreadId
      return new Promise((resolve) => {
        this.socket.emit("add_users", { threadId: tid, users_id: users_id }, (res) => {
          if (res?.ok) {
            resolve(true)
            this.socket?.emit('get_threads', (threads) => {
              this.threads = threads || this.threads
            })
            this.setActiveThread(tid)
          } else {
            resolve(false)
          }
        })
      })
    },   
    searchOrCreateThread({ uid, uname  }) {
      if (!this.socket) return
      const t = this.threads.find( x => Array.isArray(x.participants) && x.participants.length === 1 && x.participants[0] === uname );
      this.setDrawerOpen(true)
      if (!t) {
        this.createThreadAndSend( { participantIds: [uid], text: "", title: "", attachment_ids : []} )      
      } else {
        this.setActiveThread(t.id)
      }
    },
    refreshThreads(){
      if (!this.socket) return
      this.socket?.emit('get_threads', (threads) => {
        this.threads = threads || this.threads
      })
    },
  }
})
   
