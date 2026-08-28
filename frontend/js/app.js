/**
 * Job Hunter Platform — Enterprise SaaS Main Application Controller
 * Features: State management, Lucide icon triggers, Skeleton loaders, Multi-depth Job Scanner,
 * Manual JD Ingestion, Deterministic 7-Signal Matching, LaTeX/PDF Resume Workspace, and Application Tracker.
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

// UI Helper: Refresh Lucide Icons safely
function refreshIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// UI Helper: Toast Notifications (No Emojis, Standard Lucide Icons)
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle-2';
  if (type === 'error' || type === 'danger') iconName = 'alert-circle';
  if (type === 'warning') iconName = 'alert-triangle';

  toast.innerHTML = `
    <i data-lucide="${iconName}" class="icon-sm"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  refreshIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// 7 Valid Sidebar Views / Routes
const VALID_VIEWS = ['dashboard', 'jobs', 'recommendations', 'resume', 'applications', 'profile', 'system'];

// Router & View Switching (HTML5 History API)
function navigateTo(viewName, pushState = true) {
  const targetView = VALID_VIEWS.includes(viewName) ? viewName : 'dashboard';
  state.activeView = targetView;
  
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.dataset.view === targetView) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  document.querySelectorAll('.view-section').forEach(view => {
    if (view.id === `view-${targetView}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  // Update header title
  const titleMap = {
    dashboard: 'Tổng quan Dashboard',
    jobs: 'Khám phá & Tìm kiếm việc làm',
    recommendations: 'Đề xuất việc làm phù hợp',
    profile: 'Hồ sơ Ứng viên & Nguồn tham chiếu gốc',
    resume: 'Không gian Hồ sơ tạo thiết kế & Xác thực',
    applications: 'Quản lý & Theo dõi đơn nộp',
    system: 'Hệ thống & Cơ sở dữ liệu',
  };
  const headerTitle = document.getElementById('header-title-text');
  if (headerTitle) {
    headerTitle.textContent = titleMap[targetView] || 'Job Hunter Platform';
  }

  // Update browser URL (HTML5 History API)
  if (pushState) {
    const targetPath = targetView === 'dashboard' ? '/dashboard' : `/${targetView}`;
    const currentPath = window.location.pathname;
    if (currentPath !== targetPath && !(targetView === 'dashboard' && currentPath === '/')) {
      window.history.pushState({ view: targetView }, '', targetPath);
    }
  }

  // Trigger data loader for view
  if (targetView === 'dashboard') loadDashboard();
  if (targetView === 'jobs') loadJobs();
  if (targetView === 'recommendations') loadRecommendations();
  if (targetView === 'profile') loadProfile();
  if (targetView === 'applications') loadApplications();
  if (targetView === 'resume' && state.selectedResume) renderResumeWorkspace(state.selectedResume);
  if (targetView === 'system') loadSystemView();

  refreshIcons();
}


// Formatters
function formatCurrency(val, currency = 'USD') {
  if (!val) return 'Thương lượng';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(val);
}

function formatDate(dateStr) {
  if (!dateStr) return 'Gần đây';
  return new Date(dateStr).toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function getCompanyMonogram(companyName) {
  if (!companyName) return 'JH';
  const parts = companyName.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return companyName.slice(0, 2).toUpperCase();
}

function formatSourceBadge(source, sourceUrl) {
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
      <a href="${sourceUrl}" target="_blank" class="badge badge-outline" onclick="event.stopPropagation();" title="Mở bài đăng tuyển dụng gốc">
        <i data-lucide="${iconName}" class="icon-sm"></i>
        <span>${label}</span>
        <i data-lucide="external-link" class="icon-sm" style="width: 12px; height: 12px;"></i>
      </a>
    `;
  }
  return `
    <span class="badge badge-gray">
      <i data-lucide="${iconName}" class="icon-sm"></i>
      <span>${label}</span>
    </span>
  `;
}

// --- 1. Dashboard View ---
async function loadDashboard() {
  renderDashboardSkeleton();

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

function renderDashboardSkeleton() {
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

// --- 2. Jobs Explorer View ---
async function loadJobs() {
  const keyword = document.getElementById('search-job-input')?.value || '';
  const work_mode = document.getElementById('filter-work-mode')?.value || '';
  const level = document.getElementById('filter-level')?.value || '';
  const location = document.getElementById('filter-location')?.value || '';
  const source = document.getElementById('filter-source')?.value || '';

  renderJobsGridSkeleton();

  try {
    const res = await api.getJobs({ keyword, work_mode, level, location, source, page_size: 50 });
    state.jobs = res.items || [];
    renderJobsGrid(state.jobs);
  } catch (err) {
    showToast(`Không thể tải danh sách việc làm: ${err.message}`, 'error');
  }
}

function renderJobsGridSkeleton() {
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

function renderJobsGrid(jobs) {
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
          <button class="btn btn-outline btn-sm" onclick="document.getElementById('search-job-input').value=''; loadJobs();">
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
                <h3 class="job-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${job.title}</h3>
                <div class="job-company">${job.company_name || 'Công ty Tuyển dụng'}</div>
              </div>
            </div>
            <div style="display: flex; gap: 0.35rem; align-items: center; flex-shrink: 0;">
              ${sourceBadge}
            </div>
          </div>

          <div class="job-meta-tags">
            <span class="badge badge-gray">
              <i data-lucide="map-pin" class="icon-sm"></i>
              <span>${job.location || 'Vietnam'}</span>
            </span>
            <span class="badge badge-blue">
              <i data-lucide="briefcase" class="icon-sm"></i>
              <span>${job.level || 'All Levels'}</span>
            </span>
            <span class="badge badge-gray">
              <i data-lucide="home" class="icon-sm"></i>
              <span>${job.work_mode || 'ONSITE'}</span>
            </span>
            ${hasSalary ? `
              <span class="badge badge-green">
                <i data-lucide="dollar-sign" class="icon-sm"></i>
                <span>${salaryText}</span>
              </span>
            ` : ''}
          </div>

          <div class="job-description-snippet">
            ${job.description ? job.description.replace(/<[^>]*>?/gm, '') : 'Không có mô tả chi tiết.'}
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

// --- 3. Job Detail Modal & Intelligence Breakdown ---
async function openJobDetailModal(jobId) {
  const modalBackdrop = document.getElementById('job-detail-modal');
  if (!modalBackdrop) return;

  modalBackdrop.classList.add('active');
  document.getElementById('modal-job-title').textContent = 'Đang tải thông tin chi tiết...';
  document.getElementById('modal-job-body').innerHTML = `
    <div style="text-align: center; padding: 3rem;">
      <div class="spinner spinner-primary" style="width: 28px; height: 28px; margin-bottom: 0.75rem;"></div>
      <div style="color: var(--text-muted); font-size: 0.88rem;">Đang tải dữ liệu tuyển dụng và đối soát điểm tương thích...</div>
    </div>
  `;
  document.getElementById('modal-job-footer').innerHTML = '';

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
                ${match.explanation_text || 'Chưa có phân tích chi tiết.'}
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
        ${js.skill?.canonical_name || 'Skill'} ${js.is_required ? '<i data-lucide="check" class="icon-sm" style="width: 11px; height: 11px;"></i>' : ''}
      </span>
    `).join('');

    document.getElementById('modal-job-body').innerHTML = `
      ${matchSectionHtml}

      <div style="margin-bottom: 1.25rem;">
        <h4 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem;">Thông tin tổng quan</h4>
        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
          <span class="badge badge-blue">
            <i data-lucide="building" class="icon-sm"></i>
            <span>${job.company_name}</span>
          </span>
          <span class="badge badge-gray">
            <i data-lucide="map-pin" class="icon-sm"></i>
            <span>${job.location || 'Vietnam'}</span>
          </span>
          <span class="badge badge-gray">
            <i data-lucide="briefcase" class="icon-sm"></i>
            <span>${job.level || 'All Levels'}</span>
          </span>
          <span class="badge badge-gray">
            <i data-lucide="home" class="icon-sm"></i>
            <span>${job.work_mode || 'ONSITE'}</span>
          </span>
          ${job.contact_email ? `
            <span class="badge badge-green">
              <i data-lucide="mail" class="icon-sm"></i>
              <span>${job.contact_email}</span>
            </span>
          ` : ''}
          ${job.source_url ? `
            <a href="${job.source_url}" target="_blank" class="badge badge-outline" style="text-decoration: none;" title="Mở link bài đăng gốc">
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
        <div style="background-color: var(--bg-muted); padding: 1rem; border-radius: var(--radius-md); font-size: 0.85rem; line-height: 1.6; max-height: 280px; overflow-y: auto; border: 1px solid var(--border-default); white-space: pre-wrap;">
          ${job.description || 'Không có mô tả.'}
        </div>
      </div>
    `;

    // Action buttons in modal footer
    const footerEl = document.getElementById('modal-job-footer');
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

    refreshIcons();
  } catch (err) {
    document.getElementById('modal-job-body').innerHTML = `
      <div style="color: var(--danger-700); padding: 2rem; text-align: center;">
        <i data-lucide="alert-circle" class="icon-lg" style="margin-bottom: 0.5rem;"></i>
        <div>Lỗi tải thông tin chi tiết: ${err.message}</div>
      </div>
    `;
    refreshIcons();
  }
}

function closeJobDetailModal() {
  const modalBackdrop = document.getElementById('job-detail-modal');
  if (modalBackdrop) modalBackdrop.classList.remove('active');
}

async function triggerCalculateMatch(jobId) {
  try {
    showToast('Đang tính toán điểm tương thích...', 'info');
    await api.calculateMatch(jobId, true);
    showToast('Đã tính toán thành công!', 'success');
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
    showToast(`Không thể lưu tin: ${err.message}`, 'error');
  }
}

// --- 4. Resume Workspace View ---
async function startResumeTailoring(jobId, forceRegenerate = false, customTone = 'professional_and_humble') {
  closeJobDetailModal();
  navigateTo('resume');

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
          <p class="empty-state-text">${err.message}</p>
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

async function deleteTailoredResumeForJob(jobId) {
  if (!confirm('Bạn có chắc chắn muốn xóa bản CV tạo thiết kế và Cover Letter này để làm mới từ đầu?')) {
    return;
  }

  try {
    showToast('Đang xóa bản CV và Cover Letter...', 'info');
    await api.deleteTailoredResume(jobId);
    showToast('Đã xóa thành công bản CV tạo thiết kế!', 'success');
    
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

function switchResumePreviewTab(tab) {
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
    if (viewPdf) viewPdf.style.display = 'block';
  }
}

async function saveAndRecompileResume(resumeId) {
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

function copyResumeLatex() {
  const editor = document.getElementById('resume-tex-editor');
  if (editor) {
    navigator.clipboard.writeText(editor.value);
    showToast('Đã sao chép mã nguồn LaTeX vào Clipboard!', 'success');
  }
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function convertMarkdownToCleanEmail(md, candidateName = '', jobTitle = '', companyName = '') {
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

function renderCoverLetterHtml(md) {
  if (!md) return '<p style="color: var(--text-muted); padding: 0.5rem 0;">Chưa có dữ liệu Cover Letter.</p>';

  let text = md;
  // Bỏ phần header metadata nếu có
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

  // Phân tích từng dòng để xử lý Header, Bullet list, Paragraphs
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

    // Header đề mục (### hoặc ## hoặc #)
    if (line.startsWith('#')) {
      if (inList) {
        htmlParts.push('</ul>');
        inList = false;
      }
      const headerText = line.replace(/^#+\s*/, '').replace(/:$/, '');
      htmlParts.push(`<h5>${escapeHtml(headerText)}</h5>`);
      continue;
    }

    // Bullet point (- hoặc * hoặc •)
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

    // Normal text paragraph
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

