/**
 * Job Hunter Platform — Centralized Application Store
 */

export const state = {
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

const listeners = new Set();

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setState(updates) {
  Object.assign(state, updates);
  listeners.forEach(fn => fn(state));
}

export function resetUserState() {
  state.currentUser = null;
  state.savedJobs = [];
  state.applications = [];
  state.topRecommendations = [];
  state.selectedResume = null;
  state.candidateProfile = null;
  listeners.forEach(fn => fn(state));
}
