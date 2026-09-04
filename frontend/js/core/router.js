/**
 * Frontend Router (HTML5 History API)
 */

import { VALID_VIEWS, VIEW_TITLES } from '../config/config.js';
import { state } from './store.js';
import { refreshIcons } from '../utils/dom.js';
import { setAuthNavigateHandler } from '../components/common/auth-modal.js';

import { loadDashboard } from '../pages/dashboard/dashboard.page.js';
import { loadJobs } from '../pages/jobs/jobs.page.js';
import { loadRecommendations } from '../pages/recommendations/recommendations.page.js';
import { loadProfile } from '../pages/profile/profile.page.js';
import { renderResumeWorkspace } from '../pages/resume/resume.page.js';
import { loadApplications } from '../pages/applications/applications.page.js';
import { loadSystemView } from '../pages/system/system.page.js';

export function navigateTo(viewName, pushState = true) {
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
  const headerTitle = document.getElementById('header-title-text');
  if (headerTitle) {
    headerTitle.textContent = VIEW_TITLES[targetView] || 'Job Hunter Platform';
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

export function initRouter() {
  setAuthNavigateHandler(navigateTo);

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
}
