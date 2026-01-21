import Swal from 'sweetalert2'
import api from '@/lib/api'
import { useI18n } from 'vue-i18n'
import { i18n } from '@/i18n'
import { useChatStore } from '@/stores/chat'

 function translateKey(key) {
  return i18n.global.t(key)
}

function debounce(fn, ms=250) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms) }
}


export async function openSearchDialog() {

  let selected = null
  const { value } = await Swal.fire({
    title: translateKey('appvue.search'),
    iconHtml: '<i class="bi bi-search"></i>',
    html: `
      <div class="swal-search">
        <div class="mb-2" style="text-align:center">
          <input class="form-check-input" type="radio" name="kind" value="posts" checked> <label class="search-label me-3">${translateKey('userprofilevue.posts')}</label>
          <input class="form-check-input" type="radio" name="kind" value="users"> <label class="search-label">${translateKey('userprofilevue.users')}</label>
        </div>
          <input id="swal-search-input" class="swal2-input border-focus-always rounded background-swal search-input"  placeholder="${translateKey('userprofilevue.type_to_search')}" autocomplete="off">
          <div id="swal-results" class="swal-results" style="max-height:240px; overflow:auto; text-align:left"></div>
      </div>
    `,
    background: '#111',
    color: '#FFC107',
    iconColor: '#FF9800',
    showCancelButton: true,
    confirmButtonText: translateKey('appvue.search'),
    cancelButtonText: translateKey('homevue.cancel'),
    customClass: {
      popup: 'swal2-dark-popup-yellow',
      icon: 'my-swal-icon-yellow',
      confirmButton: 'my-swal-btn-yellow',
      cancelButton: 'my-swal-btn-yellow'
    },
    buttonsStyling: false,
    
    didOpen: () => {
      const $ = (sel) => Swal.getHtmlContainer().querySelector(sel)
      const input = $('#swal-search-input')
      const resultsEl = $('#swal-results')
      const kindEls = Swal.getHtmlContainer().querySelectorAll('input[name="kind"]')

      const render = (items, kind, query) => {
        if (!query) { resultsEl.innerHTML = ''; return }
        const message = kind === 'posts' ? translateKey('searchjs.no_posts_found') : kind === 'users' ? translateKey('searchjs.no_users_found') : translateKey('searchjs.no_results_found')
        if (!items.length) { resultsEl.innerHTML = `<div class=" p-2">${message}</div>`; return }
        resultsEl.innerHTML = items.map(it => {
          if (kind === 'posts') {
            return `<button data-kind="posts" data-id="${it.post_id}" data-slug="${it.slug}" class="swal-result btn btn-sm btn-outline-warning w-100 text-start mb-1">
              <div class="fw-bold">${escapeHtml(it.title || '(untitled)')}</div>
              <div class="small ">${escapeHtml(it.author_username || '')}</div>
            </button>`
          } else {
            return `<button data-kind="users" data-id="${it.id}" class="swal-result btn btn-sm btn-outline-warning w-100 text-start mb-1">
              <div class="fw-bold">${escapeHtml(it.username || '')}</div>
            </button>`
          }
        }).join('')
      }
      
      const fetchAndRender = debounce(async () => {
        const query = input.value.trim()
        if (query.length < 2) { resultsEl.innerHTML = ''; return }
        const kind = [...kindEls].find(r => r.checked)?.value || 'posts'
        if (!query) { resultsEl.innerHTML = ''; return }
        try {
          resultsEl.innerHTML = `<div class="p-2">${translateKey('searchjs.searching')}</div>`
          const url = kind === 'posts' ? '/search/posts' : '/search/users'
          const { data } = await api.get(url, { params: { query, limit: 10 } })
          render(data.items || [], kind, query)
        } catch {
          resultsEl.innerHTML = `<div class="p-2 text-danger">${translateKey('userprofilevue.search_failed')}</div>`
        }
      }, 250)

      input.addEventListener('input', fetchAndRender)
      kindEls.forEach(el => el.addEventListener('change', fetchAndRender))

      resultsEl.addEventListener('click', (e) => {
        const btn = e.target.closest('.swal-result')
        if (!btn) return
        const kind = btn.dataset.kind
        if (kind === 'posts') {
          selected = { kind, post_id: Number(btn.dataset.id), slug: btn.dataset.slug }
        } else {
          selected = { kind, id: Number(btn.dataset.id) }
        }
        Swal.clickConfirm()
      })

      setTimeout(() => input.focus(), 0)

      function escapeHtml(s='') {
        return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
      }
      
    },
    
    preConfirm: () => {
      if (selected) return selected
      const html = Swal.getHtmlContainer()
      const query = html.querySelector('#swal-search-input')?.value?.trim() || ''
      const kind = html.querySelector('input[name="kind"]:checked')?.value || 'posts'
      
      
      return { kind, query: query}
    }
  })

  return value
}




