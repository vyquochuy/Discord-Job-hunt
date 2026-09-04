/**
 * Job Hunter Platform — Resume Workspace Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, escapeHtml } from '../../utils/dom.js';
import {
  formatCurrency,
  getCompanyMonogram,
  formatSourceBadge,
} from '../../utils/formatters.js';
import { showToast } from '../../components/common/toast.js';
import { openAuthModal } from '../../components/common/auth-modal.js';
import { closeJobDetailModal } from '../../components/jobs/job-detail-modal.js';

export async function startResumeTailoring(jobId, forceRegenerate = false, customTone = 'professional_and_humble') {
  if (!state.currentUser) {
    showToast('Vui lòng đăng nhập để tạo CV và Cover Letter cá nhân hóa!', 'warning');
    openAuthModal('login', 'resume');
    return;
  }
  closeJobDetailModal();
  if (typeof window.navigateTo === 'function') {
    window.navigateTo('resume');
  }

  const resumeContainer = document.getElementById('resume-workspace-content');
  if (resumeContainer) {
    const actionLabel = forceRegenerate ? 'Tái tạo mới' : 'tạo thiết kế hồ sơ';
    resumeContainer.innerHTML = `
      <div style="text-align: center; padding: 4rem 1.5rem;">
        <div class="spinner spinner-primary" style="width: 32px; height: 32px; margin-bottom: 1rem;"></div>
        <h4 style="font-size: 1rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.35rem;">
          Đang thực hiện ${actionLabel}...
        </h4>
        <p style="color: var(--text-muted); font-size: 0.85rem; max-width: 480px; margin: 0 auto;">
          Quy trình kiểm soát đa tầng: Trích xuất bằng chứng MMR → Tạo mã nguồn LaTeX → Xác minh Fact-checking → Biên dịch PDF an toàn.
        </p>
      </div>
    `;
  }

  try {
    const tailoredResume = await api.tailorResume(jobId, forceRegenerate, customTone);
    state.selectedResume = tailoredResume;
    renderResumeWorkspace(tailoredResume);
    showToast(forceRegenerate ? 'Đã tái tạo CV và Cover Letter mới!' : 'Đã hoàn thành sinh CV tạo thiết kế cá nhân hóa!', 'success');
  } catch (err) {
    if (resumeContainer) {
      resumeContainer.innerHTML = `
        <div class="card empty-state-card">
          <div class="empty-state-icon-box" style="color: var(--danger-600); background-color: var(--danger-50);">
            <i data-lucide="alert-circle" class="icon-lg"></i>
          </div>
          <h3 class="empty-state-title">Lỗi tạo hồ sơ tạo thiết kế</h3>
          <p class="empty-state-text">${escapeHtml(err.message)}</p>
          <button class="btn btn-primary btn-sm" onclick="navigateTo('jobs')">
            <i data-lucide="arrow-left" class="icon-sm"></i>
            <span>Quay lại Khám phá việc làm</span>
          </button>
        </div>
      `;
      refreshIcons();
    }
    showToast(`Lỗi tạo hồ sơ: ${err.message}`, 'error');
  }
}

export async function deleteTailoredResumeForJob(jobId) {
  if (!confirm('Bạn có chắc chắn muốn xóa bản CV tạo thiết kế và Cover Letter này để làm mới từ đầu?')) {
    return;
  }

  try {
    showToast('Đang xóa bản CV và Cover Letter...', 'info');
    await api.deleteTailoredResume(jobId);
    showToast('Đã xóa thành công bản CV tạo thiết kế!', 'success');
    state.selectedResume = null;

    const container = document.getElementById('resume-workspace-content');
    if (container) {
      container.innerHTML = `
        <div class="card empty-state-card">
          <div class="empty-state-icon-box">
            <i data-lucide="trash-2" class="icon-lg"></i>
          </div>
          <h3 class="empty-state-title">Đã xóa bản tạo thiết kế hồ sơ</h3>
          <p class="empty-state-text">
            Bản ghi trong cơ sở dữ liệu và các tệp tin PDF/TeX trên ổ đĩa đã được dọn sạch. Bạn có thể quay lại mục <strong>Khám phá việc làm</strong> để tạo mới bất kỳ lúc nào.
          </p>
          <button class="btn btn-primary" onclick="navigateTo('jobs')">
            <i data-lucide="search" class="icon-sm"></i>
            <span>Khám phá việc làm</span>
          </button>
        </div>
      `;
      refreshIcons();
    }
  } catch (err) {
    showToast(`Lỗi xóa hồ sơ: ${err.message}`, 'error');
  }
}

export function switchResumePreviewTab(tab) {
  const tabTexBtn = document.getElementById('btn-tab-tex');
  const tabPdfBtn = document.getElementById('btn-tab-pdf');
  const viewTex = document.getElementById('resume-tab-tex');
  const viewPdf = document.getElementById('resume-tab-pdf');

  if (tab === 'tex') {
    if (tabTexBtn) tabTexBtn.className = 'btn btn-primary btn-sm';
    if (tabPdfBtn) tabPdfBtn.className = 'btn btn-outline btn-sm';
    if (viewTex) viewTex.style.display = 'block';
    if (viewPdf) viewPdf.style.display = 'none';
  } else {
    if (tabTexBtn) tabTexBtn.className = 'btn btn-outline btn-sm';
    if (tabPdfBtn) tabPdfBtn.className = 'btn btn-primary btn-sm';
    if (viewTex) viewTex.style.display = 'none';
    if (viewPdf) {
      viewPdf.style.display = 'block';
      const iframe = viewPdf.querySelector('iframe');
      if (iframe && state.selectedResume) {
        const freshUrl = api.getResumePdfUrl(state.selectedResume.id, false);
        if (iframe.src !== freshUrl) {
          iframe.src = freshUrl;
        }
      }
    }
  }
}

export async function saveAndRecompileResume(resumeId) {
  const editor = document.getElementById('resume-tex-editor');
  if (!editor) return;
  const newLatex = editor.value;

  try {
    showToast('Đang lưu và biên dịch lại PDF...', 'info');
    const updated = await api.updateResumeLatex(resumeId, newLatex);
    state.selectedResume = updated;
    renderResumeWorkspace(updated);
    showToast('Đã cập nhật mã nguồn TeX và biên dịch ra PDF thành công!', 'success');
  } catch (err) {
    showToast(`Lỗi biên dịch lại LaTeX: ${err.message}`, 'error');
  }
}

export function copyResumeLatex() {
  const editor = document.getElementById('resume-tex-editor');
  if (editor) {
    navigator.clipboard.writeText(editor.value);
    showToast('Đã sao chép mã nguồn LaTeX vào Clipboard!', 'success');
  }
}

export function convertMarkdownToCleanEmail(md, candidateName = '', jobTitle = '', companyName = '') {
  if (!md) return { subject: '', body: '' };

  let text = md;
  // Xóa tiêu đề Cover Letter ở đầu
  text = text.replace(/^#\s+Cover Letter\s*\n+/i, '');

  let emailSubject = `Ứng tuyển vị trí ${jobTitle || 'Vị trí'} tại ${companyName || 'Công ty'} - ${candidateName || 'Ứng viên'}`;

  // Bóc tách metadata nếu có khối --- ở đầu
  const metaDividerIdx = text.indexOf('---');
  if (metaDividerIdx !== -1 && metaDividerIdx < 450) {
    const metaBlock = text.slice(0, metaDividerIdx);
    const posMatch = metaBlock.match(/\*\*Position:\*\*\s*(.+)/i);
    const compMatch = metaBlock.match(/\*\*Company:\*\*\s*(.+)/i);
    if (posMatch && compMatch) {
      emailSubject = `Ứng tuyển vị trí ${posMatch[1].trim()} tại ${compMatch[1].trim()} - ${candidateName || 'Ứng viên'}`;
    }
    text = text.slice(metaDividerIdx + 3).trim();
  } else {
    // Xóa các dòng metadata thô nếu không có divider ---
    text = text.replace(/^\*\*Candidate:\*\*.*$/gim, '')
      .replace(/^\*\*Email:\*\*.*$/gim, '')
      .replace(/^\*\*Location:\*\*.*$/gim, '')
      .replace(/^\*\*Date:\*\*.*$/gim, '')
      .replace(/^\*\*To:\*\*.*$/gim, '')
      .replace(/^\*\*Company:\*\*.*$/gim, '')
      .replace(/^\*\*Position:\*\*.*$/gim, '')
      .trim();
  }

  // Chuyển đổi Markdown Headers thành đề mục chuẩn
  text = text.replace(/^###?\s*(.+)$/gm, '$1:');

  // Chuyển đổi Markdown links [Text](URL) -> Text (URL)
  text = text.replace(/\[(.*?)\]\((.*?)\)/g, '$1: $2');

  // Chuyển đổi bullet points - text / * text -> • text
  text = text.replace(/^[-*]\s+/gm, '• ');

  // Loại bỏ Markdown bold **text** và italic *text*
  text = text.replace(/\*\*(.*?)\*\*/g, '$1');
  text = text.replace(/\*(.*?)\*/g, '$1');
  text = text.replace(/_(.*?)_/g, '$1');

  // Chuẩn hóa dòng trống
  text = text.replace(/\n{3,}/g, '\n\n').trim();

  return {
    subject: emailSubject,
    body: text,
  };
}

