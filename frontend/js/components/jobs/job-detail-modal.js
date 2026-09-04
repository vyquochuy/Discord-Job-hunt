/**
 * Job Hunter Platform — Job Detail Modal & Match Intelligence Component
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, escapeHtml } from '../../utils/dom.js';
import { showToast } from '../common/toast.js';
import { openAuthModal } from '../common/auth-modal.js';

export async function openJobDetailModal(jobId) {
  const modalBackdrop = document.getElementById('job-detail-modal');
  if (!modalBackdrop) return;

  modalBackdrop.classList.add('active');
  const titleEl = document.getElementById('modal-job-title');
  const bodyEl = document.getElementById('modal-job-body');
  const footerEl = document.getElementById('modal-job-footer');

  if (titleEl) titleEl.textContent = 'Đang tải thông tin chi tiết...';
  if (bodyEl) {
    bodyEl.innerHTML = `
      <div style="text-align: center; padding: 3rem;">
        <div class="spinner spinner-primary" style="width: 28px; height: 28px; margin-bottom: 0.75rem;"></div>
        <div style="color: var(--text-muted); font-size: 0.88rem;">Đang tải dữ liệu tuyển dụng và đối soát điểm tương thích...</div>
      </div>
    `;
  }
  if (footerEl) footerEl.innerHTML = '';

  try {
    const [job, match] = await Promise.all([
      api.getJobDetail(jobId),
      api.getMatchDetail(jobId).catch(() => null),
    ]);

    state.selectedJob = job;
    state.selectedMatch = match;

    if (titleEl) titleEl.textContent = job.title;

    // Render Modal Body
    let matchSectionHtml = '';
    if (match) {
      const scoreClass = match.score >= 80 ? 'score-high' : match.score >= 60 ? 'score-med' : 'score-low';

      const signalsList = Object.entries(match.signals || {}).map(([key, val]) => {
        const percent = (val.score || 0) * 100;
        return `
          <div style="margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 0.2rem;">
              <span style="text-transform: capitalize; font-weight: 500; color: var(--slate-700);">${key.replace(/_/g, ' ')}</span>
              <strong>${percent.toFixed(0)}%</strong>
            </div>
            <div style="height: 5px; background-color: var(--slate-200); border-radius: 4px; overflow: hidden;">
              <div style="width: ${percent}%; height: 100%; background-color: var(--primary-600);"></div>
            </div>
          </div>
        `;
      }).join('');

      matchSectionHtml = `
        <div class="card" style="background-color: var(--primary-50); border-color: var(--primary-100); margin-bottom: 1.25rem; padding: 1.15rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--primary-700); letter-spacing: 0.04em;">ĐIỂM TƯƠNG THÍCH 7 CHỈ SỐ TẤT ĐỊNH</div>
              <h4 style="font-size: 1.1rem; color: var(--primary-900); margin-top: 0.2rem;">${match.recommendation || 'Đề xuất ứng tuyển'}</h4>
            </div>
            <div class="score-badge ${scoreClass}" style="font-size: 1.35rem; padding: 0.4rem 0.85rem;">
              ${match.score.toFixed(0)}/100
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 0.75rem;">
            <div>
              <div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text-muted);">PHÂN TÍCH 7 CHỈ SỐ</div>
              ${signalsList}
            </div>
            <div>
              <div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text-muted);">TỔNG HỢP BẰNG CHỨNG ĐỐI SOÁT</div>
              <div style="font-size: 0.82rem; line-height: 1.55; color: var(--text-body); background: white; padding: 0.75rem; border-radius: var(--radius-md); border: 1px solid var(--primary-100); max-height: 160px; overflow-y: auto;">
                ${escapeHtml(match.explanation_text) || 'Chưa có phân tích chi tiết.'}
              </div>
            </div>
          </div>
        </div>
      `;
    } else {
      matchSectionHtml = `
        <div class="card" style="margin-bottom: 1.25rem; padding: 1rem; text-align: center;">
          <p style="color: var(--text-muted); font-size: 0.85rem;">Chưa có bản phân tích điểm tương thích cho công việc này.</p>
          <button class="btn btn-outline btn-sm" style="margin-top: 0.5rem;" onclick="triggerCalculateMatch('${job.id}')">
            <i data-lucide="refresh-cw" class="icon-sm"></i>
            <span>Tính điểm phù hợp ngay</span>
          </button>
        </div>
      `;
    }

    const skillsHtml = (job.skills || []).map(js => `
      <span class="skill-pill ${js.is_required ? 'matched' : ''}">
        ${escapeHtml(js.skill?.canonical_name || 'Skill')} ${js.is_required ? '<i data-lucide="check" class="icon-sm" style="width: 11px; height: 11px;"></i>' : ''}
      </span>
    `).join('');

    if (bodyEl) {
      bodyEl.innerHTML = `
        ${matchSectionHtml}

        <div style="margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem;">Thông tin tổng quan</h4>
          <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
            <span class="badge badge-blue">
              <i data-lucide="building" class="icon-sm"></i>
              <span>${escapeHtml(job.company_name)}</span>
            </span>
            <span class="badge badge-gray">
              <i data-lucide="map-pin" class="icon-sm"></i>
              <span>${escapeHtml(job.location || 'Vietnam')}</span>
            </span>
            <span class="badge badge-gray">
              <i data-lucide="briefcase" class="icon-sm"></i>
              <span>${escapeHtml(job.level || 'All Levels')}</span>
            </span>
            <span class="badge badge-gray">
              <i data-lucide="home" class="icon-sm"></i>
              <span>${escapeHtml(job.work_mode || 'ONSITE')}</span>
            </span>
            ${job.contact_email ? `
              <span class="badge badge-green">
                <i data-lucide="mail" class="icon-sm"></i>
                <span>${escapeHtml(job.contact_email)}</span>
              </span>
            ` : ''}
            ${job.source_url ? `
              <a href="${escapeHtml(job.source_url)}" target="_blank" rel="noopener noreferrer" class="badge badge-outline" style="text-decoration: none;" title="Mở link bài đăng gốc">
                <i data-lucide="external-link" class="icon-sm"></i>
                <span>Xem bài đăng gốc</span>
              </a>
            ` : ''}
          </div>
        </div>

        <div style="margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem;">Kỹ năng trích xuất (Canonical Skills)</h4>
          <div class="job-skills-list">${skillsHtml || '<span style="color: var(--text-muted); font-size: 0.85rem;">Không có dữ liệu kỹ năng trích xuất.</span>'}</div>
        </div>

        <div>
          <h4 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem;">Mô tả công việc chi tiết (JD)</h4>
          <div style="background-color: var(--bg-muted); padding: 1rem; border-radius: var(--radius-md); font-size: 0.85rem; line-height: 1.6; max-height: 280px; overflow-y: auto; border: 1px solid var(--border-default); white-space: pre-wrap;">${escapeHtml(job.description || 'Không có mô tả.')}</div>
        </div>
      `;
    }

    if (footerEl) {
      footerEl.innerHTML = `
        <button class="btn btn-outline" onclick="saveJobBookmark('${job.id}')">
          <i data-lucide="bookmark" class="icon-sm"></i>
          <span>Lưu tin</span>
        </button>
        <button class="btn btn-outline" onclick="startResumeTailoring('${job.id}', true)" title="Tạo lại bản mới bỏ qua cache">
          <i data-lucide="refresh-cw" class="icon-sm"></i>
          <span>Tái tạo mới</span>
        </button>
        <button class="btn btn-primary" onclick="startResumeTailoring('${job.id}', false)">
          <i data-lucide="file-text" class="icon-sm"></i>
          <span>tạo thiết kế hồ sơ</span>
        </button>
        <button class="btn btn-success" onclick="prepareApplicationModal('${job.id}')">
          <i data-lucide="send" class="icon-sm"></i>
          <span>Nộp ứng tuyển</span>
        </button>
      `;
    }

    refreshIcons();
  } catch (err) {
    if (bodyEl) {
      bodyEl.innerHTML = `
        <div style="color: var(--danger-700); padding: 2rem; text-align: center;">
          <i data-lucide="alert-circle" class="icon-lg" style="margin-bottom: 0.5rem;"></i>
          <div>Lỗi tải thông tin chi tiết: ${escapeHtml(err.message)}</div>
        </div>
      `;
    }
    refreshIcons();
  }
}

export function closeJobDetailModal() {
  const modalBackdrop = document.getElementById('job-detail-modal');
  if (modalBackdrop) modalBackdrop.classList.remove('active');
}

export async function triggerCalculateMatch(jobId) {
  try {
    showToast('Đang tính toán điểm tương thích...', 'info');
    await api.calculateMatch(jobId, true);
    showToast('Đã tính toán thành công!', 'success');
    openJobDetailModal(jobId);
  } catch (err) {
    showToast(`Tính điểm thất bại: ${err.message}`, 'error');
  }
}

export async function saveJobBookmark(jobId) {
  if (!state.currentUser) {
    showToast('Vui lòng đăng nhập để lưu tin tuyển dụng vào danh sách theo dõi!', 'warning');
    openAuthModal('login');
    return;
  }
  try {
    await api.saveJob(jobId, 'Lưu từ Web App');
    showToast('Đã lưu công việc vào danh sách theo dõi!', 'success');
  } catch (err) {
    showToast(`Không thể lưu tin: ${err.message}`, 'error');
  }
}
