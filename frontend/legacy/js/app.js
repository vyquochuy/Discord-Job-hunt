/**
 * Job Hunter Platform - Main Application Entry Point (Modular ES Architecture)
 */

import { state } from './core/store.js';
import { api } from './api/index.js';
import { events, APP_EVENTS } from './core/events.js';
import { navigateTo, initRouter } from './core/router.js';
import { showToast } from './components/common/toast.js';
import { refreshIcons } from './utils/dom.js';
import { isLocalDevEnvironment } from './config/config.js';

import {
  openAuthModal,
  closeAuthModal,
  switchAuthTab,
  updateAuthUI,
  handleAuthLogin,
  handleAuthRegister,
  handleLogout
} from './components/common/auth-modal.js';

import { loadDashboard } from './pages/dashboard/dashboard.page.js';
import { loadJobs } from './pages/jobs/jobs.page.js';
import {
  openJobDetailModal,
  closeJobDetailModal,
  triggerCalculateMatch,
  saveJobBookmark
} from './components/jobs/job-detail-modal.js?v=2.2';

import {
  openScanJobsModal,
  closeScanJobsModal,
  toggleCustomLimitInput,
  startConfiguredJobScan
} from './components/jobs/job-scanner-modal.js';
import {
  openManualIngestModal,
  closeManualIngestModal,
  switchManualIngestTab,
  submitManualJobIngest
} from './components/jobs/manual-ingest-modal.js';
import { loadRecommendations } from './pages/recommendations/recommendations.page.js';
import {
  loadProfile,
  saveProfileChanges,
  syncProfileContext,
  handleResumeFileUpload
} from './pages/profile/profile.page.js';
import {
  startResumeTailoring,
  deleteTailoredResumeForJob,
  switchResumePreviewTab,
  saveAndRecompileResume,
  copyResumeLatex,
  renderResumeWorkspace,
  copyCoverLetterCleanEmail,
  copyCoverLetterSubject,
  openCoverLetterInMailClient,
  loadResumeHub,
  loadResumeById,
  deleteResumeFromHub
} from './pages/resume/resume.page.js';
import {
  loadApplications,
  changeApplicationStatus,
  prepareApplicationModal
} from './pages/applications/applications.page.js';
import {
  loadSystemView,
  saveCustomApiEndpoint,
  resetApiEndpoint,
  setApiPreset,
  testApiConnection,
  confirmPurgeDatabase,
  confirmResetDemo
} from './pages/system/system.page.js';

// --- Window Bridge for Backward Compatibility with Inline HTML Events ---
Object.assign(window, {
  state,
  api,
  navigateTo,
  showToast,
  refreshIcons,
  openAuthModal,
  closeAuthModal,
  switchAuthTab,
  updateAuthUI,
  handleAuthLogin,
  handleAuthRegister,
  handleLogout,
  loadDashboard,
  loadJobs,
  openJobDetailModal,
  closeJobDetailModal,
  triggerCalculateMatch,
  saveJobBookmark,
  openScanJobsModal,
  closeScanJobsModal,
  toggleCustomLimitInput,
  startConfiguredJobScan,
  openManualIngestModal,
  closeManualIngestModal,
  switchManualIngestTab,
  submitManualJobIngest,
  loadRecommendations,
  loadProfile,
  saveProfileChanges,
  syncProfileContext,
  handleResumeFileUpload,
  startResumeTailoring,
  deleteTailoredResumeForJob,
  switchResumePreviewTab,
  saveAndRecompileResume,
  copyResumeLatex,
  renderResumeWorkspace,
  copyCoverLetterCleanEmail,
  copyCoverLetterSubject,
  openCoverLetterInMailClient,
  loadResumeHub,
  loadResumeById,
  deleteResumeFromHub,
  loadApplications,
  changeApplicationStatus,
  prepareApplicationModal,
  loadSystemView,
  saveCustomApiEndpoint,
  resetApiEndpoint,
  setApiPreset,
  testApiConnection,
  confirmPurgeDatabase,
  confirmResetDemo
});

