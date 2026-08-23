/**
 * Job Hunter Platform - Main Application Logic
 */

// Application State
const state = {
  currentUser: null,
  activeView: 'dashboard',
  jobs: [],
  topRecommendations: [],
  savedJobs: [],
  applications: [],
  candidateProfile: null,
  selectedJob: null,
  selectedMatch: null,
  selectedResume: null,
  loading: false,
};

// UI Helper: Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '⚠️';

  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Router & View Switching
function navigateTo(viewName) {
  state.activeView = viewName;
  
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.dataset.view === viewName) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  document.querySelectorAll('.view-section').forEach(view => {
    if (view.id === `view-${viewName}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  // Update header title
  const titleMap = {
    dashboard: 'Dashboard Overview',
    jobs: 'Job Explorer & Search',
    recommendations: 'AI Top Recommendations',
    profile: 'Candidate Profile & Truth Master',
    resume: 'Resume Intelligence Workspace',
    applications: 'Application Tracker Lifecycle',
    system: 'System Administration & Database Management',
  };
  const headerTitle = document.getElementById('header-title-text');
  if (headerTitle) {
    headerTitle.textContent = titleMap[viewName] || 'Job Hunter Platform';
  }

  // Trigger data loader for view
  if (viewName === 'dashboard') loadDashboard();
  if (viewName === 'jobs') loadJobs();
  if (viewName === 'recommendations') loadRecommendations();
  if (viewName === 'profile') loadProfile();
  if (viewName === 'applications') loadApplications();
}

// Formatters
function formatCurrency(val, currency = 'USD') {
  if (!val) return 'N/A';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(val);
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

// --- 1. Dashboard View ---
async function loadDashboard() {
  try {
    const [jobsRes, topRecs, savedRes, appsRes] = await Promise.all([
      api.getJobs({ page: 1, page_size: 5 }),
      api.getTopRecommendations(5),
      api.getSavedJobs().catch(() => []),
      api.getApplications(1, 10).catch(() => []),
    ]);

    // Update metrics
    document.getElementById('metric-total-jobs').textContent = jobsRes.total || 0;
    document.getElementById('metric-top-recs').textContent = topRecs.length || 0;
    document.getElementById('metric-saved-jobs').textContent = savedRes.length || 0;
    document.getElementById('metric-apps-count').textContent = appsRes.length || 0;

    // Render Top Recommendations List
    const recsListEl = document.getElementById('dashboard-recs-list');
    if (recsListEl) {
      if (topRecs.length === 0) {
        recsListEl.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: var(--text-subtle);">
            <p>Chưa có dữ liệu tính điểm. Nhấn <strong>"Run Daily Batch"</strong> để quét và phân tích AI!</p>
          </div>
        `;
      } else {
        recsListEl.innerHTML = topRecs.map(rec => {
          const scoreClass = rec.score >= 80 ? 'score-high' : rec.score >= 60 ? 'score-med' : 'score-low';
          const jobTitle = rec.title || rec.job_title || 'Software Position';
          const sourceBadge = rec.source_url
            ? `<a href="${rec.source_url}" target="_blank" class="badge badge-outline" style="text-decoration: none; font-size: 0.75rem;" onclick="event.stopPropagation();">🌐 ${rec.source ? rec.source.toUpperCase() : 'Tin gốc'} ↗</a>`
            : '';
          return `
            <div class="card card-hover" style="margin-bottom: 0.75rem; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem;" onclick="openJobDetailModal('${rec.job_id}')">
              <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                  <h4 style="font-size: 1rem;">${jobTitle}</h4>
                  <span class="badge ${rec.eligibility === 'ELIGIBLE' ? 'badge-green' : 'badge-amber'}">${rec.eligibility}</span>
                  ${sourceBadge}
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">
                  <strong>${rec.company_name}</strong> • ${rec.location || 'Vietnam'} • ${rec.work_mode}
                </div>
                <div style="font-size: 0.8rem; color: var(--primary-700); margin-top: 0.35rem;">
                  🎯 <em>${rec.recommendation}</em>
                </div>
              </div>
              <div style="text-align: right;">
                <div class="score-badge ${scoreClass}" style="font-size: 1.1rem; padding: 0.4rem 0.85rem;">
                  ${rec.score.toFixed(0)}%
                </div>
                <div style="font-size: 0.75rem; color: var(--text-subtle); margin-top: 0.25rem;">Match Score</div>
              </div>
            </div>
          `;
        }).join('');
      }
    }
  } catch (err) {
    showToast(`Lỗi tải dữ liệu Dashboard: ${err.message}`, 'error');
  }
}