export function renderCoverLetterHtml(md) {
  if (!md) return '<p style="color: var(--text-muted); padding: 0.5rem 0;">Chưa có dữ liệu Cover Letter.</p>';

  let text = md;
  const metaDividerIdx = text.indexOf('---');
  if (metaDividerIdx !== -1 && metaDividerIdx < 450) {
    text = text.slice(metaDividerIdx + 3).trim();
  } else {
    text = text.replace(/^#\s+Cover Letter\s*\n+/i, '').trim();
    text = text.replace(/^\*\*Candidate:\*\*.*$/gim, '')
      .replace(/^\*\*Email:\*\*.*$/gim, '')
      .replace(/^\*\*Location:\*\*.*$/gim, '')
      .replace(/^\*\*Date:\*\*.*$/gim, '')
      .replace(/^\*\*To:\*\*.*$/gim, '')
      .replace(/^\*\*Company:\*\*.*$/gim, '')
      .replace(/^\*\*Position:\*\*.*$/gim, '')
      .trim();
  }

  const lines = text.split('\n');
  const htmlParts = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      if (inList) {
        htmlParts.push('</ul>');
        inList = false;
      }
      continue;
    }

    if (line.startsWith('#')) {
      if (inList) {
        htmlParts.push('</ul>');
        inList = false;
      }
      const headerText = line.replace(/^#+\s*/, '').replace(/:$/, '');
      htmlParts.push(`<h5>${escapeHtml(headerText)}</h5>`);
      continue;
    }

    if (/^[-*•]\s+/.test(line)) {
      if (!inList) {
        htmlParts.push('<ul>');
        inList = true;
      }
      const itemText = line.replace(/^[-*•]\s+/, '');
      const formatted = escapeHtml(itemText)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" style="color: var(--primary-600); text-decoration: underline;">$1</a>');
      htmlParts.push(`<li>${formatted}</li>`);
      continue;
    }

    if (inList) {
      htmlParts.push('</ul>');
      inList = false;
    }

    const formatted = escapeHtml(line)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" style="color: var(--primary-600); text-decoration: underline;">$1</a>');

    if (line.startsWith('Dear') || line.startsWith('Kính gửi') || line.startsWith('Sincerely') || line.startsWith('Trân trọng')) {
      htmlParts.push(`<p style="font-weight: 500; margin: 0.5rem 0;">${formatted}</p>`);
    } else {
      htmlParts.push(`<p>${formatted}</p>`);
    }
  }

  if (inList) {
    htmlParts.push('</ul>');
  }

  return htmlParts.join('');
}