// --- Application Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Session Restoration
  if (api.hasToken()) {
    try {
      const me = await api.getMe();
      state.currentUser = me;
    } catch (err) {
      console.warn('Invalid or expired session token, reset to Guest:', err);
      api.logout();
      state.currentUser = null;
    }
  }
  updateAuthUI();

  // 2. Lắng nghe sự kiện phiên làm việc hết hạn
  window.addEventListener('jh:auth_expired', () => {
    state.currentUser = null;
    updateAuthUI();
    showToast('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.', 'warning');
    const protectedViews = ['recommendations', 'resume', 'applications', 'profile'];
    if (protectedViews.includes(state.activeView)) {
      navigateTo('dashboard');
    } else if (state.activeView === 'system') {
      loadSystemView();
    }
  });

  events.on(APP_EVENTS.AUTH_LOGIN_SUCCESS, () => {
    if (state.activeView === 'system') {
      loadSystemView();
    }
  });

  events.on(APP_EVENTS.AUTH_LOGOUT, () => {
    if (state.activeView === 'system') {
      loadSystemView();
    }
  });

  // Lắng nghe trạng thái Backend waking (Render Free cold start)
  let isWakingNoticeActive = false;
  events.on(APP_EVENTS.BACKEND_WAKING, (detail) => {
    if (!isWakingNoticeActive) {
      isWakingNoticeActive = true;
      const isLocal = isLocalDevEnvironment();
      const msg = isLocal
        ? `Đang kết nối lại Backend local (thử lại ${attempt}/${maxAttempts}). Vui lòng đợi trong giây lát...`
        : `Máy chủ đang khởi động lại (Render cold start, thử lại ${attempt}/${maxAttempts}). Vui lòng đợi trong giây lát...`;
      showToast(msg, 'info');
      setTimeout(() => { isWakingNoticeActive = false; }, 15000);
    }
  });

  events.on(APP_EVENTS.BACKEND_READY, () => {
    if (isWakingNoticeActive) {
      isWakingNoticeActive = false;
      showToast('Máy chủ Backend đã sẵn sàng!', 'success');
    }
  });

  // 3. Đóng Auth Modal khi click vào vùng backdrop
  const authModalEl = document.getElementById('auth-modal');
  if (authModalEl) {
    authModalEl.addEventListener('click', (e) => {
      if (e.target === authModalEl) {
        closeAuthModal();
      }
    });
  }

  // 4. Debounced Search Input
  const searchInput = document.getElementById('search-job-input');
  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(loadJobs, 350);
    });
  }

  // 5. Resume Upload Dropzone
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

  // 6. Mobile Sidebar Drawer Toggle
  const sidebarEl = document.querySelector('.app-sidebar');
  const toggleBtnEl = document.getElementById('btn-sidebar-toggle');
  const backdropEl = document.getElementById('sidebar-backdrop');

  const openMobileSidebar = () => {
    if (sidebarEl) sidebarEl.classList.add('drawer-open');
    if (backdropEl) backdropEl.classList.add('active');
  };

  const closeMobileSidebar = () => {
    if (sidebarEl) sidebarEl.classList.remove('drawer-open');
    if (backdropEl) backdropEl.classList.remove('active');
  };

  if (toggleBtnEl) {
    toggleBtnEl.addEventListener('click', () => {
      if (sidebarEl?.classList.contains('drawer-open')) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    });
  }

  if (backdropEl) {
    backdropEl.addEventListener('click', closeMobileSidebar);
  }

  // Auto-close sidebar on mobile navigation
  document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        closeMobileSidebar();
      }
    });
  });

  window.openMobileSidebar = openMobileSidebar;
  window.closeMobileSidebar = closeMobileSidebar;

  // 7. Router Initialization (Navigation links, History API, Popstate)
  initRouter();
  refreshIcons();
});

