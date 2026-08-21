/**
 * Film Photo Organizer - Global App Coordinator & Keyboard Accelerators
 */

let activeTab = 'organizer';
let lastActiveFolderPath = '';

// Toast Notification Manager
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconMap = {
    success: '<span style="color: var(--accent-emerald); font-weight: 700;">[OK]</span>',
    error: '<span style="color: var(--accent-rose); font-weight: 700;">[ERR]</span>',
    info: '<span style="color: var(--accent-amber); font-weight: 700;">[i]</span>'
  };

  toast.innerHTML = `${iconMap[type] || ''}<div>${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.22s ease';
    setTimeout(() => toast.remove(), 240);
  }, duration);
}

// Tab Switcher
function switchMainTab(tabId) {
  activeTab = tabId;

  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.classList.remove('active');
    tab.setAttribute('aria-selected', 'false');
  });
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  const activeNavBtn = document.getElementById(`tab-btn-${tabId}`);
  const activePane = document.getElementById(`tab-${tabId}`);

  if (activeNavBtn) {
    activeNavBtn.classList.add('active');
    activeNavBtn.setAttribute('aria-selected', 'true');
  }
  if (activePane) {
    activePane.classList.add('active');
  }

  // Trigger preview update or UI refresh if needed
  if (tabId === 'contact') {
    if (window.schedulePreviewUpdate) window.schedulePreviewUpdate(true);
  }
}

// Sub-Tab Switcher (Metadata vs Layout)
function switchSettingsSubTab(subTabId) {
  document.querySelectorAll('.sub-tab').forEach(btn => {
    btn.classList.remove('active');
    btn.setAttribute('aria-selected', 'false');
  });
  document.querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));

  const btn = document.getElementById(`subtab-${subTabId}-btn`);
  const content = document.getElementById(`subtab-${subTabId}`);

  if (btn) {
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');
  }
  if (content) {
    content.classList.add('active');
  }
}

// Reveal Active Folder in Native File Manager
async function revealActiveFolder(customPath) {
  const path = customPath || lastActiveFolderPath || 
               document.getElementById('contact-source-input').value.trim() || 
               document.getElementById('organizer-source-input').value.trim();

  if (!path) {
    showToast("No active folder path specified yet.", "info");
    return;
  }

  try {
    const res = await fetch('/api/system/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    const data = await res.json();
    if (data.success) {
      showToast("Opened folder in file manager.", "success");
    } else {
      showToast(data.error || "Could not open folder.", "error");
    }
  } catch (err) {
    showToast("Failed to contact server.", "error");
  }
}

// Clear All Loaded Photos across Both Tabs
function clearLoadedPhotos() {
  if (window.resetOrganizerState) window.resetOrganizerState();
  if (window.resetContactState) window.resetContactState();
  lastActiveFolderPath = '';
  showToast("Cleared all loaded photos from workspace.", "info");
}

// Confirmation Modal Manager
let confirmedCallback = null;

function showConfirmModal(title, bodyHtml, onConfirm) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  confirmedCallback = onConfirm;
  const modal = document.getElementById('confirm-modal');
  modal.style.display = 'flex';
  const confirmBtn = document.getElementById('modal-confirm-btn');
  if (confirmBtn) confirmBtn.focus();
}

function closeConfirmModal() {
  document.getElementById('confirm-modal').style.display = 'none';
  confirmedCallback = null;
}

function executeConfirmedAction() {
  if (confirmedCallback) {
    const fn = confirmedCallback;
    closeConfirmModal();
    fn();
  }
}

// Global Keyboard Navigation & Shortcuts
function setupGlobalKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    const target = e.target;
    const isEditingText = target && (
      target.tagName === 'INPUT' || 
      target.tagName === 'TEXTAREA' || 
      target.tagName === 'SELECT'
    );

    // Escape closes modal
    if (e.key === 'Escape') {
      const modal = document.getElementById('confirm-modal');
      if (modal && modal.style.display !== 'none') {
        e.preventDefault();
        closeConfirmModal();
        return;
      }
    }

    // Ctrl+1 / Cmd+1 -> Switch to Photo Organizer
    if ((e.ctrlKey || e.metaKey) && (e.key === '1' || e.code === 'Digit1')) {
      e.preventDefault();
      switchMainTab('organizer');
      return;
    }

    // Ctrl+2 / Cmd+2 -> Switch to Contact Sheet Generator
    if ((e.ctrlKey || e.metaKey) && (e.key === '2' || e.code === 'Digit2')) {
      e.preventDefault();
      switchMainTab('contact');
      return;
    }

    // Ctrl+Enter / Cmd+Enter -> Execute Primary Action
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (activeTab === 'organizer') {
        const btn = document.getElementById('process-organizer-btn');
        if (btn && !btn.disabled) btn.click();
      } else if (activeTab === 'contact') {
        const btn = document.getElementById('generate-contact-btn');
        if (btn && !btn.disabled) btn.click();
      }
      return;
    }

    // Non-text-editing shortcuts
    if (!isEditingText) {
      // Arrow navigation in Organizer Table
      if (activeTab === 'organizer' && window.organizerMatchedFiles && window.organizerMatchedFiles.length > 0) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault();
          const files = window.organizerMatchedFiles;
          const currentIdx = files.indexOf(window.organizerSelectedFile);
          let newIdx = 0;
          if (e.key === 'ArrowDown') {
            newIdx = currentIdx < files.length - 1 ? currentIdx + 1 : 0;
          } else {
            newIdx = currentIdx > 0 ? currentIdx - 1 : files.length - 1;
          }
          if (window.selectOrganizerRow) {
            window.selectOrganizerRow(files[newIdx]);
            const selectedRow = document.querySelector('#organizer-tbody tr.selected');
            if (selectedRow) selectedRow.scrollIntoView({ block: 'nearest' });
          }
          return;
        }
      }

      // Preview Zoom Shortcuts
      if (activeTab === 'contact' && window.zoomPreview) {
        if (e.key === '+' || e.key === '=') {
          e.preventDefault();
          window.zoomPreview(0.15);
        } else if (e.key === '-' || e.key === '_') {
          e.preventDefault();
          window.zoomPreview(-0.15);
        } else if (e.key === '0') {
          e.preventDefault();
          if (window.resetPreviewZoom) window.resetPreviewZoom();
        }
      }
    }
  });
}

// Universal Drag & Drop File Resolution
async function processDataTransferItems(dataTransfer) {
  try {
    const textDrop = (dataTransfer.getData('text/plain') || dataTransfer.getData('text/uri-list') || '').trim();
    if (textDrop) {
      const res = await fetch('/api/resolve-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: textDrop })
      });
      const data = await res.json();
      if (data.valid && data.path) {
        return { folderPath: data.path, count: 0, isLocalPath: true };
      }
    }
  } catch (e) {
    console.warn('Text drop path check failed:', e);
  }

  const items = dataTransfer.items;
  const filesList = [];
  let detectedFolderName = '';

  if (items && items.length > 0) {
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
        if (entry) {
          if (entry.isDirectory && !detectedFolderName) {
            detectedFolderName = entry.name;
          }
          await traverseFileEntry(entry, '', filesList);
        } else {
          const file = item.getAsFile();
          if (file) filesList.push({ file, path: file.name });
        }
      }
    }
  } else if (dataTransfer.files && dataTransfer.files.length > 0) {
    for (let i = 0; i < dataTransfer.files.length; i++) {
      const file = dataTransfer.files[i];
      filesList.push({ file, path: file.name });
    }
  }

  if (filesList.length === 0) {
    return null;
  }

  // Check if native file.path is available (e.g. Electron / desktop webview)
  if (filesList[0].file && filesList[0].file.path) {
    const p = filesList[0].file.path;
    const parentDir = p.replace(/[/\\][^/\\]+$/, '');
    if (parentDir) {
      return { folderPath: parentDir, count: filesList.length, isLocalPath: true };
    }
  }

  // Auto-locate the real original folder on local disk (e.g. in Downloads, Pictures, Desktop)
  if (detectedFolderName) {
    try {
      const sampleNames = filesList.slice(0, 10).map(f => f.file.name);
      const res = await fetch('/api/locate-dropped-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder_name: detectedFolderName,
          filenames: sampleNames
        })
      });
      const data = await res.json();
      if (data && data.found && data.path) {
        return {
          folderPath: data.path,
          count: filesList.length,
          isLocalPath: true
        };
      }
    } catch (e) {
      console.warn("Folder auto-locate error:", e);
    }
  }

  // Fallback: upload dropped files to staging directory
  showToast(`Staging ${filesList.length} dropped photo(s)...`, 'info', 2000);
  const uploadRes = await uploadDroppedFilesBatch(filesList, detectedFolderName || 'dropped_roll');
  if (uploadRes && uploadRes.success && uploadRes.folder_path) {
    return {
      folderPath: uploadRes.folder_path,
      count: uploadRes.count,
      files: uploadRes.files,
      isLocalPath: false
    };
  }

  return null;
}

async function traverseFileEntry(entry, currentPath, result) {
  const validExtensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif', '.webp', '.dng'];
  if (entry.isFile) {
    const file = await new Promise((resolve) => entry.file(resolve));
    if (validExtensions.some(ext => file.name.toLowerCase().endsWith(ext))) {
      result.push({ file, path: currentPath ? `${currentPath}/${file.name}` : file.name });
    }
  } else if (entry.isDirectory) {
    const dirReader = entry.createReader();
    const entries = await readAllDirectoryEntries(dirReader);
    for (const child of entries) {
      await traverseFileEntry(child, currentPath ? `${currentPath}/${entry.name}` : entry.name, result);
    }
  }
}

function readAllDirectoryEntries(dirReader) {
  return new Promise((resolve) => {
    const allEntries = [];
    const read = () => {
      dirReader.readEntries((entries) => {
        if (!entries || entries.length === 0) {
          resolve(allEntries);
        } else {
          allEntries.push(...entries);
          read();
        }
      }, () => resolve(allEntries));
    };
    read();
  });
}

async function uploadDroppedFilesBatch(filesList, folderName) {
  const payloadFiles = [];
  for (const item of filesList) {
    const b64 = await readFileAsBase64String(item.file);
    payloadFiles.push({
      name: item.file.name,
      data: b64
    });
  }

  const res = await fetch('/api/upload-dropped', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      folder_name: folderName || 'dropped_roll',
      files: payloadFiles
    })
  });
  return await res.json();
}

function readFileAsBase64String(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// URL Params & Initialization
document.addEventListener('DOMContentLoaded', () => {
  document.documentElement.setAttribute('data-theme', 'dark');
  setupGlobalKeyboardShortcuts();

  // Check URL query parameters for auto-load
  const urlParams = new URLSearchParams(window.location.search);
  const initialPath = urlParams.get('path');
  if (initialPath) {
    if (window.loadContactFolder) window.loadContactFolder(initialPath);
    if (window.loadOrganizerFolder) window.loadOrganizerFolder(initialPath);
  }
});
