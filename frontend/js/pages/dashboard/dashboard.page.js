/**
 * Job Hunter Platform — Dashboard Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons } from '../../utils/dom.js';
import { getCompanyMonogram, formatSourceBadge } from '../../utils/formatters.js';
import { showToast } from '../../components/common/toast.js';

export async function loadDashboard() {
  renderDashboardSkeleton();

  try {
    let jobsRes = { total: 0, items: [] };
    let topRecs = [];
    let savedRes = [];
    let appsRes = [];

    // 1. Tải số liệu việc làm công khai (Ai cũng xem được)
    try {
      jobsRes = await api.getJobs({ page: 1, page_size: 5 });
    } catch (err) {
      console.warn('Could not load public jobs for dashboard:', err);
    }

    // 2. Chỉ tải các số liệu được bảo vệ khi người dùng đã đăng nhập
    if (state.currentUser) {
      const [recs, saved, apps] = await Promise.all([
        api.getTopRecommendations(5).catch(() => []),
        api.getSavedJobs().catch(() => []),
        api.getApplications(1, 10).catch(() => []),
      ]);
      topRecs = recs || [];
      savedRes = saved || [];
      appsRes = apps || [];
    }

    // Cập nhật thẻ chỉ số (Metrics)
    const totalJobsEl = document.getElementById('metric-total-jobs');
    const topRecsEl = document.getElementById('metric-top-recs');
    const savedJobsEl = document.getElementById('metric-saved-jobs');
    const appsCountEl = document.getElementById('metric-apps-count');

    if (totalJobsEl) totalJobsEl.textContent = jobsRes.total || 0;
    if (topRecsEl) {
      topRecsEl.textContent = state.currentUser ? (topRecs.length || 0) : '—';
      topRecsEl.title = state.currentUser ? 'Top công việc phù hợp' : 'Đăng nhập để xem';
    }
    if (savedJobsEl) {
      savedJobsEl.textContent = state.currentUser ? (savedRes.length || 0) : '—';
      savedJobsEl.title = state.currentUser ? 'Số việc làm đã lưu' : 'Đăng nhập để xem';
    }
    if (appsCountEl) {
      appsCountEl.textContent = state.currentUser ? (appsRes.length || 0) : '—';
      appsCountEl.title = state.currentUser ? 'Số đơn ứng tuyển đã nộp' : 'Đăng nhập để xem';
    }

    // Render khu vực Đề xuất hàng đầu
    const recsListEl = document.getElementById('dashboard-recs-list');
    if (recsListEl) {
      if (!state.currentUser) {
        recsListEl.innerHTML = `
          <div class="card empty-state-card" style="padding: 2.5rem 1.5rem;">
            <div class="empty-state-icon-box" style="background-color: var(--primary-50); color: var(--primary-600);">
              <i data-lucide="sparkles" class="icon-lg"></i>
            </div>
            <h4 class="empty-state-title">Đăng nhập để nhận Đề xuất việc làm phù hợp</h4>
            <p class="empty-state-text">
              Hệ thống AI sẽ đối soát hồ sơ và kỹ năng của bạn với các tin tuyển dụng để tính điểm tương thích 7 chỉ số tất định chuẩn xác.
            </p>
            <div style="display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap;">
              <button class="btn btn-primary btn-sm" onclick="openAuthModal('login')">
                <i data-lucide="log-in" class="icon-sm"></i>
                <span>Đăng nhập ngay</span>
              </button>
              <button class="btn btn-outline btn-sm" onclick="openAuthModal('register')">
                <i data-lucide="user-plus" class="icon-sm"></i>
                <span>Tạo tài khoản mới</span>
              </button>
            </div>
          </div>
        `;
      } else if (topRecs.length === 0) {
        recsListEl.innerHTML = `
          <div class="card empty-state-card">
            <div class="empty-state-icon-box">
              <i data-lucide="inbox" class="icon-lg"></i>
            </div>
            <h4 class="empty-state-title">Chưa có dữ liệu đề xuất</h4>
            <p class="empty-state-text">Nhấn nút "Quét tin tuyển dụng" để tự động thu thập và phân tích điểm tương thích cho hồ sơ của bạn.</p>
            <button class="btn btn-primary btn-sm" onclick="openScanJobsModal()">
              <i data-lucide="search" class="icon-sm"></i>
              <span>Quét tin tuyển dụng ngay</span>
            </button>
          </div>
        `;
      } else {
        recsListEl.innerHTML = topRecs.map(rec => {
          const scoreClass = rec.score >= 80 ? 'score-high' : rec.score >= 60 ? 'score-med' : 'score-low';
          const jobTitle = rec.title || rec.job_title || 'Kỹ sư phần mềm';
          const companyName = rec.company_name || 'Công ty Công nghệ';
          const monogram = getCompanyMonogram(companyName);
          const sourceBadge = formatSourceBadge(rec.source, rec.source_url);

          return `
            <div class="card card-hover" style="margin-bottom: 0.75rem; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem;" onclick="openJobDetailModal('${rec.job_id}')">
              <div style="display: flex; align-items: center; gap: 1rem; flex: 1; min-width: 0;">
                <div class="company-avatar">${monogram}</div>
                <div style="flex: 1; min-width: 0;">
                  <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                    <h4 style="font-size: 0.96rem; font-weight: 600; margin: 0;">${jobTitle}</h4>
                    <span class="badge ${rec.eligibility === 'ELIGIBLE' ? 'badge-green' : 'badge-amber'}">${rec.eligibility}</span>
                    ${sourceBadge}
                  </div>
                  <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem;">
                    <strong>${companyName}</strong> • ${rec.location || 'Vietnam'} • ${rec.work_mode || 'Flexible'}
                  </div>
                  <div style="font-size: 0.78rem; color: var(--primary-700); margin-top: 0.35rem; display: flex; align-items: center; gap: 0.35rem;">
                    <i data-lucide="target" class="icon-sm"></i>
                    <span>${rec.recommendation || 'Đề xuất ứng tuyển'}</span>
                  </div>
                </div>
              </div>
              <div style="text-align: right; flex-shrink: 0;">
                <div class="score-badge ${scoreClass}" style="font-size: 1.1rem; padding: 0.4rem 0.85rem;">
                  ${rec.score.toFixed(0)}%
                </div>
                <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">Độ tương thích</div>
              </div>
            </div>
          `;
        }).join('');
      }
    }
    refreshIcons();
  } catch (err) {
    showToast(`Không thể tải dữ liệu Dashboard: ${err.message}`, 'error');
  }
}

export function renderDashboardSkeleton() {
  const recsListEl = document.getElementById('dashboard-recs-list');
  if (!recsListEl) return;

  recsListEl.innerHTML = Array(3).fill(0).map(() => `
    <div class="card" style="margin-bottom: 0.75rem; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
      <div style="display: flex; align-items: center; gap: 1rem; flex: 1;">
        <div class="skeleton skeleton-avatar"></div>
        <div style="flex: 1; display: flex; flex-direction: column; gap: 0.4rem;">
          <div class="skeleton skeleton-title" style="width: 45%;"></div>
          <div class="skeleton skeleton-text" style="width: 30%;"></div>
        </div>
      </div>
      <div class="skeleton skeleton-badge" style="width: 50px; height: 32px;"></div>
    </div>
  `).join('');
}