export function copyCoverLetterCleanEmail() {
  const resume = state.selectedResume;
  if (!resume || !resume.cover_letter || !resume.cover_letter.content_markdown) {
    showToast('Chưa có dữ liệu Thư xin việc để sao chép!', 'warning');
    return;
  }

  const candidateName = state.candidateProfile ? state.candidateProfile.full_name : '';
  const targetTitle = resume.target_title || '';
  const companyName = resume.cover_letter.company_name || '';

  const { body } = convertMarkdownToCleanEmail(
    resume.cover_letter.content_markdown,
    candidateName,
    targetTitle,
    companyName
  );

  navigator.clipboard.writeText(body).then(() => {
    showToast('✅ Đã sao chép nội dung thư sạch (sẵn sàng dán trực tiếp vào Email)!', 'success');
  }).catch(() => {
    const textarea = document.createElement('textarea');
    textarea.value = body;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('✅ Đã sao chép nội dung thư sạch!', 'success');
  });
}

export function copyCoverLetterSubject() {
  const subjectEl = document.getElementById('cover-letter-subject-text');
  if (subjectEl) {
    const text = subjectEl.textContent.trim();
    navigator.clipboard.writeText(text);
    showToast('✅ Đã sao chép Tiêu đề Email vào Clipboard!', 'success');
  }
}