// --- 2. Jobs View ---
async function loadJobs() {
  const keyword = document.getElementById('search-job-input')?.value || '';
  const work_mode = document.getElementById('filter-work-mode')?.value || '';
  const level = document.getElementById('filter-level')?.value || '';
  const location = document.getElementById('filter-location')?.value || '';
  const source = document.getElementById('filter-source')?.value || '';

  const gridEl = document.getElementById('jobs-grid');
  if (gridEl) {
    gridEl.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem;">Đang tải danh sách công việc...</div>';
  }

  try {
    const res = await api.getJobs({ keyword, work_mode, level, location, source, page_size: 50 });
    state.jobs = res.items || [];
    renderJobsGrid(state.jobs);
  } catch (err) {
    showToast(`Không thể tải tin tuyển dụng: ${err.message}`, 'error');
  }
}

function renderJobsGrid(jobs) {
  const gridEl = document.getElementById('jobs-grid');
  if (!gridEl) return;

  if (jobs.length === 0) {
    gridEl.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 4rem 1rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🔍</div>
        <h3>Không tìm thấy tin tuyển dụng phù hợp</h3>
        <p style="color: var(--text-subtle); margin-top: 0.5rem;">Thử điều chỉnh bộ lọc hoặc kích hoạt thu thập thêm dữ liệu.</p>
      </div>
    `;
    return;
  }

  gridEl.innerHTML = jobs.map(job => {
    const sourceBadge = job.source_url
      ? `<a href="${job.source_url}" target="_blank" class="badge badge-outline" style="text-decoration: none; font-size: 0.75rem;" onclick="event.stopPropagation();" title="Mở link bài đăng gốc">🌐 ${job.source ? job.source.toUpperCase() : 'Tin gốc'} ↗</a>`
      : `<span class="badge badge-gray">${job.source ? job.source.toUpperCase() : 'Nguồn'}</span>`;

    return `
      <div class="card card-hover job-card" onclick="openJobDetailModal('${job.id}')">
        <div>
          <div class="job-card-header">
            <div style="flex: 1; min-width: 0;">
              <h3 class="job-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${job.title}</h3>
              <div class="job-company">${job.company_name}</div>
            </div>
            <div style="display: flex; gap: 0.35rem; align-items: center;">
              ${sourceBadge}
              <span class="badge badge-blue">${job.work_mode}</span>
            </div>
          </div>

          <div class="job-meta-tags">
            <span class="badge badge-gray">📍 ${job.location || 'Vietnam'}</span>
            <span class="badge badge-gray">💼 ${job.level}</span>
            ${job.min_salary || job.max_salary ? `<span class="badge badge-green">💰 ${formatCurrency(job.min_salary)} - ${formatCurrency(job.max_salary)}</span>` : ''}
          </div>

          <div style="font-size: 0.85rem; color: var(--text-muted); margin: 0.75rem 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">
            ${job.description ? job.description.replace(/<[^>]*>?/gm, '') : 'Không có mô tả chi tiết.'}
          </div>
        </div>

        <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.75rem; color: var(--text-subtle);">Đăng: ${formatDate(job.posted_at || job.created_at)}</span>
          <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openJobDetailModal('${job.id}')">Chi tiết & Phân tích →</button>
        </div>
      </div>
    `;
  }).join('');
}

// --- 3. Job Detail Modal & Intelligence View ---
async function openJobDetailModal(jobId) {
  const modalBackdrop = document.getElementById('job-detail-modal');
  if (!modalBackdrop) return;

  modalBackdrop.classList.add('active');
  document.getElementById('modal-job-title').textContent = 'Đang tải thông tin chi tiết...';
  document.getElementById('modal-job-body').innerHTML = '<div style="text-align: center; padding: 3rem;">Đang nạp dữ liệu JD và đối soát Matching Intelligence...</div>';

  try {
    const [job, match] = await Promise.all([
      api.getJobDetail(jobId),
      api.getMatchDetail(jobId).catch(() => null),
    ]);

    state.selectedJob = job;
    state.selectedMatch = match;

    document.getElementById('modal-job-title').textContent = job.title;
    
    // Render Modal Body
    let matchSectionHtml = '';
    if (match) {
      const scoreClass = match.score >= 80 ? 'score-high' : match.score >= 60 ? 'score-med' : 'score-low';
      
      const signalsList = Object.entries(match.signals || {}).map(([key, val]) => {
        const percent = (val.score || 0) * 100;
        return `
          <div style="margin-bottom: 0.6rem;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.2rem;">
              <span style="text-transform: capitalize; font-weight: 500;">${key.replace(/_/g, ' ')}</span>
              <strong>${percent.toFixed(0)}%</strong>
            </div>
            <div style="height: 6px; background-color: var(--border-color); border-radius: 4px; overflow: hidden;">
              <div style="width: ${percent}%; height: 100%; background-color: var(--primary-600);"></div>
            </div>
          </div>
        `;
      }).join('');

      matchSectionHtml = `
        <div class="card" style="background-color: var(--primary-50); border-color: var(--primary-200); margin-bottom: 1.5rem; padding: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
              <div style="font-size: 0.85rem; font-weight: 600; color: var(--primary-800);">AI DETERMINISTIC MATCH SCORE</div>
              <h3 style="font-size: 1.5rem; color: var(--primary-900);">${match.recommendation}</h3>
            </div>
            <div class="score-badge ${scoreClass}" style="font-size: 1.5rem; padding: 0.5rem 1rem;">
              ${match.score.toFixed(0)}/100
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1rem;">
            <div>
              <h4 style="font-size: 0.85rem; margin-bottom: 0.5rem; color: var(--text-muted);">7-SIGNAL DETERMINISTIC BREAKDOWN</h4>
              ${signalsList}
            </div>
            <div>
              <h4 style="font-size: 0.85rem; margin-bottom: 0.5rem; color: var(--text-muted);">EXPLAINABLE EVIDENCE SYNTHESIS</h4>
              <p style="font-size: 0.85rem; line-height: 1.6; color: var(--text-main); background: white; padding: 0.75rem; border-radius: var(--radius-md); border: 1px solid var(--primary-200);">
                ${match.explanation_text || 'Chưa có phân tích chi tiết.'}
              </p>
            </div>
          </div>
        </div>
      `;
    } else {
      matchSectionHtml = `
        <div class="card" style="margin-bottom: 1.5rem; padding: 1rem; text-align: center;">
          <p style="color: var(--text-subtle);">Chưa có bản phân tích điểm khớp cho công việc này.</p>
          <button class="btn btn-outline btn-sm" style="margin-top: 0.5rem;" onclick="triggerCalculateMatch('${job.id}')">Tính điểm phù hợp ngay (0 cost)</button>
        </div>
      `;
    }

    const skillsHtml = (job.skills || []).map(js => `
      <span class="skill-pill ${js.is_required ? 'matched' : ''}">
        ${js.skill?.canonical_name || 'Skill'} ${js.is_required ? '★' : ''}
      </span>
    `).join('');

    document.getElementById('modal-job-body').innerHTML = `
      ${matchSectionHtml}

      <div style="margin-bottom: 1.5rem;">
        <h4 style="margin-bottom: 0.5rem;">Thông tin cơ bản</h4>
        <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center;">
          <span class="badge badge-blue">🏢 ${job.company_name}</span>
          <span class="badge badge-gray">📍 ${job.location || 'Vietnam'}</span>
          <span class="badge badge-gray">💼 ${job.level}</span>
          <span class="badge badge-gray">🏠 ${job.work_mode}</span>
          ${job.source ? `<span class="badge badge-purple">🌐 Sàn: ${job.source.toUpperCase()}</span>` : ''}
          ${job.contact_email ? `<span class="badge badge-green">✉️ ${job.contact_email}</span>` : ''}
          ${job.source_url ? `<a href="${job.source_url}" target="_blank" class="btn btn-outline btn-sm" style="text-decoration: none;" title="Mở bài đăng tuyển dụng gốc">🌐 Xem tin gốc trên sàn ↗</a>` : ''}
        </div>
      </div>

      <div style="margin-bottom: 1.5rem;">
        <h4 style="margin-bottom: 0.5rem;">Kỹ năng trích xuất (Canonical Skills)</h4>
        <div class="job-skills-list">${skillsHtml || '<em>Không có dữ liệu kỹ năng trích xuất.</em>'}</div>
      </div>

      <div>
        <h4 style="margin-bottom: 0.5rem;">Mô tả công việc chi tiết (JD)</h4>
        <div style="background-color: var(--bg-body); padding: 1.25rem; border-radius: var(--radius-md); font-size: 0.9rem; line-height: 1.6; max-height: 350px; overflow-y: auto; border: 1px solid var(--border-color); white-space: pre-wrap;">
          ${job.description || 'Không có mô tả.'}
        </div>
      </div>
    `;

    // Action buttons in modal footer
    const footerEl = document.getElementById('modal-job-footer');
    footerEl.innerHTML = `
      <button class="btn btn-secondary" onclick="saveJobBookmark('${job.id}')">⭐ Lưu tin này</button>
      <button class="btn btn-primary" onclick="startResumeTailoring('${job.id}', false)">📄 Tailor Resume</button>
      <button class="btn btn-outline" onclick="startResumeTailoring('${job.id}', true)" title="Bỏ qua cache và tạo lại CV mới">🔄 Tái tạo mới (Bypass Cache)</button>
      <button class="btn btn-success" onclick="prepareApplicationModal('${job.id}')">🚀 Nộp đơn ứng tuyển</button>
    `;
  } catch (err) {
    document.getElementById('modal-job-body').innerHTML = `<div style="color: var(--danger); padding: 2rem;">Lỗi tải chi tiết: ${err.message}</div>`;
  }
}

function closeJobDetailModal() {
  const modalBackdrop = document.getElementById('job-detail-modal');
  if (modalBackdrop) modalBackdrop.classList.remove('active');
}

async function triggerCalculateMatch(jobId) {
  try {
    showToast('Đang tính toán điểm phù hợp...', 'info');
    await api.calculateMatch(jobId, true);
    showToast('Tính toán thành công!', 'success');
    openJobDetailModal(jobId);
  } catch (err) {
    showToast(`Tính điểm thất bại: ${err.message}`, 'error');
  }
}

async function saveJobBookmark(jobId) {
  try {
    await api.saveJob(jobId, 'Lưu từ Web App');
    showToast('Đã lưu công việc vào danh sách theo dõi!', 'success');
  } catch (err) {
    showToast(`Không thể lưu: ${err.message}`, 'error');
  }
}

// --- 4. Resume Workspace View ---
async function startResumeTailoring(jobId, forceRegenerate = false, customTone = 'professional_and_humble') {
  closeJobDetailModal();
  navigateTo('resume');

  const resumeContainer = document.getElementById('resume-workspace-content');
  if (resumeContainer) {
    const actionLabel = forceRegenerate ? 'Tái tạo mới (Bypass Cache)' : 'May đo CV';
    resumeContainer.innerHTML = `<div style="text-align: center; padding: 4rem;">Đang thực hiện ${actionLabel} với Multi-Stage Guardrails (RoleClassifier -> MMR Evidence -> LaTeX Generator -> Provenance Verifier -> PDF Sandbox)...</div>`;
  }

  try {
    const tailoredResume = await api.tailorResume(jobId, forceRegenerate, customTone);
    state.selectedResume = tailoredResume;
    renderResumeWorkspace(tailoredResume);
    showToast(forceRegenerate ? 'Đã tái tạo CV và Cover Letter mới!' : 'Đã hoàn thành sinh CV may đo cá nhân hóa!', 'success');
  } catch (err) {
    resumeContainer.innerHTML = `<div style="color: var(--danger); padding: 2rem;">Lỗi tạo Resume: ${err.message}</div>`;
    showToast(`Lỗi tạo Resume: ${err.message}`, 'error');
  }
}

async function deleteTailoredResumeForJob(jobId) {
  if (!confirm('Bạn có chắc chắn muốn xóa bản Tailored Resume và Cover Letter của công việc này để tạo lại từ đầu?')) {
    return;
  }

  try {
    showToast('Đang xóa bản CV và Cover Letter...', 'info');
    await api.deleteTailoredResume(jobId);
    showToast('Đã xóa thành công bản CV và Cover Letter!', 'success');
    
    // Reset workspace to empty state
    const container = document.getElementById('resume-workspace-content');
    if (container) {
      container.innerHTML = `
        <div class="card empty-state-card">
          <div class="empty-state-icon">🗑️</div>
          <h3>Đã xóa bản may đo Resume & Cover Letter</h3>
          <p class="empty-state-text">
            Bản ghi trong cơ sở dữ liệu và các tệp tin PDF/TeX trên ổ đĩa đã được xóa sạch. Bạn có thể quay lại <strong>Job Explorer</strong> để tạo mới.
          </p>
          <button class="btn btn-primary" onclick="navigateTo('jobs')">Quay lại Khám phá công việc →</button>
        </div>
      `;
    }
  } catch (err) {
    showToast(`Lỗi xóa Resume: ${err.message}`, 'error');
  }
}

function renderResumeWorkspace(resume) {
  const container = document.getElementById('resume-workspace-content');
  if (!container) return;

  const pdfUrl = api.getResumePdfUrl(resume.id);
  const jobId = resume.job_id;

  container.innerHTML = `
    <!-- Top Action Toolbar -->
    <div class="card" style="margin-bottom: 1rem; padding: 0.75rem 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; background-color: var(--bg-surface-elevated);">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <span class="badge badge-blue">Job ID: ${jobId ? jobId.slice(0, 8) : 'N/A'}</span>
        <span class="badge badge-green">Zero-Hallucination: ${(resume.provenance_score ?? 100).toFixed(0)}%</span>
      </div>

      <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
        <select id="tailor-tone-select" class="form-control" style="padding: 0.35rem 0.65rem; font-size: 0.85rem; width: auto;" title="Chọn văn phong Cover Letter">
          <option value="professional_and_humble">Phong cách: Chuyên nghiệp & Khiêm tốn</option>
          <option value="enthusiastic_and_modern">Phong cách: Nhiệt huyết & Hiện đại</option>
          <option value="direct_and_impactful">Phong cách: Trực diện & Tác động</option>
        </select>
        <button class="btn btn-outline btn-sm" onclick="startResumeTailoring('${jobId}', true, document.getElementById('tailor-tone-select').value)" title="Ép sinh lại mới hoàn toàn bỏ qua cache">
          🔄 Tái tạo mới (Bypass Cache)
        </button>
        <button class="btn btn-danger btn-sm" onclick="deleteTailoredResumeForJob('${jobId}')" title="Xóa bản CV và Cover Letter này">
          🗑️ Xóa bản này
        </button>
        <button class="btn btn-success btn-sm" onclick="prepareApplicationModal('${jobId}')">
          🚀 Nộp đơn ứng tuyển
        </button>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
      <!-- Left: PDF Preview & Info -->
      <div>
        <div class="card" style="margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
              <h3>${resume.target_title}</h3>
            </div>
            <a href="${pdfUrl}" target="_blank" class="btn btn-primary btn-sm">📥 Tải file PDF</a>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted);">
            <strong>Mục tiêu:</strong> ${resume.summary_objective || 'N/A'}
          </p>
        </div>

        <div class="card" style="height: 650px; padding: 0; overflow: hidden;">
          <iframe src="${pdfUrl}" style="width: 100%; height: 100%; border: none;"></iframe>
        </div>
      </div>

      <!-- Right: Cover Letter & Provenance -->
      <div>
        <div class="card" style="margin-bottom: 1.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <h4>✉️ Cover Letter (Multi-Stage Guardrails)</h4>
            <button class="btn btn-outline btn-sm" onclick="copyCoverLetterText()">Sao chép</button>
          </div>
          <div id="cover-letter-text" style="background-color: var(--bg-body); padding: 1rem; border-radius: var(--radius-md); font-size: 0.85rem; line-height: 1.6; max-height: 280px; overflow-y: auto; white-space: pre-wrap; font-family: monospace;">
            ${resume.cover_letter ? resume.cover_letter.content_markdown : 'Chưa có Cover Letter.'}
          </div>
        </div>

        <div class="card">
          <h4 style="margin-bottom: 0.75rem;">🛡️ Fact-Checking Evidence Map</h4>
          <div style="max-height: 300px; overflow-y: auto;">
            ${(resume.evidence_items || []).map((ev, idx) => {
              const score = ev.similarity_score != null ? (ev.similarity_score <= 1.0 ? ev.similarity_score * 100 : ev.similarity_score) : 100;
              return `
                <div style="padding: 0.75rem; border-bottom: 1px solid var(--border-color); font-size: 0.85rem;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <strong style="color: var(--primary-700);">[${ev.section || 'CLAIM'}] #${idx + 1}</strong>
                    <span class="badge badge-green" style="font-size: 0.75rem;">✓ Độ tin cậy: ${score.toFixed(0)}%</span>
                  </div>
                  <div style="color: var(--text-main); font-weight: 500;">${ev.claim_text}</div>
                  <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.3rem;">
                    📌 <em>Sự thật gốc: "${ev.original_fact || 'Hồ sơ ứng viên'}"</em>
                  </div>
                </div>
              `;
            }).join('') || '<div style="padding: 1rem; color: var(--text-subtle); text-align: center;">Không có dữ liệu bằng chứng.</div>'}
          </div>
        </div>
      </div>
    </div>
  `;
}

function copyCoverLetterText() {
  const textEl = document.getElementById('cover-letter-text');
  if (textEl) {
    navigator.clipboard.writeText(textEl.textContent.trim());
    showToast('Đã sao chép Cover Letter vào Clipboard!', 'success');
  }
}

// --- 5. Profile View ---
async function loadProfile() {
  try {
    const profile = await api.getProfile();
    state.profile = profile;

    document.getElementById('prof-full-name').value = profile.full_name || '';
    document.getElementById('prof-headline').value = profile.headline || '';
    document.getElementById('prof-email').value = profile.email || '';
    document.getElementById('prof-phone').value = profile.phone || '';
    document.getElementById('prof-location').value = profile.location || '';
    document.getElementById('prof-summary').value = profile.summary || '';
    document.getElementById('prof-target-roles').value = (profile.target_roles || []).join(', ');
    document.getElementById('prof-target-locations').value = (profile.target_locations || []).join(', ');
  } catch (err) {
    showToast(`Không thể tải hồ sơ: ${err.message}`, 'error');
  }
}

async function saveProfileChanges() {
  const payload = {
    full_name: document.getElementById('prof-full-name').value.trim(),
    headline: document.getElementById('prof-headline').value.trim(),
    email: document.getElementById('prof-email').value.trim(),
    phone: document.getElementById('prof-phone').value.trim(),
    location: document.getElementById('prof-location').value.trim(),
    summary: document.getElementById('prof-summary').value.trim(),
    target_roles: document.getElementById('prof-target-roles').value.split(',').map(s => s.trim()).filter(Boolean),
    target_locations: document.getElementById('prof-target-locations').value.split(',').map(s => s.trim()).filter(Boolean),
  };

  try {
    await api.updateProfile(payload);
    showToast('Hồ sơ ứng viên đã được lưu vào Database!', 'success');
  } catch (err) {
    showToast(`Lưu hồ sơ thất bại: ${err.message}`, 'error');
  }
}

async function syncProfileContext() {
  try {
    showToast('Đang đồng bộ từ context/candidate-profile.yaml & LaTeX template...', 'info');
    const res = await api.syncProfileFromContext();
    showToast(`Đã đồng bộ ${res.skills_imported} kỹ năng, ${res.experiences_imported} kinh nghiệm, ${res.projects_imported} dự án!`, 'success');
    loadProfile();
  } catch (err) {
    showToast(`Đồng bộ thất bại: ${err.message}`, 'error');
  }
}

// --- 6. Recommendations View ---
async function loadRecommendations() {
  const container = document.getElementById('recommendations-list');
  if (!container) return;

  container.innerHTML = '<div style="text-align: center; padding: 3rem;">Đang tải danh sách AI Recommendations...</div>';

  try {
    const recs = await api.getTopRecommendations(30);
    state.topRecommendations = recs;

    if (recs.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 4rem;">
          <h3>Chưa có bảng xếp hạng</h3>
          <p style="color: var(--text-subtle); margin-top: 0.5rem;">Hãy chạy Daily Batch để quét dữ liệu và xếp hạng ứng tuyển.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = recs.map((rec, idx) => {
      const scoreClass = rec.score >= 80 ? 'score-high' : rec.score >= 60 ? 'score-med' : 'score-low';
      const jobTitle = rec.title || rec.job_title || 'Software Position';
      const sourceBadge = rec.source_url
        ? `<a href="${rec.source_url}" target="_blank" class="badge badge-outline" style="text-decoration: none; font-size: 0.8rem;" onclick="event.stopPropagation();" title="Mở link bài đăng gốc">🌐 ${rec.source ? rec.source.toUpperCase() : 'Tin gốc'} ↗</a>`
        : '';

      return `
        <div class="card card-hover" style="margin-bottom: 1rem; cursor: pointer;" onclick="openJobDetailModal('${rec.job_id}')">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="display: flex; gap: 1rem; align-items: center;">
              <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary-300); width: 32px;">#${idx + 1}</div>
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                  <h3 style="font-size: 1.15rem; margin-bottom: 0.2rem;">${jobTitle}</h3>
                  ${sourceBadge}
                </div>
                <div style="color: var(--primary-700); font-weight: 600; font-size: 0.9rem;">
                  ${rec.company_name} • <span style="color: var(--text-muted); font-weight: 450;">${rec.location || 'Vietnam'} (${rec.work_mode})</span>
                </div>
              </div>
            </div>
            <div class="score-badge ${scoreClass}" style="font-size: 1.15rem; padding: 0.4rem 0.9rem;">
              ${rec.score.toFixed(0)}%
            </div>
          </div>

          <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <span class="badge ${rec.eligibility === 'ELIGIBLE' ? 'badge-green' : 'badge-amber'}">${rec.eligibility}</span>
              ${rec.source_url ? `<a href="${rec.source_url}" target="_blank" style="font-size: 0.8rem; color: var(--primary-600); text-decoration: underline;" onclick="event.stopPropagation();">Xem bài đăng tuyển dụng gốc ↗</a>` : ''}
            </div>
            <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openJobDetailModal('${rec.job_id}')">Phân tích & May đo CV →</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger); padding: 2rem;">Lỗi tải đề xuất: ${err.message}</div>`;
  }
}

// --- 7. Application Tracker View ---
async function loadApplications() {
  const container = document.getElementById('applications-table-body');
  if (!container) return;

  container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem;">Đang tải danh sách đơn ứng tuyển...</td></tr>';

  try {
    const apps = await api.getApplications(1, 50);
    state.applications = apps;

    if (apps.length === 0) {
      container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-subtle);">Chưa có đơn ứng tuyển nào được nộp.</td></tr>';
      return;
    }

    container.innerHTML = apps.map(app => {
      let statusBadge = 'badge-blue';
      if (app.status === 'SENT') statusBadge = 'badge-green';
      if (app.status === 'INTERVIEW') statusBadge = 'badge-amber';
      if (app.status === 'REJECTED') statusBadge = 'badge-red';

      return `
        <tr>
          <td><strong>${app.subject || 'Application Submission'}</strong></td>
          <td>${app.channel}</td>
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
    container.innerHTML = `<tr><td colspan="6" style="color: var(--danger); padding: 2rem;">Lỗi tải đơn ứng tuyển: ${err.message}</td></tr>`;
  }
}