function copyCoverLetterCleanEmail() {
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

function copyCoverLetterSubject() {
  const subjectEl = document.getElementById('cover-letter-subject-text');
  if (subjectEl) {
    const text = subjectEl.textContent.trim();
    navigator.clipboard.writeText(text);
    showToast('✅ Đã sao chép Tiêu đề Email vào Clipboard!', 'success');
  }
}

function openCoverLetterInMailClient() {
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

async function renderResumeWorkspace(resume) {
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
  const sourceUrl = job ? job.source_url : null;

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
    <!-- Top Job Details Banner (Thay thế hoàn toàn phần Mục tiêu) -->
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

    <!-- Action Toolbar (Tái tạo, Xóa, Nộp ứng tuyển) -->
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

    <!-- Main 2-Column Grid (Căn chỉnh đối xứng ngang và rộng bằng nhau 50% - 50%) -->
    <div class="ws-two-column-grid">
      <!-- Left Column: Single Unified Card for LaTeX Editor & PDF Preview -->
      <div class="card ws-col" style="display: flex; flex-direction: column;">
        <!-- Header & Action Row -->
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

        <!-- Tab Switcher Bar -->
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

        <!-- Tab 1: LaTeX Editor View (Default) -->
        <div id="resume-tab-tex">
          <textarea id="resume-tex-editor" style="width: 100%; height: 560px; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.82rem; line-height: 1.5; padding: 0.75rem; border-radius: var(--radius-md); background: var(--bg-muted); color: var(--text-main); border: 1px solid var(--border-default); resize: vertical; white-space: pre;" spellcheck="false">${(resume.latex_source || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
        </div>

        <!-- Tab 2: PDF Preview (Hidden by default) -->
        <div id="resume-tab-pdf" style="height: 560px; border-radius: var(--radius-md); overflow: hidden; display: none; border: 1px solid var(--border-default);">
          <iframe src="${pdfInlineUrl}" style="width: 100%; height: 100%; border: none;"></iframe>
        </div>
      </div>

      <!-- Right Column: Cover Letter & Evidence Map -->
      <div class="ws-col" style="display: flex; flex-direction: column; gap: 1.25rem;">
        <!-- Enhanced Cover Letter Card (Clean Formatted View Only) -->
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

          <!-- Suggested Email Subject Banner -->
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

          <!-- Clean Formatted Letter Content -->
          <div id="cl-view-formatted" class="cover-letter-paper" style="max-height: 290px;">
            ${coverLetterHtml}
          </div>
        </div>

        <!-- Evidence Map Card -->
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

// --- 5. Candidate Profile View ---
async function loadProfile() {
  try {
    const profile = await api.getProfile();
    state.candidateProfile = profile;

    if (profile.full_name) {
      const nameEl = document.getElementById('sidebar-user-name');
      if (nameEl) nameEl.textContent = profile.full_name;
    }
    if (profile.email) {
      const emailEl = document.getElementById('sidebar-user-email');
      if (emailEl) emailEl.textContent = profile.email;
    }

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val || '';
    };

    setVal('prof-full-name', profile.full_name);
    setVal('prof-headline', profile.headline);
    setVal('prof-email', profile.email);
    setVal('prof-phone', profile.phone);
    setVal('prof-location', profile.location);
    setVal('prof-summary', profile.summary);
    setVal('prof-target-roles', (profile.target_roles || []).join(', '));
    setVal('prof-target-locations', (profile.target_locations || []).join(', '));
  } catch (err) {
    showToast(`Không thể tải hồ sơ: ${err.message}`, 'error');
  }
}

async function saveProfileChanges() {
  const payload = {
    full_name: document.getElementById('prof-full-name')?.value.trim() || '',
    headline: document.getElementById('prof-headline')?.value.trim() || '',
    email: document.getElementById('prof-email')?.value.trim() || '',
    phone: document.getElementById('prof-phone')?.value.trim() || '',
    location: document.getElementById('prof-location')?.value.trim() || '',
    summary: document.getElementById('prof-summary')?.value.trim() || '',
    target_roles: (document.getElementById('prof-target-roles')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
    target_locations: (document.getElementById('prof-target-locations')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
  };

  try {
    await api.updateProfile(payload);
    showToast('Thông tin hồ sơ ứng viên đã được lưu thành công!', 'success');
    loadProfile();
  } catch (err) {
    showToast(`Lưu hồ sơ thất bại: ${err.message}`, 'error');
  }
}

async function syncProfileContext() {
  try {
    showToast('Đang đồng bộ hồ sơ từ context file...', 'info');
    const res = await api.syncProfileFromContext();
    showToast(`Đã đồng bộ ${res.skills_imported} kỹ năng, ${res.experiences_imported} kinh nghiệm, ${res.projects_imported} dự án!`, 'success');
    loadProfile();
  } catch (err) {
    showToast(`Đồng bộ thất bại: ${err.message}`, 'error');
  }
}

async function handleResumeFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  const statusText = document.getElementById('upload-status-text');
  if (statusText) {
    statusText.textContent = `Đang tải lên và trích xuất ${file.name}...`;
  }
  showToast(`Đang phân tích tệp ${file.name}...`, 'info');

  try {
    const res = await api.uploadResumeFile(file);
    if (statusText) {
      statusText.textContent = `Đã phân tích và cập nhật hồ sơ từ ${file.name}!`;
    }
    showToast(`Đã nạp ${res.skills_imported} kỹ năng, ${res.projects_imported} dự án, ${res.experiences_imported} kinh nghiệm!`, 'success');
    loadProfile();
  } catch (err) {
    if (statusText) {
      statusText.textContent = `Tải lên thất bại: ${err.message}`;
    }
    showToast(`Lỗi tải lên tệp: ${err.message}`, 'error');
  }
}

// --- 6. Recommendations View ---
async function loadRecommendations() {
  const container = document.getElementById('recommendations-list');
  if (!container) return;

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
                  <h3 style="font-size: 1rem; font-weight: 600; margin: 0;">${jobTitle}</h3>
                  ${sourceBadge}
                </div>
                <div style="color: var(--primary-700); font-weight: 500; font-size: 0.84rem; margin-top: 0.2rem;">
                  ${companyName} • <span style="color: var(--text-muted);">${rec.location || 'Vietnam'} (${rec.work_mode || 'Flexible'})</span>
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
              ${rec.recommendation ? `<span style="font-size: 0.78rem; color: var(--text-muted);">${rec.recommendation}</span>` : ''}
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
        <div>Lỗi tải danh sách đề xuất: ${err.message}</div>
      </div>
    `;
    refreshIcons();
  }
}

function renderRecommendationsSkeleton() {
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

// --- 7. Application Tracker View ---
async function loadApplications() {
  const container = document.getElementById('applications-table-body');
  if (!container) return;

  container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">Đang tải danh sách đơn ứng tuyển...</td></tr>';

  try {
    const apps = await api.getApplications(1, 50);
    state.applications = apps;

    if (apps.length === 0) {
      container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-muted);">Chưa có đơn ứng tuyển nào được ghi nhận.</td></tr>';
      return;
    }

    container.innerHTML = apps.map(app => {
      let statusBadge = 'badge-blue';
      if (app.status === 'SENT') statusBadge = 'badge-green';
      if (app.status === 'INTERVIEW') statusBadge = 'badge-amber';
      if (app.status === 'REJECTED') statusBadge = 'badge-red';

      return `
        <tr>
          <td><strong>${app.subject || 'Đơn ứng tuyển công việc'}</strong></td>
          <td>${app.channel || 'EMAIL'}</td>
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
    container.innerHTML = `<tr><td colspan="6" style="color: var(--danger-700); padding: 2rem; text-align: center;">Lỗi tải đơn ứng tuyển: ${err.message}</td></tr>`;
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

function prepareApplicationModal(jobId) {
  showToast('Tính năng nộp hồ sơ tự động đang sẵn sàng cho công việc này.', 'info');
}

// --- 8. Job Scanner Modal Controller ---
function openScanJobsModal() {
  const modal = document.getElementById('scan-jobs-modal');
  if (!modal) return;
  modal.classList.add('active');

  const progressBox = document.getElementById('scan-progress-box');
  const resultBox = document.getElementById('scan-result-box');
  const btnStart = document.getElementById('btn-start-scan');

  if (progressBox) progressBox.style.display = 'none';
  if (resultBox) {
    resultBox.style.display = 'none';
    resultBox.innerHTML = '';
  }
  if (btnStart) {
    btnStart.disabled = false;
    btnStart.innerHTML = '<i data-lucide="play" class="icon-sm"></i><span>Bắt đầu Quét dữ liệu</span>';
  }
  refreshIcons();
}

function closeScanJobsModal() {
  const modal = document.getElementById('scan-jobs-modal');
  if (modal) modal.classList.remove('active');
}

function toggleCustomLimitInput(isCustom) {
  const container = document.getElementById('custom-limit-container');
  if (container) {
    container.style.display = isCustom ? 'block' : 'none';
  }
}

async function startConfiguredJobScan() {
  const selectedRadio = document.querySelector('input[name="scan-depth-mode"]:checked');
  let limit = 20;

  if (selectedRadio) {
    if (selectedRadio.value === 'custom') {
      const customInput = document.getElementById('custom-scan-limit');
      limit = parseInt(customInput?.value, 10) || 50;
      if (limit < 1) limit = 1;
      if (limit > 500) limit = 500;
    } else {
      limit = parseInt(selectedRadio.value, 10) || 20;
    }
  }

  const btnStart = document.getElementById('btn-start-scan');
  const progressBox = document.getElementById('scan-progress-box');
  const progressStatus = document.getElementById('scan-progress-status');
  const progressDetail = document.getElementById('scan-progress-detail');
  const resultBox = document.getElementById('scan-result-box');

  if (btnStart) {
    btnStart.disabled = true;
    btnStart.innerHTML = '<div class="spinner"></div><span>Đang quét dữ liệu...</span>';
  }
  if (progressBox) progressBox.style.display = 'block';
  if (resultBox) resultBox.style.display = 'none';

  if (progressStatus) {
    progressStatus.textContent = `Đang quét dữ liệu (Giới hạn: ${limit} tin/nguồn)...`;
  }
  if (progressDetail) {
    progressDetail.textContent = 'Hệ thống đang duyệt song song ITViec, TopCV, CareerLink, Remotive và tính toán điểm tương thích...';
  }

  const startTime = Date.now();
  showToast(`Đang bắt đầu quét dữ liệu đa nguồn (${limit} tin/nguồn)...`, 'info');

  try {
    const summary = await api.triggerDailyBatch(limit);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    if (progressBox) progressBox.style.display = 'none';
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.innerHTML = '<i data-lucide="refresh-cw" class="icon-sm"></i><span>Quét lại</span>';
    }

    if (resultBox) {
      resultBox.style.display = 'block';
      const createdCount = summary.new_jobs_created ?? summary.ingestion?.created ?? 0;
      const totalFetched = summary.total_fetched ?? summary.ingestion?.total_fetched ?? 0;
      const totalScored = summary.total_matches_evaluated ?? summary.matching?.total_scored ?? 0;
      const strongCount = summary.strong_matches_count ?? 0;
      const goodCount = summary.good_matches_count ?? 0;

      resultBox.innerHTML = `
        <div style="background: var(--bg-muted); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 1.15rem;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
            <strong style="color: var(--success-700); font-size: 0.95rem; display: flex; align-items: center; gap: 0.4rem;">
              <i data-lucide="check-circle-2" class="icon-sm"></i>
              <span>Quét hoàn tất thành công</span>
            </strong>
            <span style="font-size: 0.78rem; color: var(--text-muted);">Thời gian: ${elapsed}s</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.65rem; margin-bottom: 0.85rem;">
            <div style="background: var(--bg-surface); padding: 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-default); text-align: center;">
              <div style="font-size: 1.25rem; font-weight: 700; color: var(--primary-700);">${totalFetched}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">Tin đã thu thập</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-default); text-align: center;">
              <div style="font-size: 1.25rem; font-weight: 700; color: var(--success-700);">${createdCount}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">Tin mới vào DB</div>
            </div>
            <div style="background: var(--bg-surface); padding: 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-default); text-align: center;">
              <div style="font-size: 1.25rem; font-weight: 700; color: var(--warning-700);">${totalScored}</div>
              <div style="font-size: 0.72rem; color: var(--text-muted);">Đã tính 7 chỉ số</div>
            </div>
          </div>

          <div style="font-size: 0.82rem; color: var(--text-body); margin-bottom: 0.75rem;">
            Phát hiện <strong>${strongCount}</strong> tin rất phù hợp và <strong>${goodCount}</strong> tin tiềm năng.
          </div>

          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-primary btn-sm" style="flex: 1;" onclick="closeScanJobsModal(); navigateTo('jobs');">
              <i data-lucide="briefcase" class="icon-sm"></i>
              <span>Xem danh sách việc làm</span>
            </button>
            <button class="btn btn-outline btn-sm" onclick="closeScanJobsModal(); loadDashboard();">
              <span>Xem Dashboard</span>
            </button>
          </div>
        </div>
      `;
    }

    showToast(`Quét hoàn tất: ${summary.new_jobs_created || 0} tin mới, ${summary.total_matches_evaluated || 0} tin đã tính điểm!`, 'success');
    loadDashboard();
    refreshIcons();
  } catch (err) {
    if (progressBox) progressBox.style.display = 'none';
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.innerHTML = '<i data-lucide="refresh-cw" class="icon-sm"></i><span>Thử lại</span>';
    }
    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="background: var(--danger-50); border: 1px solid var(--danger-100); border-radius: var(--radius-md); padding: 0.85rem; color: var(--danger-700); font-size: 0.85rem;">
          <strong>Lỗi quét dữ liệu:</strong> ${err.message}
        </div>
      `;
    }
    showToast(`Lỗi chạy quét dữ liệu: ${err.message}`, 'error');
    refreshIcons();
  }
}

// --- 9. Manual JD Ingestion Controller ---
let currentManualIngestMode = 'text';

function openManualIngestModal() {
  const modal = document.getElementById('manual-ingest-modal');
  if (!modal) return;

  const textInput = document.getElementById('manual-raw-text');
  const urlInput = document.getElementById('manual-url-input');
  const resultBox = document.getElementById('manual-ingest-result');

  if (textInput) textInput.value = '';
  if (urlInput) urlInput.value = '';
  if (resultBox) {
    resultBox.style.display = 'none';
    resultBox.innerHTML = '';
  }

  switchManualIngestTab('text');
  modal.classList.add('active');
  refreshIcons();
}

function closeManualIngestModal() {
  const modal = document.getElementById('manual-ingest-modal');
  if (modal) modal.classList.remove('active');
}

function switchManualIngestTab(mode) {
  currentManualIngestMode = mode;
  const btnText = document.getElementById('tab-btn-text');
  const btnUrl = document.getElementById('tab-btn-url');
  const contentText = document.getElementById('tab-content-text');
  const contentUrl = document.getElementById('tab-content-url');

  if (mode === 'text') {
    if (btnText) btnText.classList.add('active');
    if (btnUrl) btnUrl.classList.remove('active');
    if (contentText) contentText.classList.add('active');
    if (contentUrl) contentUrl.classList.remove('active');
  } else {
    if (btnText) btnText.classList.remove('active');
    if (btnUrl) btnUrl.classList.add('active');
    if (contentText) contentText.classList.remove('active');
    if (contentUrl) contentUrl.classList.add('active');
  }
}

async function submitManualJobIngest() {
  const btnSubmit = document.getElementById('btn-submit-manual-ingest');
  const resultBox = document.getElementById('manual-ingest-result');
  const autoMatch = document.getElementById('manual-auto-match')?.checked ?? true;

  let rawText = '';
  let url = '';

  if (currentManualIngestMode === 'text') {
    rawText = document.getElementById('manual-raw-text')?.value?.trim() || '';
    if (rawText.length < 30) {
      showToast('Nội dung JD quá ngắn (cần tối thiểu 30 ký tự để trích xuất).', 'warning');
      return;
    }
  } else {
    url = document.getElementById('manual-url-input')?.value?.trim() || '';
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      showToast('Đường dẫn URL không hợp lệ (cần bắt đầu bằng http:// hoặc https://).', 'warning');
      return;
    }
  }

  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<div class="spinner"></div><span>Đang trích xuất & phân tích...</span>';
  }

  if (resultBox) {
    resultBox.style.display = 'block';
    resultBox.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; color: var(--text-muted);">
        <div class="spinner spinner-primary" style="margin-bottom: 0.5rem;"></div>
        <div>Đang phân tích cấu trúc bài đăng, trích xuất kỹ năng và tính điểm tương thích...</div>
      </div>
    `;
  }

  try {
    const payload = {
      mode: currentManualIngestMode,
      raw_text: currentManualIngestMode === 'text' ? rawText : null,
      url: currentManualIngestMode === 'url' ? url : null,
      auto_match: autoMatch,
    };

    const response = await api.ingestManualJob(payload);

    if (response.status === 'failed') {
      renderManualIngestError(response);
      showToast(response.message || 'Trích xuất tin thất bại.', 'error');
    } else {
      renderManualIngestSuccess(response);
      showToast(response.message || 'Đã nạp tin tuyển dụng thành công!', 'success');
      if (state.activeView === 'jobs') loadJobs();
      if (state.activeView === 'dashboard') loadDashboard();
    }
  } catch (err) {
    if (resultBox) {
      resultBox.innerHTML = `
        <div class="card" style="padding: 1rem; background-color: var(--danger-50); border-color: var(--danger-100);">
          <div style="color: var(--danger-700); font-weight: 600; margin-bottom: 0.35rem;">Lỗi khi nạp tin tuyển dụng</div>
          <p style="font-size: 0.84rem; color: var(--text-body);">${err.message || 'Đã xảy ra lỗi không xác định.'}</p>
        </div>
      `;
    }
    showToast(`Lỗi: ${err.message}`, 'error');
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<i data-lucide="play" class="icon-sm"></i><span>Phân tích & Nạp JD</span>';
      refreshIcons();
    }
  }
}

function renderManualIngestSuccess(res) {
  const resultBox = document.getElementById('manual-ingest-result');
  if (!resultBox) return;

  const job = res.job;
  const match = res.match;
  const meta = res.extraction_metadata || {};

  const statusBadge = res.status === 'created'
    ? '<span class="badge badge-green">Mới tạo</span>'
    : res.status === 'duplicate'
    ? '<span class="badge badge-amber">Đã tồn tại</span>'
    : '<span class="badge badge-gray">Thiếu trường</span>';

  const confidencePercent = Math.round((meta.overall_confidence || 0) * 100);
  const confidenceColor = confidencePercent >= 75 ? 'var(--success-600)' : confidencePercent >= 50 ? 'var(--warning-600)' : 'var(--danger-600)';

  let checklistHtml = '';
  if (meta.fields && meta.fields.length > 0) {
    checklistHtml = meta.fields.map(f => `
      <div class="field-item ${f.detected ? 'detected' : 'undetected'}">
        <i data-lucide="${f.detected ? 'check' : 'x'}" class="icon-sm" style="width: 12px; height: 12px;"></i>
        <span style="font-weight: 600; text-transform: capitalize;">${f.field}</span>
        <span style="font-size: 0.72rem; opacity: 0.75;">(${Math.round((f.confidence || 0) * 100)}%)</span>
      </div>
    `).join('');
  }

  resultBox.innerHTML = `
    <div class="card" style="background: var(--bg-surface); border: 1px solid var(--border-default); padding: 1.15rem;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
        <div>
          ${statusBadge}
          <h4 style="margin: 0.35rem 0 0.1rem 0; font-size: 1.05rem; color: var(--text-main);">${job ? job.title : 'Tin tuyển dụng'}</h4>
          <div style="font-size: 0.82rem; color: var(--text-muted);">${job ? job.company_name : ''} • ${job?.location || 'Vietnam'}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Độ tin cậy trích xuất</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: ${confidenceColor};">${confidencePercent}%</div>
        </div>
      </div>

      <div class="field-checklist-grid">
        ${checklistHtml}
      </div>

      ${match ? `
        <div style="background: var(--primary-50); border: 1px solid var(--primary-100); border-radius: var(--radius-md); padding: 0.85rem; margin-top: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <strong style="font-size: 0.88rem; color: var(--primary-900);">Điểm tương thích 7 chỉ số:</strong>
            <span style="font-size: 1.1rem; font-weight: 700; color: var(--primary-700);">${Math.round(match.score || 0)}/100</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-body);">${match.explanation_text || match.explanation || ''}</div>
        </div>
      ` : ''}

      <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; border-top: 1px solid var(--border-default); padding-top: 0.75rem;">
        ${job ? `
          <button class="btn btn-outline btn-sm" onclick="closeManualIngestModal(); openJobDetailModal('${job.id}')">
            <i data-lucide="eye" class="icon-sm"></i>
            <span>Xem chi tiết</span>
          </button>
          <button class="btn btn-primary btn-sm" onclick="closeManualIngestModal(); startResumeTailoring('${job.id}')">
            <i data-lucide="file-text" class="icon-sm"></i>
            <span>tạo thiết kế CV</span>
          </button>
        ` : ''}
      </div>
    </div>
  `;

  refreshIcons();
}

function renderManualIngestError(res) {
  const resultBox = document.getElementById('manual-ingest-result');
  if (!resultBox) return;

  resultBox.innerHTML = `
    <div class="card" style="background-color: var(--danger-50); border-color: var(--danger-100); padding: 1rem;">
      <div style="display: flex; align-items: center; gap: 0.4rem; color: var(--danger-700); font-weight: 600; margin-bottom: 0.35rem;">
        <i data-lucide="alert-circle" class="icon-sm"></i>
        <span>${res.message || 'Không thể trích xuất tin tuyển dụng.'}</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">
        Hãy thử dán nội dung văn bản đầy đủ hơn (tiêu đề, kỹ năng yêu cầu, mức lương hoặc thông tin liên hệ).
      </div>
    </div>
  `;

  refreshIcons();
}

// --- 10. System Administration Controllers ---
function loadSystemView() {
  const currentBase = api.getBaseUrl();
  const currentSource = api.getResolutionSource();

  const inputEl = document.getElementById('custom-api-base-input');
  if (inputEl) {
    inputEl.value = currentBase;
  }

  const sourceBadge = document.getElementById('api-source-badge');
  if (sourceBadge) {
    sourceBadge.textContent = `Nguồn: ${currentSource}`;
  }

  refreshIcons();
}

function saveCustomApiEndpoint() {
  const inputEl = document.getElementById('custom-api-base-input');
  const val = inputEl ? inputEl.value.trim() : '';

  if (!val) {
    showToast('Vui lòng nhập API URL hợp lệ (hoặc bấm Mặc định để xóa tùy biến).', 'warning');
    return;
  }

  api.setBaseUrl(val);
  showToast(`Đã lưu cấu hình API: ${api.getBaseUrl()}`, 'success');
  loadSystemView();
  testApiConnection();
}

function resetApiEndpoint() {
  api.resetBaseUrl();
  showToast(`Đã khôi phục API Endpoint về cấu hình mặc định: ${api.getBaseUrl()}`, 'info');
  loadSystemView();
  testApiConnection();
}

function setApiPreset(url) {
  const inputEl = document.getElementById('custom-api-base-input');
  if (inputEl) {
    inputEl.value = url;
  }
  saveCustomApiEndpoint();
}

async function testApiConnection() {
  const statusBadge = document.getElementById('api-health-status-badge');
  const resultBox = document.getElementById('api-health-result');
  const pingBtn = document.getElementById('btn-ping-api');

  if (statusBadge) {
    statusBadge.className = 'badge badge-outline';
    statusBadge.innerHTML = `<i data-lucide="loader" class="icon-spin"></i> Đang ping...`;
  }
  if (pingBtn) {
    pingBtn.disabled = true;
  }
  refreshIcons();

  const health = await api.checkHealth();

  if (pingBtn) {
    pingBtn.disabled = false;
  }

  if (health.healthy) {
    if (statusBadge) {
      statusBadge.className = 'badge badge-green';
      statusBadge.textContent = `Online (${health.latencyMs} ms)`;
    }

    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px;">
          <div><strong style="color: var(--color-text-primary);">Trạng thái API:</strong> <span style="color: var(--color-success); font-weight: 600;">Sẵn sàng (200 OK)</span></div>
          <div><strong style="color: var(--color-text-primary);">Độ trễ (Latency):</strong> <span>${health.latencyMs} ms</span></div>
          <div><strong style="color: var(--color-text-primary);">PostgreSQL DB:</strong> <span style="color: ${health.data?.components?.database === 'connected' ? 'var(--color-success)' : 'var(--color-danger)'}; font-weight: 600;">${health.data?.components?.database || 'connected'}</span></div>
          <div><strong style="color: var(--color-text-primary);">Redis Cache/Queue:</strong> <span style="color: ${health.data?.components?.redis === 'connected' ? 'var(--color-success)' : 'var(--color-warning)'}; font-weight: 600;">${health.data?.components?.redis || 'connected'}</span></div>
          <div><strong style="color: var(--color-text-primary);">Phiên bản Backend:</strong> <span>v${health.data?.version || '1.0.0'}</span></div>
          <div><strong style="color: var(--color-text-primary);">Môi trường:</strong> <span>${health.data?.environment || 'production'}</span></div>
        </div>
      `;
    }
    showToast(`Kết nối Backend thành công (${health.latencyMs} ms)`, 'success');
  } else {
    if (statusBadge) {
      statusBadge.className = 'badge badge-red';
      statusBadge.textContent = `Mất kết nối`;
    }

    if (resultBox) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="color: var(--color-danger);">
          <strong>Lỗi kết nối:</strong> ${health.error || 'Không thể liên lạc với máy chủ API.'}
          <div style="margin-top: 6px; font-size: 0.75rem; color: var(--color-text-muted);">
            Vui lòng kiểm tra lại URL API, trạng thái máy chủ Backend (Render/Koyeb/Localhost) hoặc cấu hình CORS.
          </div>
        </div>
      `;
    }
    showToast(`Không thể kết nối Backend: ${health.error}`, 'error');
  }

  refreshIcons();
}

async function confirmPurgeDatabase(scope, description) {
  const promptMessage = `XÁC NHẬN THỰC THI:\n"${description}" (Phạm vi: ${scope})\n\nThao tác này sẽ xóa dữ liệu và không thể hoàn tác. Bạn có chắc chắn muốn tiếp tục?`;
  if (!confirm(promptMessage)) return;

  try {
    showToast(`Đang thực thi xóa dữ liệu phạm vi '${scope}'...`, 'warning');
    const report = await api.purgeDatabase(scope, true);
    showToast(`Thao tác hoàn tất: ${report.message}`, 'success');
    
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
            <div class="empty-state-icon-box">
              <i data-lucide="trash-2" class="icon-lg"></i>
            </div>
            <h3 class="empty-state-title">Đã dọn dẹp toàn bộ dữ liệu tạo thiết kế</h3>
            <p class="empty-state-text">Bạn có thể chọn công việc trong mục Khám phá việc làm để tạo hồ sơ tạo thiết kế mới.</p>
            <button class="btn btn-primary btn-sm" onclick="navigateTo('jobs')">
              <i data-lucide="search" class="icon-sm"></i>
              <span>Khám phá việc làm</span>
            </button>
          </div>
        `;
        refreshIcons();
      }
    }
  } catch (err) {
    showToast(`Lỗi dọn dẹp Database: ${err.message}`, 'error');
  }
}

async function confirmResetDemo() {
  const promptMessage = `KHÔI PHỤC TRẠNG THÁI MẪU (RESET DEMO):\n\nThao tác này sẽ:\n1. Làm trống toàn bộ dữ liệu hiện tại\n2. Nạp lại Từ điển Canonical Skills (180+ kỹ năng)\n3. Đồng bộ lại Hồ sơ ứng viên từ context.example/\n\nTiếp tục?`;
  if (!confirm(promptMessage)) return;

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
  // Navigation Event Listeners
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const view = link.dataset.view;
      if (view) navigateTo(view);
    });
    link.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const view = link.dataset.view;
        if (view) navigateTo(view);
      }
    });
  });

  // Debounced Search Input
  const searchInput = document.getElementById('search-job-input');
  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(loadJobs, 350);
    });
  }

  // Resume Upload Dropzone
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

  // Handle Browser Back / Forward Buttons
  window.addEventListener('popstate', (e) => {
    const viewFromState = e.state?.view;
    if (viewFromState && VALID_VIEWS.includes(viewFromState)) {
      navigateTo(viewFromState, false);
    } else {
      const currentPath = window.location.pathname.replace(/^\/+|\/+$/g, '').toLowerCase();
      const targetView = VALID_VIEWS.includes(currentPath) ? currentPath : 'dashboard';
      navigateTo(targetView, false);
    }
  });

  // Initial load based on current browser URL pathname (e.g. /jobs, /recommendations, /resume,...)
  const pathSegment = window.location.pathname.replace(/^\/+|\/+$/g, '').toLowerCase();
  const initialView = VALID_VIEWS.includes(pathSegment) ? pathSegment : 'dashboard';
  navigateTo(initialView, false);
  refreshIcons();
});

