/**
 * Job Hunter Platform — Recommendations Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, escapeHtml } from '../../utils/dom.js';
import { getCompanyMonogram, formatSourceBadge } from '../../utils/formatters.js';

export async function loadRecommendations() {
  const container = document.getElementById('recommendations-list');
  if (!container) return;

  if (!state.currentUser) {
    container.innerHTML = `
      <div class="card empty-state-card" style="padding: 3.5rem 1.5rem;">
        <div class="empty-state-icon-box" style="background-color: var(--primary-50); color: var(--primary-600);">
          <i data-lucide="sparkles" class="icon-lg"></i>
        </div>
        <h3 class="empty-state-title">Yêu cầu Đăng nhập</h3>
        <p class="empty-state-text">
          Bảng xếp hạng đề xuất việc làm cần liên kết với hồ sơ ứng viên cá nhân để đối soát các tín hiệu tương thích và tư cách ứng tuyển (Eligibility).
        </p>
        <button class="btn btn-primary" onclick="openAuthModal('login', 'recommendations')">
          <i data-lucide="log-in" class="icon-sm"></i>
          <span>Đăng nhập hoặc Đăng ký</span>
        </button>
      </div>
    `;
    refreshIcons();
    return;
  }

  renderRecommendationsSkeleton();

  try {
    const recs = await api.getTopRecommendations(30);
    state.topRecommendations = recs;

    if (recs.length === 0) {
      container.innerHTML = `
        <div class="card empty-state-card">
          <div class="empty-state-icon-box">
            <i data-lucide="sparkles" class="icon-lg"></i>
          </div>
          <h3 class="empty-state-title">Chưa có bảng xếp hạng đề xuất</h3>
          <p class="empty-state-text">Hãy chạy tiến trình quét tin tuyển dụng để tính điểm phù hợp và tạo bảng xếp hạng.</p>
          <button class="btn btn-primary btn-sm" onclick="openScanJobsModal()">
            <i data-lucide="search" class="icon-sm"></i>
            <span>Quét tin ngay</span>
          </button>
        </div>
      `;
      refreshIcons();
      return;
    }

    container.innerHTML = recs.map((rec, idx) => {
      const scoreClass = rec.score >= 80 ? 'score-high' : rec.score >= 60 ? 'score-med' : 'score-low';
      const jobTitle = rec.title || rec.job_title || 'Kỹ sư phần mềm';
      const companyName = rec.company_name || 'Công ty Công nghệ';
      const monogram = getCompanyMonogram(companyName);
      const sourceBadge = formatSourceBadge(rec.source, rec.source_url);

      return `
        <div class="card card-hover" style="margin-bottom: 0.85rem; cursor: pointer;" onclick="openJobDetailModal('${rec.job_id}')">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
            <div style="display: flex; gap: 0.85rem; align-items: center; flex: 1; min-width: 0;">
              <div style="font-size: 1.15rem; font-weight: 700; color: var(--slate-400); width: 32px; text-align: center;">#${idx + 1}</div>
              <div class="company-avatar">${monogram}</div>
              <div style="min-width: 0; flex: 1;">
                <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                  <h3 style="font-size: 1rem; font-weight: 600; margin: 0;">${escapeHtml(jobTitle)}</h3>
                  ${sourceBadge}
                </div>
                <div style="color: var(--primary-700); font-weight: 500; font-size: 0.84rem; margin-top: 0.2rem;">
                  ${escapeHtml(companyName)} • <span style="color: var(--text-muted);">${escapeHtml(rec.location || 'Vietnam')} (${escapeHtml(rec.work_mode || 'Flexible')})</span>
                </div>
              </div>
            </div>
            <div class="score-badge ${scoreClass}" style="font-size: 1.15rem; padding: 0.35rem 0.85rem; flex-shrink: 0;">
              ${rec.score.toFixed(0)}%
            </div>
          </div>

          <div style="margin-top: 0.75rem; padding-top: 0.65rem; border-top: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <span class="badge ${rec.eligibility === 'ELIGIBLE' ? 'badge-green' : 'badge-amber'}">${rec.eligibility}</span>
              ${rec.recommendation ? `<span style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(rec.recommendation)}</span>` : ''}
            </div>
            <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openJobDetailModal('${rec.job_id}')">
              <span>Phân tích & tạo thiết kế</span>
              <i data-lucide="chevron-right" class="icon-sm"></i>
            </button>
          </div>
        </div>
      `;
    }).join('');

    refreshIcons();
  } catch (err) {
    container.innerHTML = `
      <div style="color: var(--danger-700); padding: 2rem; text-align: center;">
        <i data-lucide="alert-circle" class="icon-lg" style="margin-bottom: 0.5rem;"></i>
        <div>Lỗi tải danh sách đề xuất: ${escapeHtml(err.message)}</div>
      </div>
    `;
    refreshIcons();
  }
}

export function renderRecommendationsSkeleton() {
  const container = document.getElementById('recommendations-list');
  if (!container) return;

  container.innerHTML = Array(4).fill(0).map(() => `
    <div class="card" style="margin-bottom: 0.85rem; padding: 1.15rem;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; gap: 0.75rem; align-items: center; flex: 1;">
          <div class="skeleton skeleton-avatar"></div>
          <div style="flex: 1; display: flex; flex-direction: column; gap: 0.4rem;">
            <div class="skeleton skeleton-title" style="width: 50%;"></div>
            <div class="skeleton skeleton-text" style="width: 35%;"></div>
          </div>
        </div>
        <div class="skeleton skeleton-badge" style="width: 50px; height: 30px;"></div>
      </div>
    </div>
  `).join('');
}
