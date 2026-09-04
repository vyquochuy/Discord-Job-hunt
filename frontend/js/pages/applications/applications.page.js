/**
 * Applications Tracking Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { showToast } from '../../components/common/toast.js';
import { openAuthModal } from '../../components/common/auth-modal.js';
import { refreshIcons } from '../../utils/dom.js';
import { formatDate } from '../../utils/formatters.js';

export async function loadApplications() {
  const container = document.getElementById('applications-table-body');
  if (!container) return;

  if (!state.currentUser) {
    container.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 3rem 1.5rem;">
          <div style="max-width: 420px; margin: 0 auto;">
            <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.35rem; color: var(--text-main);">Yêu cầu Đăng nhập</div>
            <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 1rem;">Đăng nhập để theo dõi trạng thái, nhật ký gửi thư và quản lý danh sách các công việc bạn đã nộp đơn.</div>
            <button class="btn btn-primary btn-sm" onclick="openAuthModal('login', 'applications')">
              <i data-lucide="log-in" class="icon-sm"></i>
              <span>Đăng nhập ngay</span>
            </button>
          </div>
        </td>
      </tr>
    `;
    refreshIcons();
    return;
  }

  container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">Đang tải danh sách đơn ứng tuyển...</td></tr>';

  try {
    const apps = await api.getApplications(1, 50);
    state.applications = apps;

    if (apps.length === 0) {
      container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-muted);">Chưa có đơn ứng tuyển nào được ghi nhận.</td></tr>';
      return;
    }

    container.innerHTML = apps.map(app => {
      let statusBadge = 'badge-blue';
      if (app.status === 'SENT') statusBadge = 'badge-green';
      if (app.status === 'INTERVIEW') statusBadge = 'badge-amber';
      if (app.status === 'REJECTED') statusBadge = 'badge-red';

      return `
        <tr>
          <td><strong>${app.subject || 'Đơn ứng tuyển công việc'}</strong></td>
          <td>${app.channel || 'EMAIL'}</td>
          <td>${app.recipient_email || 'N/A'}</td>
          <td><span class="badge ${statusBadge}">${app.status}</span></td>
          <td>${formatDate(app.sent_at || app.created_at)}</td>
          <td>
            <select class="form-control" style="padding: 0.25rem 0.5rem; font-size: 0.8rem; width: auto;" onchange="changeApplicationStatus('${app.id}', this.value)">
              <option value="DRAFT" ${app.status === 'DRAFT' ? 'selected' : ''}>DRAFT</option>
              <option value="READY" ${app.status === 'READY' ? 'selected' : ''}>READY</option>
              <option value="SENT" ${app.status === 'SENT' ? 'selected' : ''}>SENT</option>
              <option value="INTERVIEW" ${app.status === 'INTERVIEW' ? 'selected' : ''}>INTERVIEW</option>
              <option value="OFFER" ${app.status === 'OFFER' ? 'selected' : ''}>OFFER</option>
              <option value="REJECTED" ${app.status === 'REJECTED' ? 'selected' : ''}>REJECTED</option>
            </select>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<tr><td colspan="6" style="color: var(--danger-700); padding: 2rem; text-align: center;">Lỗi tải đơn ứng tuyển: ${err.message}</td></tr>`;
  }
}

export async function changeApplicationStatus(appId, newStatus) {
  try {
    await api.updateApplicationStatus(appId, newStatus);
    showToast(`Đã chuyển trạng thái sang ${newStatus}!`, 'success');
  } catch (err) {
    showToast(`Không thể cập nhật trạng thái: ${err.message}`, 'error');
  }
}

export function prepareApplicationModal(jobId) {
  showToast('Tính năng nộp hồ sơ tự động đang sẵn sàng cho công việc này.', 'info');
}
