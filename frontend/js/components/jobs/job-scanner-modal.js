/**
 * Job Hunter Platform — Multi-Depth Job Scanner Modal Component
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, escapeHtml } from '../../utils/dom.js';
import { showToast } from '../common/toast.js';
import { openAuthModal } from '../common/auth-modal.js';

export function openScanJobsModal() {
  if (!state.currentUser) {
    showToast('Tính năng Quét tin tuyển dụng yêu cầu tài khoản Quản trị viên (Superuser)!', 'warning');
    openAuthModal('login');
    return;
  }
  if (!state.currentUser.is_superuser) {
    showToast('Bạn đang đăng nhập tài khoản Ứng viên. Tác vụ Quét tin chỉ dành riêng cho Quản trị viên (Superuser)!', 'warning');
    return;
  }

  const modal = document.getElementById('scan-jobs-modal');
  if (!modal) return;
  modal.classList.add('active');

  const progressBox = document.getElementById('scan-progress-box');
  const resultBox = document.getElementById('scan-result-box');
  const btnStart = document.getElementById('btn-start-scan');

  if (progressBox) progressBox.style.display = 'none';
  if (resultBox) {
    resultBox.style.display = 'none';
    resultBox.innerHTML = '';
  }
  if (btnStart) {
    btnStart.disabled = false;
    btnStart.innerHTML = '<i data-lucide="play" class="icon-sm"></i><span>Bắt đầu Quét dữ liệu</span>';
  }
  refreshIcons();
}

export function closeScanJobsModal() {
  const modal = document.getElementById('scan-jobs-modal');
  if (modal) modal.classList.remove('active');
}

export function toggleCustomLimitInput(isCustom) {
  const container = document.getElementById('custom-limit-container');
  if (container) {
    container.style.display = isCustom ? 'block' : 'none';
  }
}

export async function startConfiguredJobScan() {
  const selectedRadio = document.querySelector('input[name="scan-depth-mode"]:checked');
  let limit = 20;

  if (selectedRadio) {
    if (selectedRadio.value === 'custom') {
      const customInput = document.getElementById('custom-scan-limit');
      limit = parseInt(customInput?.value, 10) || 50;
      if (limit < 1) limit = 1;
      if (limit > 500) limit = 500;
    } else {
      limit = parseInt(selectedRadio.value, 10) || 20;
    }
  }

  const btnStart = document.getElementById('btn-start-scan');
  const progressBox = document.getElementById('scan-progress-box');
  const progressStatus = document.getElementById('scan-progress-status');
  const progressDetail = document.getElementById('scan-progress-detail');
  const resultBox = document.getElementById('scan-result-box');

  if (btnStart) {
    btnStart.disabled = true;
    btnStart.innerHTML = '<div class="spinner"></div><span>Đang quét dữ liệu...</span>';
  }
  if (progressBox) progressBox.style.display = 'block';
  if (resultBox) resultBox.style.display = 'none';

  if (progressStatus) {
    progressStatus.textContent = `Đang quét dữ liệu (Giới hạn: ${limit} tin/nguồn)...`;
  }
  if (progressDetail) {
    progressDetail.textContent = 'Hệ thống đang duyệt song song ITViec, TopCV, CareerLink, Remotive và tính toán điểm tương thích...';
  }

  const startTime = Date.now();
  showToast(`Đang bắt đầu quét dữ liệu đa nguồn (${limit} tin/nguồn)...`, 'info');

  try {
    const summary = await api.triggerDailyBatch(limit);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    if (progressBox) progressBox.style.display = 'none';
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.innerHTML = '<i data-lucide="refresh-cw" class="icon-sm"></i><span>Quét lại</span>';
    }

    if (resultBox) {
      resultBox.style.display = 'block';
      const createdCount = summary.new_jobs_created ?? summary.ingestion?.created ?? 0;
      const totalFetched = summary.total_fetched ?? summary.ingestion?.total_fetched ?? 0;
      const totalScored = summary.total_matches_evaluated ?? summary.matching?.total_scored ?? 0;
      const strongCount = summary.strong_matches_count ?? 0;
      const goodCount = summary.good_matches_count ?? 0;

      resultBox.innerHTML = `
        <div style="background: var(--bg-muted); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 1.15rem;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
            <strong style="color: var(--success-700); font-size: 0.95rem; display: flex; align-items: center; gap: 0.4rem;">
              <i data-lucide="check-circle-2" class="icon-sm"></i>
              <span>Quét hoàn tất thành công</span>
            </strong>
            <span style="font-size: 0.78rem; color: var(--text-muted);">Thời gian: ${elapsed}s</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.65rem; margin-bottom: 0.85rem;">
            <div style="background: var(--bg-surface); padding: 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-default); text-align: center;">
              <div style="font-size: 1.25rem; font-weight: 700; color: var(--primary-700);">${totalFetched}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">Tin đã thu thập</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-default); text-align: center;">
              <div style="font-size: 1.25rem; font-weight: 700; color: var(--success-700);">${createdCount}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">Tin mới vào DB</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-default); text-align: center;">
              <div style="font-size: 1.25rem; font-weight: 700; color: var(--warning-700);">${totalScored}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">Đã tính 7 chỉ số</div>
            </div>
          </div>

          <div style="font-size: 0.82rem; color: var(--text-body); margin-bottom: 0.75rem;">
            Phát hiện <strong>${strongCount}</strong> tin rất phù hợp và <strong>${goodCount}</strong> tin tiềm năng.
          </div>

          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-primary btn-sm" style="flex: 1;" onclick="closeScanJobsModal(); navigateTo('jobs');">
              <i data-lucide="briefcase" class="icon-sm"></i>
              <span>Xem danh sách việc làm</span>
            </button>
            <button class="btn btn-outline btn-sm" onclick="closeScanJobsModal(); if (typeof window.loadDashboard === 'function') window.loadDashboard();">
              <span>Xem Dashboard</span>
            </button>
          </div>
        </div>
      `;
    }

    showToast(`Quét hoàn tất: ${summary.new_jobs_created || 0} tin mới, ${summary.total_matches_evaluated || 0} tin đã tính điểm!`, 'success');
    if (typeof window.loadDashboard === 'function') {
      window.loadDashboard();
    }
    refreshIcons();
  } catch (err) {
    if (progressBox) progressBox.style.display = 'none';
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.innerHTML = '<i data-lucide="refresh-cw" class="icon-sm"></i><span>Thử lại</span>';
    }
    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="background: var(--danger-50); border: 1px solid var(--danger-100); border-radius: var(--radius-md); padding: 0.85rem; color: var(--danger-700); font-size: 0.85rem;">
          <strong>Lỗi quét dữ liệu:</strong> ${escapeHtml(err.message)}
        </div>
      `;
    }
    showToast(`Lỗi chạy quét dữ liệu: ${err.message}`, 'error');
    refreshIcons();
  }
}