async function changeApplicationStatus(appId, newStatus) {
  try {
    await api.updateApplicationStatus(appId, newStatus);
    showToast(`Đã chuyển trạng thái sang ${newStatus}!`, 'success');
  } catch (err) {
    showToast(`Không thể cập nhật trạng thái: ${err.message}`, 'error');
  }
}

// Initial Batch Trigger
async function triggerDailyBatch() {
  try {
    showToast('Đang kích hoạt quy trình quét tự động hàng ngày...', 'info');
    const summary = await api.triggerDailyBatch(15);
    showToast(`Quét hoàn tất: ${summary.ingestion?.created || 0} tin mới, ${summary.matching?.total_scored || 0} tin đã tính điểm!`, 'success');
    loadDashboard();
  } catch (err) {
    showToast(`Lỗi chạy batch: ${err.message}`, 'error');
  }
}

// --- 8. File Upload & Dynamic Ingestion ---
async function handleResumeFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  const statusText = document.getElementById('upload-status-text');
  if (statusText) {
    statusText.textContent = `⏳ Đang tải lên và phân tích ${file.name}...`;
  }
  showToast(`Đang phân tích tệp ${file.name}...`, 'info');

  try {
    const res = await api.uploadResumeFile(file);
    if (statusText) {
      statusText.textContent = `✅ Đã tải lên và nạp hồ sơ thành công từ ${file.name}!`;
    }
    showToast(`Đã phân tích ${res.skills_imported} kỹ năng, ${res.projects_imported} dự án, ${res.experiences_imported} kinh nghiệm!`, 'success');
    
    // Tải lại dữ liệu Profile lên UI
    loadProfile();
  } catch (err) {
    if (statusText) {
      statusText.textContent = `❌ Tải lên thất bại: ${err.message}`;
    }
    showToast(`Lỗi tải lên tệp: ${err.message}`, 'error');
  }
}

