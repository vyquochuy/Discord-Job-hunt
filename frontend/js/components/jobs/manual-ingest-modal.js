/**
 * Job Hunter Platform — Manual Job Description Ingestion Modal Component
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, escapeHtml } from '../../utils/dom.js';
import { showToast } from '../common/toast.js';
import { openAuthModal } from '../common/auth-modal.js';

let currentManualIngestMode = 'text';

export function openManualIngestModal() {
  if (!state.currentUser) {
    showToast('Vui lòng đăng nhập để nạp mô tả công việc (JD) thủ công!', 'warning');
    openAuthModal('login');
    return;
  }

  const modal = document.getElementById('manual-ingest-modal');
  if (!modal) return;

  const textInput = document.getElementById('manual-raw-text');
  const urlInput = document.getElementById('manual-url-input');
  const resultBox = document.getElementById('manual-ingest-result');

  if (textInput) textInput.value = '';
  if (urlInput) urlInput.value = '';
  if (resultBox) {
    resultBox.style.display = 'none';
    resultBox.innerHTML = '';
  }

  switchManualIngestTab('text');
  modal.classList.add('active');
  refreshIcons();
}

export function closeManualIngestModal() {
  const modal = document.getElementById('manual-ingest-modal');
  if (modal) modal.classList.remove('active');
}

export function switchManualIngestTab(mode) {
  currentManualIngestMode = mode;
  const btnText = document.getElementById('tab-btn-text');
  const btnUrl = document.getElementById('tab-btn-url');
  const contentText = document.getElementById('tab-content-text');
  const contentUrl = document.getElementById('tab-content-url');

  if (mode === 'text') {
    if (btnText) btnText.classList.add('active');
    if (btnUrl) btnUrl.classList.remove('active');
    if (contentText) contentText.classList.add('active');
    if (contentUrl) contentUrl.classList.remove('active');
  } else {
    if (btnText) btnText.classList.remove('active');
    if (btnUrl) btnUrl.classList.add('active');
    if (contentText) contentText.classList.remove('active');
    if (contentUrl) contentUrl.classList.add('active');
  }
}

export async function submitManualJobIngest() {
  const btnSubmit = document.getElementById('btn-submit-manual-ingest');
  const resultBox = document.getElementById('manual-ingest-result');
  const autoMatch = document.getElementById('manual-auto-match')?.checked ?? true;

  let rawText = '';
  let url = '';

  if (currentManualIngestMode === 'text') {
    rawText = document.getElementById('manual-raw-text')?.value?.trim() || '';
    if (rawText.length < 30) {
      showToast('Nội dung JD quá ngắn (cần tối thiểu 30 ký tự để trích xuất).', 'warning');
      return;
    }
  } else {
    url = document.getElementById('manual-url-input')?.value?.trim() || '';
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      showToast('Đường dẫn URL không hợp lệ (cần bắt đầu bằng http:// hoặc https://).', 'warning');
      return;
    }
  }

  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<div class="spinner"></div><span>Đang trích xuất & phân tích...</span>';
  }

  if (resultBox) {
    resultBox.style.display = 'block';
    resultBox.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; color: var(--text-muted);">
        <div class="spinner spinner-primary" style="margin-bottom: 0.5rem;"></div>
        <div>Đang phân tích cấu trúc bài đăng, trích xuất kỹ năng và tính điểm tương thích...</div>
      </div>
    `;
  }

  try {
    const payload = {
      mode: currentManualIngestMode,
      raw_text: currentManualIngestMode === 'text' ? rawText : null,
      url: currentManualIngestMode === 'url' ? url : null,
      auto_match: autoMatch,
    };

    const response = await api.ingestManualJob(payload);

    if (response.status === 'failed') {
      renderManualIngestError(response);
      showToast(response.message || 'Trích xuất tin thất bại.', 'error');
    } else {
      renderManualIngestSuccess(response);
      showToast(response.message || 'Đã nạp tin tuyển dụng thành công!', 'success');
      if (typeof window.loadJobs === 'function' && state.activeView === 'jobs') window.loadJobs();
      if (typeof window.loadDashboard === 'function' && state.activeView === 'dashboard') window.loadDashboard();
    }
  } catch (err) {
    if (resultBox) {
      resultBox.innerHTML = `
        <div class="card" style="padding: 1rem; background-color: var(--danger-50); border-color: var(--danger-100);">
          <div style="color: var(--danger-700); font-weight: 600; margin-bottom: 0.35rem;">Lỗi khi nạp tin tuyển dụng</div>
          <p style="font-size: 0.84rem; color: var(--text-body);">${escapeHtml(err.message) || 'Đã xảy ra lỗi không xác định.'}</p>
        </div>
      `;
    }
    showToast(`Lỗi: ${err.message}`, 'error');
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<i data-lucide="play" class="icon-sm"></i><span>Phân tích & Nạp JD</span>';
      refreshIcons();
    }
  }
}

function renderManualIngestSuccess(res) {
  const resultBox = document.getElementById('manual-ingest-result');
  if (!resultBox) return;

  const job = res.job;
  const match = res.match;
  const meta = res.extraction_metadata || {};

  const statusBadge = res.status === 'created'
    ? '<span class="badge badge-green">Mới tạo</span>'
    : res.status === 'duplicate'
    ? '<span class="badge badge-amber">Đã tồn tại</span>'
    : '<span class="badge badge-gray">Thiếu trường</span>';

  const confidencePercent = Math.round((meta.overall_confidence || 0) * 100);
  const confidenceColor = confidencePercent >= 75 ? 'var(--success-600)' : confidencePercent >= 50 ? 'var(--warning-600)' : 'var(--danger-600)';

  let checklistHtml = '';
  if (meta.fields && meta.fields.length > 0) {
    checklistHtml = meta.fields.map(f => `
      <div class="field-item ${f.detected ? 'detected' : 'undetected'}">
        <i data-lucide="${f.detected ? 'check' : 'x'}" class="icon-sm" style="width: 12px; height: 12px;"></i>
        <span style="font-weight: 600; text-transform: capitalize;">${escapeHtml(f.field)}</span>
        <span style="font-size: 0.72rem; opacity: 0.75;">(${Math.round((f.confidence || 0) * 100)}%)</span>
      </div>
    `).join('');
  }

  resultBox.innerHTML = `
    <div class="card" style="background: var(--bg-surface); border: 1px solid var(--border-default); padding: 1.15rem;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
        <div>
          ${statusBadge}
          <h4 style="margin: 0.35rem 0 0.1rem 0; font-size: 1.05rem; color: var(--text-main);">${job ? escapeHtml(job.title) : 'Tin tuyển dụng'}</h4>
          <div style="font-size: 0.82rem; color: var(--text-muted);">${job ? escapeHtml(job.company_name) : ''} • ${job?.location || 'Vietnam'}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Độ tin cậy trích xuất</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: ${confidenceColor};">${confidencePercent}%</div>
        </div>
      </div>

      <div class="field-checklist-grid">
        ${checklistHtml}
      </div>

      ${match ? `
        <div style="background: var(--primary-50); border: 1px solid var(--primary-100); border-radius: var(--radius-md); padding: 0.85rem; margin-top: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <strong style="font-size: 0.88rem; color: var(--primary-900);">Điểm tương thích 7 chỉ số:</strong>
            <span style="font-size: 1.1rem; font-weight: 700; color: var(--primary-700);">${Math.round(match.score || 0)}/100</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-body);">${escapeHtml(match.explanation_text || match.explanation || '')}</div>
        </div>
      ` : ''}

      <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; border-top: 1px solid var(--border-default); padding-top: 0.75rem;">
        ${job ? `
          <button class="btn btn-outline btn-sm" onclick="closeManualIngestModal(); openJobDetailModal('${job.id}')">
            <i data-lucide="eye" class="icon-sm"></i>
            <span>Xem chi tiết</span>
          </button>
          <button class="btn btn-primary btn-sm" onclick="closeManualIngestModal(); startResumeTailoring('${job.id}')">
            <i data-lucide="file-text" class="icon-sm"></i>
            <span>tạo thiết kế CV</span>
          </button>
        ` : ''}
      </div>
    </div>
  `;

  refreshIcons();
}

function renderManualIngestError(res) {
  const resultBox = document.getElementById('manual-ingest-result');
  if (!resultBox) return;

  resultBox.innerHTML = `
    <div class="card" style="background-color: var(--danger-50); border-color: var(--danger-100); padding: 1rem;">
      <div style="display: flex; align-items: center; gap: 0.4rem; color: var(--danger-700); font-weight: 600; margin-bottom: 0.35rem;">
        <i data-lucide="alert-circle" class="icon-sm"></i>
        <span>${escapeHtml(res.message || 'Không thể trích xuất tin tuyển dụng.')}</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">
        Hãy thử dán nội dung văn bản đầy đủ hơn (tiêu đề, kỹ năng yêu cầu, mức lương hoặc thông tin liên hệ).
      </div>
    </div>
  `;

  refreshIcons();
}
