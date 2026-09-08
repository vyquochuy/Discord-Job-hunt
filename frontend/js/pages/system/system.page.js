/**
 * System Administration and API Settings Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { showToast } from '../../components/common/toast.js';
import { openAuthModal } from '../../components/common/auth-modal.js';
import { refreshIcons } from '../../utils/dom.js';
import { loadDashboard } from '../dashboard/dashboard.page.js';
import { loadProfile } from '../profile/profile.page.js';

export function loadSystemView() {
  const currentBase = api.getBaseUrl();
  const currentSource = api.getResolutionSource();
  const isAdmin = Boolean(state.currentUser && state.currentUser.is_superuser);

  const bannerContainer = document.getElementById('system-admin-banner-container');
  if (bannerContainer) {
    if (isAdmin) {
      bannerContainer.innerHTML = `
        <div class="card" style="border-left: 4px solid var(--success-600); background: var(--bg-surface); padding: 12px 18px;">
          <div style="display: flex; gap: 12px; align-items: center;">
            <div style="background: rgba(16, 185, 129, 0.15); color: var(--success-600); width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              <i data-lucide="shield-check" class="icon"></i>
            </div>
            <div>
              <div style="font-size: 0.88rem; font-weight: 700; color: var(--success-700);">Đã xác thực quyền Quản trị viên tối cao (Superuser)</div>
              <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 1px;">
                Tài khoản: <strong>${state.currentUser.email || 'Admin'}</strong>. Bạn có toàn quyền cấu hình API Endpoint và thực thi các lệnh dọn dẹp cơ sở dữ liệu.
              </div>
            </div>
          </div>
        </div>
      `;
    } else {
      bannerContainer.innerHTML = `
        <div class="card" style="border-left: 4px solid var(--warning-600); background: var(--bg-surface); padding: 14px 18px;">
          <div style="display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap;">
            <div style="display: flex; gap: 12px; align-items: center;">
              <div style="background: rgba(245, 158, 11, 0.15); color: var(--warning-600); width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <i data-lucide="shield-alert" class="icon"></i>
              </div>
              <div>
                <div style="font-size: 0.88rem; font-weight: 700; color: var(--text-main);">Yêu cầu quyền Quản trị viên (Superuser)</div>
                <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">
                  ${state.currentUser ? 'Tài khoản hiện tại không có quyền Quản trị viên. Toàn bộ tác vụ cấu hình và dọn dẹp hệ thống đã bị khóa.' : 'Bạn chưa đăng nhập. Vui lòng đăng nhập tài khoản Quản trị viên để thực hiện các thao tác hệ thống.'}
                </div>
              </div>
            </div>
            <button class="btn btn-primary btn-sm" onclick="openAuthModal('login', 'system')">
              <i data-lucide="log-in" class="icon-sm"></i>
              <span>${state.currentUser ? 'Đổi tài khoản Admin' : 'Đăng nhập Admin'}</span>
            </button>
          </div>
        </div>
      `;
    }
  }

  const inputEl = document.getElementById('custom-api-base-input');
  if (inputEl) {
    inputEl.value = currentBase;
    inputEl.disabled = !isAdmin;
    inputEl.style.opacity = isAdmin ? '1' : '0.6';
    inputEl.style.cursor = isAdmin ? 'text' : 'not-allowed';
  }

  const sourceBadge = document.getElementById('api-source-badge');
  if (sourceBadge) {
    sourceBadge.textContent = `Nguồn: ${currentSource}`;
  }

  // Khóa/Mở khóa toàn bộ các nút tác vụ Admin
  document.querySelectorAll('.btn-admin-action').forEach(btn => {
    btn.disabled = !isAdmin;
    btn.style.opacity = isAdmin ? '1' : '0.5';
    btn.style.cursor = isAdmin ? 'pointer' : 'not-allowed';
    if (!isAdmin) {
      btn.setAttribute('title', 'Yêu cầu quyền Quản trị viên (Superuser)');
    }
  });

  refreshIcons();
}

export function saveCustomApiEndpoint() {
  if (!state.currentUser || !state.currentUser.is_superuser) {
    showToast('Tác vụ này chỉ cho phép Quản trị viên (Superuser) thực hiện!', 'warning');
    openAuthModal('login', 'system');
    return;
  }

  const inputEl = document.getElementById('custom-api-base-input');
  const val = inputEl ? inputEl.value.trim() : '';

  if (!val) {
    showToast('Vui lòng nhập API URL hợp lệ (hoặc bấm Mặc định để xóa tùy biến).', 'warning');
    return;
  }

  api.setBaseUrl(val);
  showToast(`Đã lưu cấu hình API: ${api.getBaseUrl()}`, 'success');
  loadSystemView();
  testApiConnection();
}

export function resetApiEndpoint() {
  if (!state.currentUser || !state.currentUser.is_superuser) {
    showToast('Tác vụ này chỉ cho phép Quản trị viên (Superuser) thực hiện!', 'warning');
    openAuthModal('login', 'system');
    return;
  }

  api.resetBaseUrl();
  showToast(`Đã khôi phục API Endpoint về cấu hình mặc định: ${api.getBaseUrl()}`, 'info');
  loadSystemView();
  testApiConnection();
}

export function setApiPreset(url) {
  if (!state.currentUser || !state.currentUser.is_superuser) {
    showToast('Tác vụ này chỉ cho phép Quản trị viên (Superuser) thực hiện!', 'warning');
    openAuthModal('login', 'system');
    return;
  }

  const inputEl = document.getElementById('custom-api-base-input');
  if (inputEl) {
    inputEl.value = url;
  }
  saveCustomApiEndpoint();
}

export async function testApiConnection() {
  const statusBadge = document.getElementById('api-health-status-badge');
  const resultBox = document.getElementById('api-health-result');
  const pingBtn = document.getElementById('btn-ping-api');

  if (statusBadge) {
    statusBadge.className = 'badge badge-outline';
    statusBadge.innerHTML = `<i data-lucide="loader" class="icon-spin"></i> Đang ping...`;
  }
  if (pingBtn) {
    pingBtn.disabled = true;
  }
  refreshIcons();

  const health = await api.checkHealth();

  if (pingBtn) {
    pingBtn.disabled = false;
  }

  if (health.healthy) {
    if (statusBadge) {
      statusBadge.className = 'badge badge-green';
      statusBadge.textContent = `Online (${health.latencyMs} ms)`;
    }

    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px;">
          <div><strong style="color: var(--color-text-primary);">Trạng thái API:</strong> <span style="color: var(--color-success); font-weight: 600;">Sẵn sàng (200 OK)</span></div>
          <div><strong style="color: var(--color-text-primary);">Độ trễ (Latency):</strong> <span>${health.latencyMs} ms</span></div>
          <div><strong style="color: var(--color-text-primary);">Dịch vụ:</strong> <span>${health.data?.service || 'job-hunt-backend'}</span></div>
          <div><strong style="color: var(--color-text-primary);">Liveness Probe:</strong> <span style="color: var(--color-success); font-weight: 600;">${health.data?.status || 'ok'}</span></div>
        </div>
      `;
    }
    showToast(`Kết nối Backend thành công (${health.latencyMs} ms)`, 'success');
  } else {
    if (statusBadge) {
      statusBadge.className = 'badge badge-red';
      statusBadge.textContent = `Mất kết nối`;
    }

    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="color: var(--color-danger);">
          <strong>Lỗi kết nối:</strong> ${health.error || 'Không thể liên lạc với máy chủ API.'}
          <div style="margin-top: 6px; font-size: 0.75rem; color: var(--color-text-muted);">
            Vui lòng kiểm tra lại URL API, trạng thái máy chủ Backend (Render/Koyeb/Localhost) hoặc cấu hình CORS.
          </div>
        </div>
      `;
    }
    showToast(`Không thể kết nối Backend: ${health.error}`, 'error');
  }

  refreshIcons();
}

export async function confirmPurgeDatabase(scope, description) {
  if (!state.currentUser) {
    showToast('Tác vụ Quản trị hệ thống yêu cầu tài khoản Quản trị viên (Superuser)!', 'warning');
    openAuthModal('login', 'system');
    return;
  }
  if (!state.currentUser.is_superuser) {
    showToast('Bạn không có quyền Quản trị viên (Superuser) để thực hiện tác vụ xóa dữ liệu này!', 'warning');
    return;
  }

  const promptMessage = `XÁC NHẬN THỰC THI:\n"${description}" (Phạm vi: ${scope})\n\nThao tác này sẽ xóa dữ liệu và không thể hoàn tác. Bạn có chắc chắn muốn tiếp tục?`;
  if (!confirm(promptMessage)) return;

  try {
    showToast(`Đang thực thi xóa dữ liệu phạm vi '${scope}'...`, 'warning');
    const report = await api.purgeDatabase(scope, true);
    showToast(`Thao tác hoàn tất: ${report.message}`, 'success');
    
    if (scope === 'all' || scope === 'jobs_and_tailoring') {
      state.jobs = [];
      state.topRecommendations = [];
      state.selectedResume = null;
      loadDashboard();
      if (scope === 'all') loadProfile();
    } else if (scope === 'tailoring_only') {
      state.selectedResume = null;
      const resumeContainer = document.getElementById('resume-workspace-content');
      if (resumeContainer) {
        resumeContainer.innerHTML = `
          <div class="card empty-state-card">
            <div class="empty-state-icon-box">
              <i data-lucide="trash-2" class="icon-lg"></i>
            </div>
            <h3 class="empty-state-title">Đã dọn dẹp toàn bộ dữ liệu tạo thiết kế</h3>
            <p class="empty-state-text">Bạn có thể chọn công việc trong mục Khám phá việc làm để tạo hồ sơ tạo thiết kế mới.</p>
            <button class="btn btn-primary btn-sm" onclick="navigateTo('jobs')">
              <i data-lucide="search" class="icon-sm"></i>
              <span>Khám phá việc làm</span>
            </button>
          </div>
        `;
        refreshIcons();
      }
    }
  } catch (err) {
    showToast(`Lỗi dọn dẹp Database: ${err.message}`, 'error');
  }
}

export async function confirmResetDemo() {
  if (!state.currentUser) {
    showToast('Tác vụ Quản trị hệ thống yêu cầu tài khoản Quản trị viên (Superuser)!', 'warning');
    openAuthModal('login', 'system');
    return;
  }
  if (!state.currentUser.is_superuser) {
    showToast('Bạn không có quyền Quản trị viên (Superuser) để khôi phục trạng thái mẫu!', 'warning');
    return;
  }

  const promptMessage = `KHÔI PHỤC TRẠNG THÁI MẪU (RESET DEMO):\n\nThao tác này sẽ:\n1. Làm trống toàn bộ dữ liệu hiện tại\n2. Nạp lại Từ điển Canonical Skills (180+ kỹ năng)\n3. Đồng bộ lại Hồ sơ ứng viên từ context.example/\n\nTiếp tục?`;
  if (!confirm(promptMessage)) return;

  try {
    showToast('Đang khôi phục toàn bộ hệ thống về trạng thái mẫu ban đầu...', 'info');
    const res = await api.resetDemo();
    showToast(`Khôi phục thành công: ${res.message}`, 'success');
    loadDashboard();
    loadProfile();
  } catch (err) {
    showToast(`Lỗi reset demo: ${err.message}`, 'error');
  }
}
