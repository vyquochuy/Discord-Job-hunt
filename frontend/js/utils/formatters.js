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
    iconName = 'briefcase';
  } else if (src === 'itviec') {
    label = 'ITViec';
    iconName = 'code-2';
  } else if (src === 'careerlink') {
    label = 'CareerLink';
    iconName = 'link';
  } else if (src === 'remotive') {
    label = 'Remotive';
    iconName = 'globe';
  } else if (src === 'topdev') {
    label = 'TopDev';
    iconName = 'code';
  } else if (src === 'vietnamworks') {
    label = 'VietnamWorks';
    iconName = 'building-2';
  } else if (src === 'upwork') {
    label = 'Upwork';
    iconName = 'briefcase';
  } else if (src === 'itnavi') {
    label = 'ITNavi';
    iconName = 'compass';
  } else if (src === 'growupwork') {
    label = 'GrowUpWork';
    iconName = 'award';
  } else if (src === 'mock') {
    label = 'Demo';
    iconName = 'terminal';
  } else {
    label = src ? src.toUpperCase() : 'Khác';
  }

  let finalUrl = sourceUrl;
  if (finalUrl && finalUrl.startsWith('http')) {
    if (finalUrl.includes('upwork.com/freelance-jobs/apply/')) {
      const slug = finalUrl.split('/apply/')[1]?.split('?')[0] || '';
      const kw = slug.split('-').filter(w => !/^\d+$/.test(w)).join(' ');
      finalUrl = `https://www.upwork.com/nx/search/jobs/?q=${encodeURIComponent(kw || 'software')}&sort=recency`;
    } else if (finalUrl.includes('growupwork.com/tim-viec/') && /-\d+$/.test(finalUrl)) {
      if (finalUrl.includes('brse') || finalUrl.includes('comtor')) {
        finalUrl = 'https://growupwork.com/tim-viec/comtor-brse';
      } else if (finalUrl.includes('fullstack') || finalUrl.includes('web')) {
        finalUrl = 'https://growupwork.com/tim-viec/lap-trinh-web';
      } else if (finalUrl.includes('cloud') || finalUrl.includes('devops')) {
        finalUrl = 'https://growupwork.com/tim-viec/viec-lam-tai-japan';
      } else {
        finalUrl = 'https://growupwork.com/tim-viec/ky-su-it';
      }
    }

    return `
      <a href="${escapeHtml(finalUrl)}" target="_blank" rel="noopener noreferrer" class="badge badge-outline" onclick="event.stopPropagation();" title="Mở bài đăng tuyển dụng gốc">
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
