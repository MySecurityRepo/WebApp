<script setup>
import { computed, ref, toRefs, nextTick } from 'vue' 
import CommentNode from './CommentNode.vue'
import { EditorContent } from '@tiptap/vue-3'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  editor: { type: Object, default: null },
  editorLoading: { type: Boolean, default: false },
  editorError: { type: String, default: null },
  isFileActive: { type: Boolean, default: false },
  isFocused: { type: Boolean, default: false },
  user: { type: Object, default: null },
  getChildState: { type: Function, default: null },
  replyingId: { type: Number, default: 0},
  isreplying: { type: Boolean, default: false },
})



const { node, depth, editor, editorLoading, editorError, isFileActive, isFocused, user, replyingId, isreplying } = toRefs(props)
const emit = defineEmits(['like', 'dislike', 'toggle-reply', 'file-change', 'reply', 'fetch-children', 'delete-comment'])
const indentPx = computed(() => Math.min(depth.value, 10) * 8)

const showPicker = ref(false)

const childState = computed(() =>
  props.getChildState
    ? props.getChildState(node.value.post_id, node.value.comment_id)
    : null
)

function insertEmoji(event) {
  const emoji = event.detail?.unicode
  if (!emoji) return
  editor.value?.commands.insertContent(emoji)
  showPicker.value = false
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



function goToParent(commentId) {
  
  if (!commentId) return
  const el = document.getElementById(`comment-${commentId}`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
  waitForStablePosition(el, { quiet: 200, timeout: 2000, threshold: 1 })
    .then(() => {
      el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'nearest' });
    });  
}


function onToggle(node) {
  node.showchildren = !node.showchildren
  if (!node.showchildren) return
  
  if ((!node.children || node.children.length === 0) && node.n_replies > 0) emit('fetch-children', node)
}


</script> 


