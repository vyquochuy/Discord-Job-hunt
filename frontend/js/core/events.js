/**
 * Job Hunter Platform — Centralized Event Bus
 */

class EventBus {
  constructor() {
    this.target = new EventTarget();
  }

  on(event, callback) {
    const handler = (e) => callback(e.detail);
    this.target.addEventListener(event, handler);
    return () => this.target.removeEventListener(event, handler);
  }

  emit(event, detail = null) {
    this.target.dispatchEvent(new CustomEvent(event, { detail }));
    // Also dispatch to window for external integration
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(event, { detail }));
    }
  }
}

export const events = new EventBus();

export const APP_EVENTS = {
  AUTH_EXPIRED: 'jh:auth_expired',
  AUTH_LOGIN_SUCCESS: 'jh:auth_login_success',
  AUTH_LOGOUT: 'jh:auth_logout',
  PROFILE_UPDATED: 'jh:profile_updated',
  VIEW_CHANGED: 'jh:view_changed',
};
