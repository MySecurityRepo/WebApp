import { Node } from '@tiptap/core'

export const Attachment = Node.create({
  name: 'attachment',
  group: 'inline',
  inline: true,
  atom: true,

  addOptions() {
    return { resolve: () => null }
  },

  addAttributes() {
    return { id: { default: null }, kind: { default: 'file' } }
  },

  parseHTML() {
    return [{
      tag: 'attachment',
      getAttrs: el => {
        const h = (el)
        return { id: h.getAttribute('data-id'), kind: h.getAttribute('data-kind') || 'file' }
      },
    }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['attachment', { 'data-id': HTMLAttributes.id, 'data-kind': HTMLAttributes.kind }]
  },

  addNodeView() {
    return ({ node, editor }) => {
    
      const dom = document.createElement('span')
      dom.className = 'tt-attachment'
      const render = () => {
        dom.textContent = ''
        const id = String(node.attrs.id ?? '')
        const att = this.options.resolve?.(id)

        const kindAttr = node.attrs.kind || 'file'
        const kind = (kindAttr === 'file' && att?.mime) ? (att.mime.startsWith('image/') ? 'image' : att.mime.startsWith('video/') ? 'video' : att.mime === 'application/pdf' ? 'pdf' : 'file') : kindAttr

        if (!att) {
          const span = document.createElement('span')
          span.textContent = '…'
          dom.appendChild(span)
          return
        }
        
        if (att.url) {
          att.url = att.url.replace(/^\//, "");
        }
        
        if (kind === 'image') {
          const img = new Image()
          const md = att.variants?.md ? `${att.variants.md}` : att.url
          img.src = md
          
          img.loading = 'lazy'
          img.decoding = 'async'
          img.className = 'img-fluid rounded'
          img.style.maxWidth = '240px'
          dom.appendChild(img)
          return
        }

        if (kind === 'video') {
          const v = document.createElement('video')
          v.controls = true
          v.playsInline = true
          v.preload = 'metadata'
          v.style.maxWidth = '320px'
          v.poster = att.thumbnail;
          const s = document.createElement('source');
          s.src = att.url;
          if (att.mime) s.type = att.mime;
          v.appendChild(s);
          dom.appendChild(v)
          return
        }


        const a = document.createElement('a')
        a.href = att.url;
        a.target = '_blank'
        a.rel = 'noopener noreferrer'
        a.textContent = att.mime === 'application/pdf' ? `📄${att.name || 'PDF'}` : `📎 ${att.name || 'attachment'}`
        dom.appendChild(a)
      }

      render()

      return {
        dom,
        update: (updatedNode) => {
          if (updatedNode.type.name !== 'attachment') return false
          if (updatedNode.attrs.id !== node.attrs.id || updatedNode.attrs.kind !== node.attrs.kind) {
            node = updatedNode
            render()
            return true
          }
        
          render()
          return true
        },
        ignoreMutation: () => true,
      }
    }
  },
})