<template>
  
  <div class="comment-node"> 
    <div class="flex-grow-1 "> 
      <div class="comment-row" :id="`comment-${node.comment_id}`" :style="{ marginLeft: indentPx + 'px' }">
        <div class="label-comment me-1"  >
          <RouterLink :to="`/user/${node.author_id}`" class="comment-author text-warning text-decoration-none fw-semibold" >{{ node.author_username }}></RouterLink>
          <span v-if="node.parent_username" type="button" class=" parent-mention btn-link p-0 m-0 fw-semibold" @click="goToParent(node.parent_id)">@{{ node.parent_username }}</span>:
        </div>   
        <div class="body enhanced-comment" v-html="node.enhancedBody"></div> 
      </div>
      
      <div class="margin-comment-buttons align-items-center" :style="{ marginLeft: indentPx + 'px' }">
        <button class="btn-like-comments border-0 bg-transparent" :disabled="node.isliking || node.isdisliking || !user || node.author_id === user.id" @click="emit('like', node)" :aria-pressed="node.is_liked ? 'true' : 'false'">
          <i class="bi p-0 m-0 i-comment-buttons" :class="node.is_liked ? 'bi-hand-thumbs-up-fill text-danger' : 'bi-hand-thumbs-up text-danger'"></i>
          <span v-if="Number(node.likes) > 0" class="text-danger comment-numbers"> {{ node.likes }} </span>
        </button> 
        

        <button class="btn-like-comments border-0 bg-transparent" :disabled="node.isliking || node.isdisliking || !user || node.author_id === user.id" @click="emit('dislike', node)" :aria-pressed="node.is_disliked ? 'true' : 'false'">
          <i class="bi p-0 m-0 i-comment-buttons" :class="node.is_disliked ? 'bi-hand-thumbs-down-fill text-danger' : 'bi-hand-thumbs-down text-danger'"></i>
          <span v-if="Number(node.dislikes) > 0" class="text-danger comment-numbers" > {{ node.dislikes }} </span>
        </button> 
        

        <button class="btn-like-comments border-0 bg-transparent" :disabled="!user" @click="emit('toggle-reply', node)">
          <i class="bi bi-chat-dots text-danger p-0 m-0 i-comment-buttons"></i>
          <span v-if="Number(node.n_replies) > 0" class="text-danger comment-numbers"> {{ node.n_replies }} </span>
        </button> 
         
        
        <button v-if="node.n_replies > 0" class="btn-like-comments border-0 bg-transparent" :aria-controls="`replies-${node.comment_id}`" @click="onToggle(node)">
          <i class="bi i-comment-buttons" :class="node.showchildren ? 'bi-dash-circle text-danger' : 'bi-plus-circle text-danger'"></i>
        </button>
        
        <button v-if="user?.id===node.author_id || user?.id===node.post_author_id" class="btn-like-comments border-0 bg-transparent" @click="emit('delete-comment', node)">
          <i class="bi bi-x-circle i-comment-buttons text-danger"></i>
        </button> 
        
      </div>
      
      <div v-if="node.isreplying && (replyingId === node.comment_id)" class="mb-4">
        <div class="w-50 comment-toolbar"> 
          <div class="comment-toolbar bg-dark border border-2 rounded-top xs-limited-width-alert position-relative d-flex align-items-stretch">
            <button class="rounded-top-left btn-like border border-1 bg-dark text-toolbar" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleBold().run()" :class="{ 'btn-active': editor?.isActive('bold') }"><strong>B</strong></button>
            <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleItalic().run()" :class="{ 'btn-active': editor?.isActive('italic') }"><i>I</i></button>
            <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleUnderline().run()" :class="{ 'btn-active': editor?.isActive('underline') }"><u>U</u></button>
            <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleBulletList().run()" :class="{ 'btn-active': editor?.isActive('bulletList') }">•</button>
            <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="editor?.chain().focus().toggleOrderedList().run()" :class="{ 'btn-active': editor?.isActive('orderedList') }">1.</button>
            <button class="btn-like border border-1 bg-dark text-toolbar1" :disabled="!editor || editorLoading" @click="showPicker = !showPicker" :class="{ 'btn-active': showPicker }">💫</button>
            <emoji-picker v-if="showPicker" data-source="/emoji/data.json" @emoji-click="insertEmoji" class="position-absolute z-3 bg-dark border border-2 border-warning rounded p-2" style="top: 100%; left: 0;"> </emoji-picker>
            <input :id="`uploader-${node.comment_id}`" type="file" accept="image/*,video/*,application/pdf" @change="emit('file-change', $event)" aria-hidden="true" style="display: none"/>
            <button type="button" class="btn-like border btn-attch bg-dark text-toolbar1" :class="{'btn-active': isFileActive}" :disabled="!editor || editorLoading">
              <label :for="`uploader-${node.comment_id}`" class="btn-like-label p-2 bg-dark text-secondary">📎</label>
            </button>
          </div> 
        </div>
        <div v-if="editorLoading" class="text-secondary small">{{ t('homevue.loading_editor') }}</div>
        <div v-else-if="editorError" class="text-danger small">{{ editorError }}</div>
        <EditorContent v-else :editor="editor" class="my-editor-comment w-50 xs-limited-width-alert text-center border border-2 p-2 border-focus bg-dark rounded-bottom" :class="{ 'border-warning': isFocused }"/>
        <button class="btn btn-outline-warning fw-bold mt-2 me-1 my-button-dim" :disabled="editorLoading || !editor || editor.isEmpty || isreplying" @click="emit('reply', node)" >{{ t('commentnodevue.reply') }}</button>
        <button class="btn btn-outline-warning fw-bold mt-2 my-button-dim" :disabled="editorLoading || !editor" @click="emit('toggle-reply', node)">{{ t('homevue.cancel') }}</button>
      </div>
      
      <div v-if="node.children?.length && node.showchildren"  :id="`replies-${node.comment_id}`" class="children">
        <CommentNode v-for="child in node.children" :key="child.comment_id" :node="child" :depth="depth + 1" :editor="editor" :editorLoading="editorLoading" :editorError="editorError" :isFocused="isFocused" :isFileActive="isFileActive" :replyingId="replyingId" :isreplying="isreplying" :user="user" :getChildState="getChildState" @like="emit('like', $event)" @dislike="emit('dislike', $event)"  @toggle-reply="emit('toggle-reply', $event)" @file-change="emit('file-change', $event)" @reply="emit('reply', $event)" @fetch-children="emit('fetch-children', $event)" @delete-comment="emit('delete-comment', $event)" />
        
        <div v-if="childState?.hasMore" class="mt-1 mb-3 ms-1" >
          <button  class="border-0 bg-transparent text-danger class-show-comments fw-bold" :disabled="childState?.loading" @click="emit('fetch-children', node)" :aria-controls="`replies-${node.comment_id}`">
            {{ t('homevue.show_more') }}
          </button>
        </div>
      </div>
    </div> 
  </div>
</template> 
