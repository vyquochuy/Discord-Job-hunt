/**
 * Job Hunter Platform — Job Card Component
 */

import { escapeHtml } from '../../utils/dom.js';
import {
  formatCurrency,
  formatDate,
  getCompanyMonogram,
  formatSourceBadge,
} from '../../utils/formatters.js';

export function createJobCard(job) {
  const monogram = getCompanyMonogram(job.company_name);
  const sourceBadge = formatSourceBadge(job.source, job.source_url);
  const salaryText = formatCurrency(job.salary_max || job.salary_min, job.salary_currency);
  const levelText = job.level ? job.level.toUpperCase() : 'ALL LEVELS';
  const workModeText = job.work_mode ? job.work_mode.toUpperCase() : 'ONSITE';

  return `
    <div class="card card-hover job-card" onclick="openJobDetailModal('${job.id}')">
      <div class="job-card-header">
        <div class="company-avatar">${monogram}</div>
        <div style="flex: 1; min-width: 0;">
          <h3 class="job-title" title="${escapeHtml(job.title)}">${escapeHtml(job.title)}</h3>
          <div class="company-name">${escapeHtml(job.company_name || 'N/A')}</div>
        </div>
      </div>

      <div class="job-card-meta">
        <span class="badge badge-gray" title="Địa điểm">
          <i data-lucide="map-pin" class="icon-sm"></i>
          <span>${escapeHtml(job.location || 'Vietnam')}</span>
        </span>
        <span class="badge badge-blue" title="Hình thức làm việc">
          <i data-lucide="laptop" class="icon-sm"></i>
          <span>${escapeHtml(workModeText)}</span>
        </span>
        <span class="badge badge-gray" title="Cấp bậc">
          <i data-lucide="layers" class="icon-sm"></i>
          <span>${escapeHtml(levelText)}</span>
        </span>
        <span class="badge badge-green" title="Mức lương">
          <i data-lucide="dollar-sign" class="icon-sm"></i>
          <span>${escapeHtml(salaryText)}</span>
        </span>
        ${sourceBadge}
      </div>

      <p class="job-card-description">
        ${escapeHtml(job.description_raw ? job.description_raw.slice(0, 140) + '...' : 'Chưa có mô tả chi tiết.')}
      </p>

      <div class="job-card-footer">
        <span style="font-size: 0.75rem; color: var(--text-muted);">
          Đăng ngày: ${formatDate(job.posted_at || job.created_at)}
        </span>
        <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openJobDetailModal('${job.id}')">
          <span>Chi tiết</span>
          <i data-lucide="chevron-right" class="icon-sm"></i>
        </button>
      </div>
    </div>
  `;
}

export function renderJobsSkeleton(container, count = 6) {
  if (!container) return;
  container.innerHTML = Array(count).fill(0).map(() => `
    <div class="card job-card" style="pointer-events: none;">
      <div class="job-card-header">
        <div class="skeleton skeleton-avatar"></div>
        <div style="flex: 1; display: flex; flex-direction: column; gap: 0.4rem;">
          <div class="skeleton skeleton-title" style="width: 70%;"></div>
          <div class="skeleton skeleton-text" style="width: 40%;"></div>
        </div>
      </div>
      <div style="display: flex; gap: 0.4rem; margin: 0.75rem 0;">
        <div class="skeleton skeleton-badge"></div>
        <div class="skeleton skeleton-badge"></div>
        <div class="skeleton skeleton-badge"></div>
      </div>
      <div class="skeleton skeleton-text" style="width: 100%; margin-bottom: 0.35rem;"></div>
      <div class="skeleton skeleton-text" style="width: 80%;"></div>
    </div>
  `).join('');
}
