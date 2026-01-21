import { Node } from '@tiptap/core'

export const Video = Node.create({
  name: 'video',

  group: 'block',

  selectable: true,

  draggable: true,

  atom: false,

  addAttributes() {
    return {
      src: {
        default: null,
      },
    }
  },

   parseHTML() {
    return [{ tag: 'video[src]' }]
  },
  

  renderHTML({ HTMLAttributes }) {
    return ['video', { ...HTMLAttributes, controls: true }]
  },

  addNodeView() {
    return ({ node }) => {
      const video = document.createElement('video')
      video.controls = true
      video.src = node.attrs.src
      video.style.maxWidth = '100%'
      video.style.display = 'block'
      video.style.margin = '1rem auto'
      
      return {dom: video}
    }
  },
})
