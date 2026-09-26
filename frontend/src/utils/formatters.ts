/**
 * Job Hunter Platform — Data Formatting Utilities
 */

export function formatCurrency(amount?: number | null, currency?: string | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) {
    return 'Thỏa thuận';
  }

  const curr = (currency || 'VND').toUpperCase();

  if (curr === 'USD') {
    return `$${amount.toLocaleString('en-US')}`;
  }

  // VND format: Ví dụ 15.000.000 đ hoặc 15 tr
  if (amount >= 1_000_000) {
    const millions = amount / 1_000_000;
    return `${millions % 1 === 0 ? millions : millions.toFixed(1)} triệu đ`;
  }

  return `${amount.toLocaleString('vi-VN')} đ`;
}

export function formatDate(dateString?: string | null): string {
  if (!dateString) return 'Mới đăng';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Mới đăng';

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 60) {
      return diffMinutes <= 1 ? 'Vừa xong' : `${diffMinutes} phút trước`;
    }
    if (diffHours < 24) {
      return `${diffHours} giờ trước`;
    }
    if (diffDays < 7) {
      return `${diffDays} ngày trước`;
    }

    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch (_) {
    return 'Mới đăng';
  }
}

export function getCompanyMonogram(name?: string | null): string {
  if (!name || typeof name !== 'string') return 'JH';
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function getSourceBadgeInfo(source?: string | null): { label: string; colorClass: string } {
  const s = (source || 'other').toLowerCase();
  switch (s) {
    case 'itviec':
      return { label: 'ITViec', colorClass: 'bg-red-50 text-red-700 border-red-200' };
    case 'topcv':
      return { label: 'TopCV', colorClass: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
    case 'remotive':
      return { label: 'Remotive', colorClass: 'bg-blue-50 text-blue-700 border-blue-200' };
    case 'careerlink':
      return { label: 'CareerLink', colorClass: 'bg-cyan-50 text-cyan-700 border-cyan-200' };
    case 'topdev':
      return { label: 'TopDev', colorClass: 'bg-orange-50 text-orange-700 border-orange-200' };
    case 'vietnamworks':
      return { label: 'VietnamWorks', colorClass: 'bg-indigo-50 text-indigo-700 border-indigo-200' };
    case 'manual':
      return { label: 'Nhập tay', colorClass: 'bg-purple-50 text-purple-700 border-purple-200' };
    case 'mock':
      return { label: 'Demo', colorClass: 'bg-slate-100 text-slate-700 border-slate-300' };
    default:
      return { label: source || 'Đối tác', colorClass: 'bg-slate-50 text-slate-600 border-slate-200' };
  }
}

export function convertMarkdownToCleanEmail(
  markdown: string,
  candidateName = '',
  targetTitle = '',
  _companyName = ''
): { subject: string; body: string } {
  const lines = markdown.split('\n');
  const bodyLines: string[] = [];
  let subject = `Ứng tuyển vị trí ${targetTitle || 'Software Engineer'} — ${candidateName || 'Ứng viên'}`;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // Catch Subject line
    if (line.toLowerCase().startsWith('subject:') || line.toLowerCase().startsWith('tiêu đề:')) {
      subject = line.replace(/^(subject|tiêu đề):\s*/i, '').trim();
      continue;
    }

    if (line.startsWith('#')) {
      const headerText = line.replace(/^#+\s*/, '').replace(/:$/, '');
      bodyLines.push('');
      bodyLines.push(headerText.toUpperCase());
      continue;
    }

    if (/^[-*•]\s+/.test(line)) {
      const itemText = line.replace(/^[-*•]\s+/, '');
      bodyLines.push(`• ${itemText}`);
      continue;
    }

    bodyLines.push(line);
  }

  // Clean empty lines
  const body = bodyLines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  return { subject, body };
}