export function openCoverLetterInMailClient() {
  const resume = state.selectedResume;
  if (!resume || !resume.cover_letter || !resume.cover_letter.content_markdown) {
    showToast('Chưa có dữ liệu Thư xin việc!', 'warning');
    return;
  }

  const candidateName = state.candidateProfile ? state.candidateProfile.full_name : '';
  const targetTitle = resume.target_title || '';
  const companyName = resume.cover_letter.company_name || '';

  const { subject, body } = convertMarkdownToCleanEmail(
    resume.cover_letter.content_markdown,
    candidateName,
    targetTitle,
    companyName
  );

  const mailtoUrl = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.open(mailtoUrl, '_blank');
}

export function prepareApplicationModal(jobId) {
  showToast('Tính năng nộp hồ sơ tự động đang sẵn sàng cho công việc này.', 'info');
}

export async function renderResumeWorkspace(resume) {
  const container = document.getElementById('resume-workspace-content');
  if (!container) return;

  const pdfDownloadUrl = api.getResumePdfUrl(resume.id, true);
  const pdfInlineUrl = api.getResumePdfUrl(resume.id, false);
  const jobId = resume.job_id;

  // Lấy chi tiết thông tin Job mục tiêu
  let job = (state.jobs || []).find(j => j.id === jobId);
  if (!job && jobId) {
    try {
      job = await api.getJobDetail(jobId);
    } catch (e) {
      console.warn('Không thể tải chi tiết job cho workspace header:', e);
    }
  }

  const jobTitle = (job && job.title) || resume.target_title || 'Vị trí Ứng tuyển';
  const companyName = (job && job.company_name) || (resume.cover_letter && resume.cover_letter.company_name) || 'Công ty Tuyển dụng';
  const location = (job && job.location) || 'Việt Nam';
  const workMode = (job && job.work_mode) || 'Full-time';
  const level = (job && job.level) || 'All Levels';
  const monogram = getCompanyMonogram(companyName);

  const hasSalary = job && (job.min_salary || job.max_salary);
  const salaryText = hasSalary
    ? `${formatCurrency(job.min_salary, job.salary_currency)} - ${formatCurrency(job.max_salary, job.salary_currency)}`
    : 'Mức lương: Thỏa thuận';

  const sourceBadge = job ? formatSourceBadge(job.source, job.source_url) : '';

  const matchedSkillsList = (resume.matched_skills && resume.matched_skills.length > 0)
    ? resume.matched_skills
    : (job && job.skills_required ? job.skills_required : []);

  const candidateName = state.candidateProfile ? state.candidateProfile.full_name : '';
  const coverLetterMarkdown = resume.cover_letter ? resume.cover_letter.content_markdown : '';
  const { subject: emailSubject } = convertMarkdownToCleanEmail(
    coverLetterMarkdown,
    candidateName,
    jobTitle,
    companyName
  );
  const coverLetterHtml = renderCoverLetterHtml(coverLetterMarkdown);

  container.innerHTML = `
    <!-- Top Job Details Banner -->
    <div class="card" style="margin-bottom: 1rem; padding: 1.25rem 1.5rem; border-left: 4px solid var(--primary-600); background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-muted) 100%);">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
        <div style="display: flex; gap: 0.85rem; align-items: center; min-width: 0; flex: 1;">
          <div class="company-avatar" style="width: 48px; height: 48px; font-size: 1.2rem; font-weight: 700; border-radius: var(--radius-md); flex-shrink: 0;">${monogram}</div>
          <div style="min-width: 0;">
            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
              <h2 style="margin: 0; font-size: 1.2rem; font-weight: 700; color: var(--text-main); line-height: 1.3;">${escapeHtml(jobTitle)}</h2>
              ${sourceBadge}
            </div>
            <div style="font-size: 0.95rem; font-weight: 600; color: var(--primary-700); margin-top: 0.2rem;">
              ${escapeHtml(companyName)}
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
          <button class="btn btn-outline btn-sm" onclick="openJobDetailModal('${jobId}')" title="Xem toàn bộ nội dung bản mô tả công việc (JD)">
            <i data-lucide="file-text" class="icon-sm"></i>
            <span>Xem chi tiết JD</span>
          </button>
          <a href="${pdfDownloadUrl}" target="_blank" class="btn btn-primary btn-sm" title="Tải tệp tin PDF về máy">
            <i data-lucide="download" class="icon-sm"></i>
            <span>Tải PDF CV</span>
          </a>
        </div>
      </div>

      <!-- Job Meta Tags & Attributes -->
      <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.85rem; padding-top: 0.75rem; border-top: 1px solid var(--border-default);">
        <span class="badge badge-gray" style="font-size: 0.78rem;">
          <i data-lucide="map-pin" class="icon-sm"></i>
          <span>${escapeHtml(location)}</span>
        </span>
        <span class="badge badge-blue" style="font-size: 0.78rem;">
          <i data-lucide="briefcase" class="icon-sm"></i>
          <span>${escapeHtml(workMode)}</span>
        </span>
        <span class="badge badge-gray" style="font-size: 0.78rem;">
          <i data-lucide="layers" class="icon-sm"></i>
          <span>${escapeHtml(level)}</span>
        </span>
        <span class="badge badge-green" style="font-size: 0.78rem;">
          <i data-lucide="dollar-sign" class="icon-sm"></i>
          <span>${escapeHtml(salaryText)}</span>
        </span>
        <span class="badge badge-green" style="font-size: 0.78rem;">
          <i data-lucide="shield-check" class="icon-sm"></i>
          <span>Xác thực bằng chứng: ${(resume.provenance_score ?? 100).toFixed(0)}%</span>
        </span>
      </div>

      ${matchedSkillsList && matchedSkillsList.length > 0 ? `
        <div style="margin-top: 0.65rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; font-size: 0.8rem;">
          <span style="color: var(--text-muted); font-weight: 500;">Kỹ năng:</span>
          ${matchedSkillsList.slice(0, 8).map(sk => `
            <span class="badge badge-blue" style="font-size: 0.74rem; font-weight: 500;">${escapeHtml(sk)}</span>
          `).join('')}
        </div>
      ` : ''}
    </div>

    <!-- Action Toolbar -->
    <div class="card" style="margin-bottom: 1rem; padding: 0.75rem 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="badge badge-blue">Job ID: ${jobId ? jobId.slice(0, 8) : 'N/A'}</span>
        <span style="font-size: 0.82rem; color: var(--text-muted);">Phiên bản CV: v${resume.version || 1}</span>
      </div>

      <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
        <select id="tailor-tone-select" class="form-control" style="padding: 0.35rem 0.65rem; font-size: 0.82rem; width: auto;" title="Chọn văn phong Cover Letter">
          <option value="professional_and_humble">Văn phong: Chuyên nghiệp & Khiêm tốn</option>
          <option value="enthusiastic_and_modern">Văn phong: Nhiệt huyết & Hiện đại</option>
          <option value="direct_and_impactful">Văn phong: Trực diện & Tác động</option>
        </select>
        <button class="btn btn-outline btn-sm" onclick="startResumeTailoring('${jobId}', true, document.getElementById('tailor-tone-select').value)" title="Ép sinh lại mới hoàn toàn">
          <i data-lucide="refresh-cw" class="icon-sm"></i>
          <span>Tái tạo mới</span>
        </button>
        <button class="btn btn-danger btn-sm" onclick="deleteTailoredResumeForJob('${jobId}')" title="Xóa bản tạo thiết kế này">
          <i data-lucide="trash-2" class="icon-sm"></i>
          <span>Xóa bản này</span>
        </button>
        <button class="btn btn-success btn-sm" onclick="prepareApplicationModal('${jobId}')">
          <i data-lucide="send" class="icon-sm"></i>
          <span>Nộp ứng tuyển</span>
        </button>
      </div>
    </div>

    <!-- Main 2-Column Grid -->
    <div class="ws-two-column-grid">
      <!-- Left Column: LaTeX Editor & PDF Preview -->
      <div class="card ws-col" style="display: flex; flex-direction: column;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
          <h4 style="font-size: 0.95rem; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 0.4rem;">
            <i data-lucide="file-text" class="icon-sm" style="color: var(--primary-600);"></i>
            <span>Hồ sơ CV (ATS LaTeX)</span>
          </h4>
          <div style="display: flex; gap: 0.35rem;">
            <button class="btn btn-outline btn-sm" onclick="copyResumeLatex()" title="Sao chép toàn bộ TeX">
              <i data-lucide="copy" class="icon-sm"></i>
              <span>Sao chép TeX</span>
            </button>
            <button class="btn btn-warning btn-sm" onclick="saveAndRecompileResume('${resume.id}')" title="Lưu và biên dịch lại PDF">
              <i data-lucide="save" class="icon-sm"></i>
              <span>Lưu & Biên dịch lại</span>
            </button>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; padding-bottom: 0.65rem; border-bottom: 1px solid var(--border-default);">
          <div style="display: flex; gap: 0.35rem;">
            <button id="btn-tab-tex" class="btn btn-primary btn-sm" onclick="switchResumePreviewTab('tex')">
              <i data-lucide="code" class="icon-sm"></i>
              <span>Mã nguồn LaTeX (.tex)</span>
            </button>
            <button id="btn-tab-pdf" class="btn btn-outline btn-sm" onclick="switchResumePreviewTab('pdf')">
              <i data-lucide="eye" class="icon-sm"></i>
              <span>Xem trước PDF</span>
            </button>
          </div>
          <span class="badge badge-blue" style="font-size: 0.72rem;">LaTeX ATS Mode</span>
        </div>

        <div id="resume-tab-tex">
          <textarea id="resume-tex-editor" style="width: 100%; height: 560px; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.82rem; line-height: 1.5; padding: 0.75rem; border-radius: var(--radius-md); background: var(--bg-muted); color: var(--text-main); border: 1px solid var(--border-default); resize: vertical; white-space: pre;" spellcheck="false">${(resume.latex_source || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
        </div>

        <div id="resume-tab-pdf" style="height: 560px; border-radius: var(--radius-md); overflow: hidden; display: none; border: 1px solid var(--border-default);">
          <iframe src="${pdfInlineUrl}" style="width: 100%; height: 100%; border: none;"></iframe>
        </div>
      </div>

      <!-- Right Column: Cover Letter & Evidence Map -->
      <div class="ws-col" style="display: flex; flex-direction: column; gap: 1.25rem;">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
            <h4 style="font-size: 0.95rem; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 0.4rem;">
              <i data-lucide="mail" class="icon-sm" style="color: var(--primary-600);"></i>
              <span>Thư xin việc (Cover Letter)</span>
            </h4>
            
            <div style="display: flex; gap: 0.35rem; align-items: center;">
              <button class="btn btn-primary btn-sm" onclick="copyCoverLetterCleanEmail()" title="Sao chép nội dung thư sạch không có mã Markdown để dán thẳng vào Email">
                <i data-lucide="copy" class="icon-sm"></i>
                <span>Sao chép gửi Email</span>
              </button>
              <button class="btn btn-outline btn-sm" onclick="openCoverLetterInMailClient()" title="Mở ứng dụng gửi Email mặc định">
                <i data-lucide="send" class="icon-sm"></i>
                <span>Gửi Mail</span>
              </button>
            </div>
          </div>

          <div class="cover-letter-subject-box">
            <div style="min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              <strong style="color: var(--primary-800);">Tiêu đề Email:</strong>
              <span id="cover-letter-subject-text" style="color: var(--primary-900); font-weight: 500; margin-left: 0.3rem;">${escapeHtml(emailSubject)}</span>
            </div>
            <button class="btn btn-outline btn-sm" style="padding: 0.2rem 0.5rem; font-size: 0.75rem; flex-shrink: 0;" onclick="copyCoverLetterSubject()" title="Sao chép riêng Tiêu đề Email">
              <i data-lucide="copy" class="icon-sm" style="width: 12px; height: 12px;"></i>
              <span>Chép Tiêu đề</span>
            </button>
          </div>

          <div id="cl-view-formatted" class="cover-letter-paper" style="max-height: 290px;">
            ${coverLetterHtml}
          </div>
        </div>

        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <h4 style="font-size: 0.95rem; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 0.4rem;">
              <i data-lucide="shield-check" class="icon-sm" style="color: var(--success-600);"></i>
              <span>Fact-Checking Evidence Map</span>
            </h4>
            <span class="badge badge-green" style="font-size: 0.72rem;">Độ tin cậy: ${(resume.provenance_score ?? 100).toFixed(0)}%</span>
          </div>

          <div style="max-height: 200px; overflow-y: auto;">
            ${(resume.evidence_items || []).map((ev, idx) => {
              const score = ev.similarity_score != null ? (ev.similarity_score <= 1.0 ? ev.similarity_score * 100 : ev.similarity_score) : 100;
              return `
                <div style="padding: 0.65rem 0.5rem; border-bottom: 1px solid var(--border-default); font-size: 0.82rem;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
                    <strong style="color: var(--primary-700);">[${escapeHtml(ev.section || 'KHẲNG ĐỊNH')}] #${idx + 1}</strong>
                    <span class="badge badge-green" style="font-size: 0.72rem;">Độ tin cậy: ${score.toFixed(0)}%</span>
                  </div>
                  <div style="color: var(--text-main); font-weight: 500;">${escapeHtml(ev.claim_text)}</div>
                  <div style="color: var(--text-muted); font-size: 0.76rem; margin-top: 0.25rem;">
                    <em>Căn cứ gốc: "${escapeHtml(ev.original_fact || 'Hồ sơ ứng viên')}"</em>
                  </div>
                </div>
              `;
            }).join('') || '<div style="padding: 1rem; color: var(--text-muted); text-align: center; font-size: 0.85rem;">Không có dữ liệu bằng chứng.</div>'}
          </div>
        </div>
      </div>
    </div>
  `;

  refreshIcons();
}
