/**
 * Job Hunter Platform - Main Application Entry Point (Modular ES Architecture)
 */

import { state } from './core/store.js';
import { api } from './api/index.js';
import { navigateTo, initRouter } from './core/router.js';
import { showToast } from './components/common/toast.js';
import { refreshIcons } from './utils/dom.js';

import {
  openAuthModal,
  closeAuthModal,
  switchAuthTab,
  updateAuthUI,
  handleAuthLogin,
  handleAuthRegister,
  handleQuickAdminLogin,
  handleLogout
} from './components/common/auth-modal.js';

import { loadDashboard } from './pages/dashboard/dashboard.page.js';
import { loadJobs } from './pages/jobs/jobs.page.js';
import {
  openJobDetailModal,
  closeJobDetailModal,
  triggerCalculateMatch,
  saveJobBookmark
} from './components/jobs/job-detail-modal.js';
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
  openCoverLetterInMailClient
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
  handleQuickAdminLogin,
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

  // 6. Router Initialization (Navigation links, History API, Popstate)
  initRouter();
  refreshIcons();
});
