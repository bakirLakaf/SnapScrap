document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  const originalFetch = window.fetch;
  window.fetch = async function () {
    let [resource, config] = arguments;
    if (config && (config.method === 'POST' || config.method === 'PUT' || config.method === 'DELETE')) {
      config.headers = config.headers || {};
      if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;
    }
    return originalFetch.apply(this, arguments);
  };

  const today = new Date().toISOString().slice(0, 10);
  const mergeDateEl = document.getElementById('mergeDate');
  if (mergeDateEl) mergeDateEl.value = today;

  let statusTimeout = null;

  // === Status ===
  async function pollTask(taskId, onDone) {
    const res = await fetch(`/api/task/${taskId}`);
    const data = await res.json();
    const type = data.status === 'done' ? 'done' : data.status === 'error' ? 'error' : 'running';
    showStatus(type, data.message || '');
    if (data.status === 'pending' || data.status === 'running') {
      setTimeout(() => pollTask(taskId, onDone), 1000);
    } else if (data.status === 'done' && onDone) {
      onDone();
    }
  }

  function showStatus(type, msg, autoHide) {
    const section = document.getElementById('statusSection');
    const card = document.getElementById('statusCard');
    section.classList.add('visible');
    card.className = 'status-card ' + type;
    document.getElementById('statusTitle').textContent =
      type === 'done' ? 'تم بنجاح' : type === 'error' ? 'خطأ' : 'جاري المعالجة...';
    document.getElementById('statusMessage').textContent = msg || '';
    if (statusTimeout) clearTimeout(statusTimeout);
    if (type === 'done' && autoHide !== false) {
      statusTimeout = setTimeout(() => section.classList.remove('visible'), 5000);
    }
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    if (loading) btn.classList.add('loading'); else btn.classList.remove('loading');
  }

  // === Accounts ===
  async function addAccount(username) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'add', username }),
    });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
      return;
    }
    renderAccounts(data.accounts);
    document.getElementById('newAccountInput').value = '';
    const bulkInput = document.getElementById('newAccounts');
    if (bulkInput) bulkInput.value = '';
    showStatus('done', `تم إضافة ${username}`);
  }

  async function removeAccount(username) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'remove', username }),
    });
    const data = await res.json();
    if (data.ok) renderAccounts(data.accounts);
  }

  async function toggleAccount(username) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'toggle', username }),
    });
    const data = await res.json();
    if (data.ok) renderAccounts(data.accounts);
  }

  function renderAccounts(accounts) {
    const list = document.getElementById('accountsList');
    if (!list) return;

    const items = accounts.map(a => `
      <label class="account-item-sidebar">
        <input type="checkbox" class="account-check" data-username="${escapeHtml(a.username)}" ${a.checked ? 'checked' : ''}>
        ${a.avatar ? `<img src="${a.avatar}" class="account-avatar" alt="">` : ''}
        <span class="account-name" title="${escapeHtml(a.username)}">${escapeHtml(a.username)}</span>
        <button type="button" class="btn-remove-sm" data-username="${escapeHtml(a.username)}" title="حذف">×</button>
      </label>
    `).join('');

    const emptyHtml = '<p class="empty-accounts" id="emptyAccounts" style="display:none">لا توجد حسابات</p>';
    list.innerHTML = items + emptyHtml;

    const emptyEl = document.getElementById('emptyAccounts');
    if (emptyEl) emptyEl.style.display = accounts.length ? 'none' : 'block';

    list.querySelectorAll('.account-check').forEach(cb => {
      cb.addEventListener('change', () => toggleAccount(cb.dataset.username));
    });
    list.querySelectorAll('.btn-remove-sm').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation(); // Prevent label click
        removeAccount(btn.dataset.username);
      });
    });
  }

  async function setAllChecked(checked) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'set_all_checked', checked }),
    });
    const data = await res.json();
    if (data.ok) renderAccounts(data.accounts);
  }

  document.getElementById('selectAll')?.addEventListener('click', () => setAllChecked(true));
  document.getElementById('deselectAll')?.addEventListener('click', () => setAllChecked(false));

  // Toggle Bulk Add (Reverted to Toggle Link)
  const toggleBulkLink = document.getElementById('toggleBulkAdd');
  const singleInput = document.getElementById('newAccountInput');
  const bulkInput = document.getElementById('newAccounts');
  const addBtn = document.querySelector('#addAccountForm button[type="submit"]');

  if (toggleBulkLink) {
    toggleBulkLink.addEventListener('click', () => {
      if (bulkInput.style.display === 'none') {
        bulkInput.style.display = 'block';
        singleInput.parentElement.style.display = 'none'; // Hide input-row
        if (addBtn) addBtn.textContent = 'إضافة دفعة';
      } else {
        bulkInput.style.display = 'none';
        singleInput.parentElement.style.display = 'flex';
        if (addBtn) addBtn.textContent = 'إضافة';
      }
    });
  }

  // === Suggested accounts ===
  async function loadSuggestedAccounts() {
    const list = document.getElementById('suggestedList');
    if (!list) return;
    try {
      const res = await fetch('/api/suggested-accounts');
      const data = await res.json();
      const accounts = data.accounts || [];
      list.innerHTML = accounts.map(a => `
        <label class="suggested-item">
          <input type="checkbox" class="suggested-check" data-username="${escapeHtml(a.username)}">
          <span>${escapeHtml(a.label || a.username)}</span>
        </label>
      `).join('');
    } catch {
      list.innerHTML = '<span class="empty-accounts">فشل تحميل الحسابات المقترحة</span>';
    }
  }

  // Toggle Suggestions
  const suggestedHeader = document.getElementById('suggestedHeader');
  const suggestedList = document.getElementById('suggestedList');
  const toggleIcon = document.getElementById('suggestedToggleIcon');

  if (suggestedHeader && suggestedList) {
    suggestedHeader.addEventListener('click', (e) => {
      // Prevent toggle if clicking the refresh button
      if (e.target.closest('#refreshSuggested')) return;

      if (suggestedList.style.display === 'none') {
        suggestedList.style.display = 'flex'; // Changed to flex to match CSS
        suggestedHeader.classList.remove('collapsed');
        if (toggleIcon) toggleIcon.style.transform = 'rotate(0deg)';
      } else {
        suggestedList.style.display = 'none';
        suggestedHeader.classList.add('collapsed');
        if (toggleIcon) toggleIcon.style.transform = 'rotate(90deg)';
      }
    });
  }

  loadSuggestedAccounts();

  document.getElementById('refreshSuggested')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshSuggested');
    btn.disabled = true;
    btn.classList.add('loading'); // Use CSS spinner if available or just wait
    await loadSuggestedAccounts();
    btn.disabled = false;
    btn.classList.remove('loading');
    showStatus('done', 'تم تحديث الحسابات المقترحة');
  });

  document.getElementById('addSelectedSuggested')?.addEventListener('click', async () => {
    const checked = [...document.querySelectorAll('.suggested-check:checked')].map(cb => cb.dataset.username);
    if (!checked.length) {
      showStatus('error', 'حدّد حسابات لإضافتها');
      return;
    }
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'add_bulk', usernames: checked }),
    });
    const data = await res.json();
    if (data.ok) {
      renderAccounts(data.accounts);
      const msg = data.added > 0 ? `تم إضافة ${data.added} حساب${data.added > 1 ? 'ات' : ''}` : 'كل المحدد موجود مسبقاً';
      showStatus('done', msg);
      document.querySelectorAll('.suggested-check:checked').forEach(cb => { cb.checked = false; });
    } else {
      showStatus('error', data.error || 'خطأ');
    }
  });

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // Add Account Form Submit
  document.getElementById('addAccountForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const isBulk = bulkInput && bulkInput.style.display !== 'none';
    let usernames = [];

    if (isBulk) {
      const text = bulkInput.value;
      usernames = text.split(/\r?\n|,/).map(s => s.trim().toLowerCase()).filter(Boolean);
    } else {
      const val = singleInput.value.trim().toLowerCase();
      if (val) usernames = [val];
    }

    if (!usernames.length) {
      showStatus('error', 'أدخل اسم مستخدم');
      return;
    }

    const btn = document.getElementById('submitAddBtn') || addBtn;
    setLoading(btn, true);

    try {
      if (usernames.length === 1) {
        await addAccount(usernames[0]);
      } else {
        const res = await fetch('/api/accounts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'add_bulk', usernames }),
        });
        const data = await res.json();
        if (!data.ok) {
          showStatus('error', data.error);
        } else {
          renderAccounts(data.accounts);

          // Clear inputs
          if (bulkInput) bulkInput.value = '';
          if (document.getElementById('newAccountInput')) document.getElementById('newAccountInput').value = '';

          const msg = data.added > 0 ? `تم إضافة ${data.added} حساب` : '';
          const skip = data.skipped?.length ? ` (${data.skipped.length} موجود)` : '';
          showStatus('done', msg + skip || 'تم');
        }
      }
    } catch (err) {
      showStatus('error', 'حدث خطأ غير متوقع');
    } finally {
      setLoading(btn, false);
    }
  });

  document.getElementById('downloadSelected')?.addEventListener('click', async () => {
    const checked = [...document.querySelectorAll('.account-check:checked')].map(cb => cb.dataset.username);
    if (!checked.length) {
      showStatus('error', 'حدّد حسابات لتنزيلها');
      return;
    }
    const btn = document.getElementById('downloadSelected');
    setLoading(btn, true);
    // Use the sidebar checkbox
    const merge = document.getElementById('batchMergeSidebar')?.checked || false;
    const res = await fetch('/api/download-selected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usernames: checked, merge }),
    });
    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري التحميل...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  renderAccounts(window.INIT_ACCOUNTS || []);

  // === Refresh merged folders ===
  async function refreshMergedFolders() {
    const res = await fetch('/api/merged-folders');
    const folders = await res.json();

    // Upload folder select
    const sel = document.getElementById('uploadUsername');
    if (sel) {
      const currentVal = sel.value;
      const opts = '<option value="">اختر المجلد</option><option value="__manual__">أدخل يدوياً</option>' +
        folders.map(f => `<option value="${escapeHtml(f.username)}" data-date="${escapeHtml(f.date)}">${escapeHtml(f.username)} / ${escapeHtml(f.date)}</option>`).join('');
      sel.innerHTML = opts;
      if (currentVal) sel.value = currentVal;
    }

    // Clear folder select
    const clearSel = document.getElementById('clearFolder');
    if (clearSel) {
      clearSel.innerHTML = '<option value="">اختر المجلد</option>' +
        folders.map(f => `<option value="${escapeHtml(f.username)}" data-date="${escapeHtml(f.date)}">${escapeHtml(f.username)} / ${escapeHtml(f.date)}</option>`).join('');
    }

    // TikTok folder select
    const tiktokSel = document.getElementById('tiktokFolder');
    if (tiktokSel) {
      tiktokSel.innerHTML = '<option value="">اختر المجلد</option>' +
        folders.map(f => `<option value="${escapeHtml(f.username)}" data-date="${escapeHtml(f.date)}">${escapeHtml(f.username)} / ${escapeHtml(f.date)}</option>`).join('');
    }
  }

  document.getElementById('refreshMerged')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshMerged');
    btn.disabled = true;
    btn.textContent = '...';
    await refreshMergedFolders();
    // await refreshClearFolders(); // Handled by refreshMergedFolders now
    btn.disabled = false;
    btn.textContent = '↻ مجلدات';
    showStatus('done', 'تم تحديث قائمة المجلدات');
  });

  // === Schedule + next run ===
  function updateNextRun() {
    const el = document.getElementById('nextRun');
    if (!el) return;
    const enabled = document.getElementById('scheduleEnabled')?.checked;
    if (!enabled) {
      el.textContent = '';
      return;
    }
    const h = parseInt(document.getElementById('scheduleHour')?.value) || 9;
    const m = parseInt(document.getElementById('scheduleMinute')?.value) || 0;
    const now = new Date();
    let next = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0);
    if (next <= now) next.setDate(next.getDate() + 1);
    const opts = { hour: '2-digit', minute: '2-digit', weekday: 'short' };
    el.textContent = 'التشغيل التالي: ' + next.toLocaleDateString('ar-SA', opts);
  }

  document.getElementById('scheduleEnabled')?.addEventListener('change', updateNextRun);
  document.getElementById('scheduleHour')?.addEventListener('change', updateNextRun);
  document.getElementById('scheduleMinute')?.addEventListener('change', updateNextRun);
  setTimeout(updateNextRun, 100);

  // === Schedule ===
  document.getElementById('scheduleForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    const res = await fetch('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: document.getElementById('scheduleEnabled').checked,
        hour: parseInt(document.getElementById('scheduleHour').value) || 9,
        minute: parseInt(document.getElementById('scheduleMinute').value) || 0,
        merge: document.getElementById('scheduleMerge').checked,
      }),
    });
    const data = await res.json();
    setLoading(btn, false);
    if (data.ok) {
      showStatus('done', 'تم حفظ الجدولة');
      updateNextRun();
    }
  });

  // === Tabs ===
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      const id = tab.dataset.tab === 'folder' ? 'uploadFolder' : 'uploadFile';
      document.getElementById(id).classList.add('active');
    });
  });

  // === Upload select ===
  const uploadUsername = document.getElementById('uploadUsername');
  const uploadDate = document.getElementById('uploadDate');
  const manualUpload = document.getElementById('manualUpload');
  uploadUsername?.addEventListener('change', () => {
    const opt = uploadUsername.options[uploadUsername.selectedIndex];
    const val = opt?.value || '';
    if (val === '__manual__') {
      manualUpload.style.display = 'flex';
      uploadDate.value = '';
    } else {
      manualUpload.style.display = 'none';
      uploadDate.value = opt?.dataset?.date || '';
    }
  });

  // === File drop ===
  const fileDrop = document.getElementById('fileDrop');
  const videoFile = document.getElementById('videoFile');
  const fileSelectedEl = document.getElementById('fileSelected');
  function updateFileSelected() {
    const f = videoFile?.files[0];
    if (fileSelectedEl) {
      fileSelectedEl.style.display = f ? 'block' : 'none';
      fileSelectedEl.textContent = f ? '✓ ' + f.name : '';
    }
  }
  videoFile?.addEventListener('change', updateFileSelected);
  fileDrop?.addEventListener('click', () => videoFile?.click());
  fileDrop?.addEventListener('dragover', (e) => { e.preventDefault(); fileDrop.classList.add('dragover'); });
  fileDrop?.addEventListener('dragleave', () => fileDrop.classList.remove('dragover'));
  fileDrop?.addEventListener('drop', (e) => {
    e.preventDefault();
    fileDrop.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      videoFile.files = e.dataTransfer.files;
      updateFileSelected();
    }
  });

  // === Download ===
  document.getElementById('downloadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const merge = document.getElementById('mergeAfter')?.checked || false;
    if (!username) {
      showStatus('error', 'أدخل اسم المستخدم');
      return;
    }
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, merge }),
    });
    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري التحميل...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  // === YouTube channels ===
  function populateChannelSelects(channels) {
    const opts = '<option value="">اختر القناة</option>' +
      (channels || []).map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.title)}</option>`).join('');
    const sel1 = document.getElementById('uploadChannel');
    const sel2 = document.getElementById('uploadFileChannel');
    const sel3 = document.getElementById('bulkUploadChannel');

    [sel1, sel2, sel3].forEach(sel => {
      if (sel) {
        const v = sel.value;
        sel.innerHTML = opts;
        if (v) sel.value = v;

        // Auto-select 'Content Creators Stories' for bulk upload by default
        if (sel.id === 'bulkUploadChannel' && !v && channels) {
          const targetChannel = channels.find(c => c.title.toLowerCase().includes("content creators stories") || c.title.toLowerCase().includes("stories"));
          if (targetChannel) {
            sel.value = targetChannel.id;
          }
        }
      }
    });
  }

  async function loadYoutubeChannels() {
    const el = document.getElementById('youtubeChannels');
    try {
      const res = await fetch('/api/youtube/channels');
      const data = await res.json();
      if (data.ok && data.channels?.length) {
        populateChannelSelects(data.channels);
        if (el) el.textContent = 'قناتك: ' + data.channels.map(c => c.title).join('، ');
      } else {
        populateChannelSelects([]);
        if (el) el.textContent = data.error || 'أضف قناة عبر «+ إضافة قناة»';
      }
    } catch {
      populateChannelSelects([]);
      if (el) el.textContent = '';
    }
  }
  loadYoutubeChannels();

  document.getElementById('refreshChannels')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshChannels');
    btn.disabled = true;
    btn.textContent = '...';
    const res = await fetch('/api/youtube/refresh', { method: 'POST' });
    const data = await res.json();
    btn.disabled = false;
    btn.textContent = '↻ قنوات';
    if (data.ok) {
      populateChannelSelects(data.channels);
      showStatus('done', 'تم تحديث القنوات');
    } else {
      showStatus('error', data.error || 'فشل التحديث');
    }
  });

  // URL params: youtube_connected, youtube_error
  const params = new URLSearchParams(location.search);
  if (params.get('youtube_connected')) {
    loadYoutubeChannels();
    showStatus('done', 'تم إضافة القناة بنجاح');
    history.replaceState({}, '', location.pathname);
  }
  if (params.get('youtube_error')) {
    showStatus('error', decodeURIComponent(params.get('youtube_error') || 'خطأ'));
    history.replaceState({}, '', location.pathname);
  }

  // === Merge ===
  document.getElementById('mergeForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('mergeUsername').value.trim();
    const date = (document.getElementById('mergeDate').value || today).trim();
    const mergeMode = document.querySelector('input[name="mergeMode"]:checked')?.value || 'shorts';
    if (!username) {
      showStatus('error', 'أدخل اسم المستخدم');
      return;
    }
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    const res = await fetch('/api/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date, merge_mode: mergeMode }),
    });
    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري الدمج...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  // === Upload folder ===
  document.getElementById('uploadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const sel = uploadUsername.value;
    const username = sel === '__manual__'
      ? document.getElementById('uploadUsernameManual')?.value?.trim()
      : uploadUsername.value.trim();
    const date = (sel === '__manual__'
      ? document.getElementById('uploadDateManual')?.value?.trim()
      : uploadDate.value.trim()) || today;
    const privacy = document.getElementById('uploadPrivacy').value;
    const uploadType = document.getElementById('uploadType')?.value || 'shorts';
    const channelId = document.getElementById('uploadChannel')?.value || null;
    if (!username) {
      showStatus('error', 'اختر مجلداً أو أدخل اسم المستخدم');
      return;
    }
    const res = await fetch('/api/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date, privacy, upload_type: uploadType, channel_id: channelId || undefined }),
    });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري الرفع إلى يوتيوب...');
    pollTask(data.task_id);
  });

  // === Upload file ===
  document.getElementById('uploadFileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = videoFile.files[0];
    if (!file) {
      showStatus('error', 'اختر ملف فيديو');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', document.getElementById('uploadTitle').value.trim() || file.name.replace(/\.[^.]+$/, ''));
    formData.append('privacy', document.getElementById('uploadFilePrivacy').value);
    const channelId = document.getElementById('uploadFileChannel')?.value;
    if (channelId) formData.append('channel_id', channelId);
    const res = await fetch('/api/upload-file', { method: 'POST', body: formData });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري الرفع إلى يوتيوب...');
    pollTask(data.task_id);
  });

  // === Upload all ===
  document.getElementById('uploadAll')?.addEventListener('click', async () => {
    const btn = document.getElementById('uploadAll');
    const res = await fetch('/api/merged-folders');
    const folders = await res.json();
    if (!folders.length) {
      showStatus('error', 'لا توجد مجلدات مدمجة للرفع');
      return;
    }
    const privacy = document.getElementById('uploadPrivacy')?.value || 'private';
    const uploadType = document.getElementById('uploadType')?.value || 'shorts';
    const channelId = document.getElementById('bulkUploadChannel')?.value || null;

    if (!channelId) {
      showStatus('error', 'الرجاء اختيار القناة لرفع الفيديوهات إليها');
      return;
    }

    setLoading(btn, true);
    const postRes = await fetch('/api/upload-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folders, privacy, upload_type: uploadType, channel_id: channelId || undefined }),
    });
    const data = await postRes.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error || 'خطأ');
      return;
    }
    showStatus('running', 'جاري رفع الكل...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  // === Clear batch ===
  document.getElementById('clearBatchBtn')?.addEventListener('click', async () => {
    const sel = document.getElementById('clearFolder');
    const opt = sel?.options[sel.selectedIndex];
    const username = opt?.value;
    const date = opt?.dataset?.date;
    if (!username || !date) {
      showStatus('error', 'اختر مجلداً للمسح');
      return;
    }
    if (!confirm(`حذف ${username}/${date} نهائياً؟`)) return;
    const res = await fetch('/api/clear-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date }),
    });
    const data = await res.json();
    if (data.ok) {
      showStatus('done', data.message);
      refreshMergedFolders();
    } else {
      showStatus('error', data.error);
    }
  });

  // === TikTok Manual Bridge ===
  const tiktokFolder = document.getElementById('tiktokFolder');

  document.getElementById('openFolderBtn')?.addEventListener('click', async () => {
    const opt = tiktokFolder?.options[tiktokFolder.selectedIndex];
    const username = opt?.value;
    const date = opt?.dataset?.date;

    if (!username) {
      showStatus('error', 'اختر مجلداً أولاً');
      return;
    }

    const res = await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date }),
    });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
    }
  });

  document.getElementById('copyCaptionBtn')?.addEventListener('click', () => {
    const opt = tiktokFolder?.options[tiktokFolder.selectedIndex];
    const username = opt?.value;

    if (!username) {
      showStatus('error', 'اختر مجلداً أولاً');
      return;
    }

    // Basic caption template
    const caption = `Snapchat Story from ${username} #snapchat #story #fyp #viral`;
    navigator.clipboard.writeText(caption).then(() => {
      showStatus('done', 'تم نسخ العنوان!');
    }).catch(() => {
      showStatus('error', 'فشل النسخ');
    });
  });
});
