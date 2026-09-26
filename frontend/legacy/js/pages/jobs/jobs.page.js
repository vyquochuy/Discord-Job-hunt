/**
 * Job Hunter Platform — Jobs Explorer Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, escapeHtml } from '../../utils/dom.js';
import {
  formatCurrency,
  formatDate,
  getCompanyMonogram,
  formatSourceBadge,
} from '../../utils/formatters.js';
import { showToast } from '../../components/common/toast.js';

export function getJobFilterParams() {
  const keyword = document.getElementById('search-job-input')?.value?.trim() || '';
  const work_mode = document.getElementById('filter-work-mode')?.value || '';
  const level = document.getElementById('filter-level')?.value || '';
  const location = document.getElementById('filter-location')?.value || '';
  const source = document.getElementById('filter-source')?.value || '';

  return { keyword, work_mode, level, location, source };
}

export async function loadJobs() {
  const filters = getJobFilterParams();
  renderJobsGridSkeleton();

  try {
    const res = await api.getJobs({ ...filters, page_size: 50 });
    state.jobs = res.items || [];
    renderJobsGrid(state.jobs);
  } catch (err) {
    showToast(`Không thể tải danh sách việc làm: ${err.message}`, 'error');
  }
}

export function renderJobsGridSkeleton() {
  const gridEl = document.getElementById('jobs-grid');
  if (!gridEl) return;

  gridEl.innerHTML = Array(6).fill(0).map(() => `
    <div class="skeleton-card">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="skeleton skeleton-avatar"></div>
        <div class="skeleton skeleton-badge"></div>
      </div>
      <div class="skeleton skeleton-title"></div>
      <div class="skeleton skeleton-text" style="width: 40%;"></div>
      <div style="display: flex; gap: 0.4rem; margin: 0.5rem 0;">
        <div class="skeleton skeleton-badge"></div>
        <div class="skeleton skeleton-badge"></div>
      </div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text" style="width: 80%;"></div>
    </div>
  `).join('');
}

export function renderJobsGrid(jobs) {
  const gridEl = document.getElementById('jobs-grid');
  if (!gridEl) return;

  if (jobs.length === 0) {
    gridEl.innerHTML = `
      <div class="card empty-state-card" style="grid-column: 1/-1;">
        <div class="empty-state-icon-box">
          <i data-lucide="search-x" class="icon-lg"></i>
        </div>
        <h3 class="empty-state-title">Không tìm thấy tin tuyển dụng phù hợp</h3>
        <p class="empty-state-text">Hãy thử thay đổi từ khóa, điều chỉnh lại bộ lọc hoặc quét bổ sung dữ liệu mới từ các sàn tuyển dụng.</p>
        <div style="display: flex; gap: 0.5rem; justify-content: center;">
          <button class="btn btn-outline btn-sm" onclick="document.getElementById('search-job-input').value=''; if (typeof window.loadJobs === 'function') window.loadJobs();">
            <i data-lucide="rotate-ccw" class="icon-sm"></i>
            <span>Đặt lại bộ lọc</span>
          </button>
          <button class="btn btn-primary btn-sm" onclick="openScanJobsModal()">
            <i data-lucide="search" class="icon-sm"></i>
            <span>Quét thêm tin</span>
          </button>
        </div>
      </div>
    `;
    refreshIcons();
    return;
  }

  gridEl.innerHTML = jobs.map(job => {
    const monogram = getCompanyMonogram(job.company_name);
    const sourceBadge = formatSourceBadge(job.source, job.source_url);
    const hasSalary = job.min_salary || job.max_salary;
    const salaryText = hasSalary
      ? `${formatCurrency(job.min_salary)} - ${formatCurrency(job.max_salary)}`
      : 'Thỏa thuận';

    return `
      <div class="card card-hover job-card" onclick="openJobDetailModal('${job.id}')">
        <div>
          <div class="job-card-header">
            <div style="display: flex; gap: 0.75rem; align-items: center; min-width: 0;">
              <div class="company-avatar">${monogram}</div>
              <div style="min-width: 0;">
                <h3 class="job-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(job.title)}</h3>
                <div class="job-company">${escapeHtml(job.company_name || 'Công ty Tuyển dụng')}</div>
              </div>
            </div>
            <div style="display: flex; gap: 0.35rem; align-items: center; flex-shrink: 0;">
              ${sourceBadge}
            </div>
          </div>

          <div class="job-meta-tags">
            <span class="badge badge-gray">
              <i data-lucide="map-pin" class="icon-sm"></i>
              <span>${escapeHtml(job.location || 'Vietnam')}</span>
            </span>
            <span class="badge badge-blue">
              <i data-lucide="briefcase" class="icon-sm"></i>
              <span>${escapeHtml(job.level || 'All Levels')}</span>
            </span>
            <span class="badge badge-gray">
              <i data-lucide="home" class="icon-sm"></i>
              <span>${escapeHtml(job.work_mode || 'ONSITE')}</span>
            </span>
            ${hasSalary ? `
              <span class="badge badge-green">
                <i data-lucide="dollar-sign" class="icon-sm"></i>
                <span>${escapeHtml(salaryText)}</span>
              </span>
            ` : ''}
          </div>

          <div class="job-description-snippet">
            ${escapeHtml(job.description ? job.description.replace(/<[^>]*>?/gm, '').slice(0, 160) + '...' : 'Không có mô tả chi tiết.')}
          </div>
        </div>

        <div class="job-card-footer">
          <div class="job-date">
            <i data-lucide="clock" class="icon-sm"></i>
            <span>${formatDate(job.posted_at || job.created_at)}</span>
          </div>
          <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openJobDetailModal('${job.id}')">
            <span>Chi tiết</span>
            <i data-lucide="chevron-right" class="icon-sm"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');

  refreshIcons();
}