// --- 9. System Administration & Database Purge ---
async function confirmPurgeDatabase(scope, description) {
  const promptMessage = `⚠️ CẢNH BÁO: Bạn đang yêu cầu thực thi:\n"${description}" (Phạm vi: ${scope})\n\nBạn có chắc chắn muốn xóa không? Thao tác này KHÔNG THỂ HOÀN TÁC!`;
  if (!confirm(promptMessage)) {
    return;
  }

  try {
    showToast(`Đang thực thi xóa dữ liệu phạm vi '${scope}'...`, 'warning');
    const report = await api.purgeDatabase(scope, true);
    showToast(`Thao tác hoàn tất: ${report.message}`, 'success');
    
    // Refresh views based on scope
    if (scope === 'all' || scope === 'jobs_and_tailoring') {
      state.jobs = [];
      state.topRecommendations = [];
      state.selectedResume = null;
      loadDashboard();
      if (scope === 'all') loadProfile();
    } else if (scope === 'tailoring_only') {
      state.selectedResume = null;
      const resumeContainer = document.getElementById('resume-workspace-content');
      if (resumeContainer) {
        resumeContainer.innerHTML = `
          <div class="card empty-state-card">
            <div class="empty-state-icon">📄</div>
            <h3>Toàn bộ dữ liệu Tailored Resume đã được làm trống</h3>
            <p class="empty-state-text">Bạn có thể chọn công việc trong <strong>Job Explorer</strong> để tạo bản CV may đo mới.</p>
            <button class="btn btn-primary" onclick="navigateTo('jobs')">Khám phá công việc →</button>
          </div>
        `;
      }
    }
  } catch (err) {
    showToast(`Lỗi dọn dẹp Database: ${err.message}`, 'error');
  }
}