export async function openSearchUsersToAdd({ target, userId } = {}) {
  const selected = new Map();
  let lastResults = [];

  const { value, isConfirmed } = await Swal.fire({
    target, 
    heightAuto: false, 
    title: translateKey('searchjs.add_users'),
    iconHtml: '<i class="bi bi-search"></i>',
    html: `
      <div class="swal-search">
        <input id="swal-search-input" class="swal2-input border-focus-always rounded background-swal search-input" placeholder='${translateKey('searchjs.search_user')}' autocomplete="off"">
        
        <div class="d-flex mt-3 mb-2 align-items-center" style="text-align:left">
          <div class="me-2 text-warning search-label">${translateKey('searchjs.selected')}:</div>
          <div id="swal-selected" class="d-flex flex-wrap gap-1 text-warning search-label" style="flex: 1;"></div>
        </div>

        <div class="d-flex align-items-center" style="text-align:left">
          <div class="text-warning search-label">${translateKey('searchjs.results')}:</div>
          <div id="swal-results" class="swal-results list-group search-label" style="max-height:240px; overflow:auto; text-align:left"></div>
        </div> 
      </div>`,
    background: '#111',
    color: '#FFC107',
    iconColor: '#FF9800',
    showCancelButton: true,
    allowOutsideClick: false,
    allowEscapeKey: false,
    confirmButtonText: translateKey('appvue.ok'),
    cancelButtonText: translateKey('homevue.cancel'),
    customClass: {
      popup: 'swal2-dark-popup-yellow',
      icon: 'my-swal-icon-yellow',
      confirmButton: 'my-swal-btn-yellow',
      cancelButton: 'my-swal-btn-yellow'
    },
    buttonsStyling: false,

    didOpen: () => {
      const $ = (sel) => Swal.getHtmlContainer().querySelector(sel);
      const input = $('#swal-search-input');
      const resultsEl = $('#swal-results');
      const selectedEl = $('#swal-selected');

      const escapeHtml = (s='') =>
        s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

      const renderSelected = () => {
        selectedEl.innerHTML = '';
        if (!selected.size) {
          selectedEl.innerHTML = `<div class="text-warning ms-2">${translateKey('searchjs.no_users_selected')}</div>`;
          return;
        }
        for (const u of selected.values()) {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'btn btn-sm btn-outline-warning me-2';
          btn.textContent = `${u.username} ✕`;
          btn.onclick = () => { selected.delete(u.id); renderSelected(); renderResults(lastResults); };
          selectedEl.appendChild(btn);
        }
      };

      const renderResults = (items) => {
        const chat = useChatStore()
        const activeThread = chat.threads.find(x => x.id === chat.activeThreadId)
        const participants = activeThread?.participants || []
        lastResults = items.filter( i => !participants.includes(i.username))
        if (!lastResults.length) {
          resultsEl.innerHTML = `<div class=" p-2">${translateKey('searchjs.no_users_found')}</div>`;
          return;
        }
        resultsEl.innerHTML = lastResults.map((it) => {
          const isSel = selected.has(it.id);
          return `
            <button data-id="${it.id}" class="btn btn-outline-warning d-flex flex-wrap align-items-center mb-1 px-0 w-100">
              <span class="badge bg-warning text-dark users_button ms-1 me-1 px-1 py-1">${isSel ? '-' : '+'}</span>
              <span class="fw-bold users_button px-1">${escapeHtml(it.username || '')}</span>        
            </button>
            `;
          }).join('');
        };

      const fetchAndRender = debounce(async () => {
        const q = (input.value || '').trim();
        if (q.length < 2) { resultsEl.innerHTML = ''; return; }
        try {
          resultsEl.innerHTML = `<div class="p-2 text-warning">${translateKey('searchjs.searching')}</div>`;
          const url = '/search/users';
          const { data } = await api.get(url, { params: { query: q, limit: 10 } });
          renderResults(data.items || []);
        } catch (err) {
          resultsEl.innerHTML = `<div class="p-2 text-danger">${translateKey('searchjs.search_failed')}</div>`;
        }
      }, 250);

      resultsEl.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-id]');
        if (!btn) return;
        const id = Number(btn.dataset.id);
        const item = lastResults.find(u => u.id === id);
        if (!item) return;

        if (selected.has(id)) selected.delete(id);
        else selected.set(id, { id: item.id, username: item.username });

        renderSelected();
        renderResults(lastResults);
        
        input.value = '';
        resultsEl.innerHTML = '';
        input.focus();

      });

      input.addEventListener('input', fetchAndRender);
      setTimeout(() => input.focus(), 0);

      resultsEl.innerHTML = '';
      renderSelected();
    },

    preConfirm: async () => {
      if (!selected.size) {
        Swal.showValidationMessage('Select at least one user.');
        return false;
      }
      const picked = Array.from(selected.values());

      const confirm = await Swal.fire({
        title: translateKey('searchjs.confirm_add_users'),
        html: `
          <div class="mb-2">${translateKey('searchjs.message_add_user1')}</div>
          <div>${picked.map(u => `<span class="badge bg-warning text-dark me-2 mb-2">${u.username}</span>`).join('')}</div>
          <div class="mt-2 text-warning">${translateKey('searchjs.message_add_user2')}</div>
        `,
        iconHtml: '<i class="bi bi-person-plus"></i> ',
        showCancelButton: true,
        allowOutsideClick: false,
        allowEscapeKey: false,
        confirmButtonText: translateKey('searchjs.add_users'),
        cancelButtonText: translateKey('userprofilevue.back'),
        background: '#111',
        iconColor: '#FF9800',
        color: '#FFC107',
        buttonsStyling: false,
        customClass: {
          popup: 'swal2-dark-popup-yellow',
          confirmButton: 'my-swal-btn-yellow',
          cancelButton: 'my-swal-btn-yellow',
          icon: 'my-swal-icon-yellow',
        }
      });

      if (!confirm.isConfirmed) {
        const preventHide = (e) => e.preventDefault()
        target.removeEventListener('hide.bs.offcanvas', preventHide)
        return false;
        
      }

      return picked;
    }
  });

  if (!isConfirmed) return null;
  return value;
}
