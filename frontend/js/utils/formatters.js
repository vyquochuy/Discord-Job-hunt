/**
 * Job Hunter Platform — Data Formatting Utilities
 */

import { escapeHtml } from './dom.js';

export function formatCurrency(val, currency = 'USD') {
  if (!val) return 'Thương lượng';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(val);
}

export function formatDate(dateStr) {
  if (!dateStr) return 'Gần đây';
  try {
    return new Date(dateStr).toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch (_) {
    return dateStr;
  }
}

export function getCompanyMonogram(companyName) {
  if (!companyName) return 'JH';
  const parts = companyName.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return companyName.slice(0, 2).toUpperCase();
}

export function formatSourceBadge(source, sourceUrl) {
  const src = (source || 'other').toLowerCase();
  let label = src.toUpperCase();
  let iconName = 'globe';

  if (src === 'manual') {
    label = 'Thủ công';
    iconName = 'edit-3';
  } else if (src === 'topcv') {
    label = 'TopCV';
  } else if (src === 'itviec') {
    label = 'ITViec';
  } else if (src === 'careerlink') {
    label = 'CareerLink';
  } else if (src === 'remotive') {
    label = 'Remotive';
  } else if (src === 'mock') {
    label = 'Demo';
    iconName = 'terminal';
  } else {
    label = src ? src.toUpperCase() : 'Khác';
  }

  if (sourceUrl && sourceUrl.startsWith('http')) {
    return `
      <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer" class="badge badge-outline" onclick="event.stopPropagation();" title="Mở bài đăng tuyển dụng gốc">
        <i data-lucide="${iconName}" class="icon-sm"></i>
        <span>${escapeHtml(label)}</span>
        <i data-lucide="external-link" class="icon-sm" style="width: 12px; height: 12px;"></i>
      </a>
    `;
  }
  return `
    <span class="badge badge-gray">
      <i data-lucide="${iconName}" class="icon-sm"></i>
      <span>${escapeHtml(label)}</span>
    </span>
  `;
}