async function confirmResetDemo() {
  const promptMessage = `🔄 BẠN CÓ CHẮC CHẮN MUỐN RESET DEMO?\n\nThao tác này sẽ:\n1. Xóa toàn bộ dữ liệu hiện tại\n2. Nạp lại Từ điển Canonical Skills (180+ kỹ năng)\n3. Đồng bộ lại Hồ sơ ứng viên từ context.example/\n\nTiếp tục?`;
  if (!confirm(promptMessage)) {
    return;
  }

  try {
    showToast('Đang khôi phục toàn bộ hệ thống về trạng thái mẫu ban đầu...', 'info');
    const res = await api.resetDemo();
    showToast(`Khôi phục thành công: ${res.message}`, 'success');
    loadDashboard();
    loadProfile();
  } catch (err) {
    showToast(`Lỗi reset demo: ${err.message}`, 'error');
  }
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Setup Navigation listeners
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const view = link.dataset.view;
      if (view) navigateTo(view);
    });
  });

  // Setup Search Listeners
  const searchInput = document.getElementById('search-job-input');
  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(loadJobs, 400);
    });
  }

  // Setup Drag & Drop for Dropzone
  const dropzone = document.getElementById('resume-dropzone');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        const fileInput = document.getElementById('resume-file-input');
        if (fileInput) {
          fileInput.files = files;
          handleResumeFileUpload({ target: { files } });
        }
      }
    });
  }

  // Load default view
  navigateTo('dashboard');
});

