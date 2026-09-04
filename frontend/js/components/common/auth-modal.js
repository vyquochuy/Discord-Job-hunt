/**
 * Job Hunter Platform — Authentication Modal & Role Controller
 */

import { isLocalDevEnvironment } from '../../config/config.js';
import { state, resetUserState } from '../../core/store.js';
import { events, APP_EVENTS } from '../../core/events.js';
import { api } from '../../api/index.js';
import { showToast } from './toast.js';
import { refreshIcons } from '../../utils/dom.js';

let pendingRedirectView = null;
let navigateFn = null;

export function setAuthNavigateHandler(fn) {
  navigateFn = fn;
}

function doNavigate(targetView, pushState = false) {
  if (typeof navigateFn === 'function') {
    navigateFn(targetView, pushState);
  } else if (typeof window !== 'undefined' && typeof window.navigateTo === 'function') {
    window.navigateTo(targetView, pushState);
  }
}

export function updateAuthUI() {
  const loggedInContainer = document.getElementById('sidebar-user-logged-in');
  const guestContainer = document.getElementById('sidebar-user-guest');
  const headerBtnLogin = document.getElementById('header-btn-login');
  const nameEl = document.getElementById('sidebar-user-name');
  const emailEl = document.getElementById('sidebar-user-email');
  const roleBadge = document.getElementById('sidebar-role-badge');
  const quickDevContainer = document.getElementById('quick-dev-login-container');

  // Control Quick Dev Login button visibility strictly:
  if (quickDevContainer) {
    quickDevContainer.style.display = isLocalDevEnvironment() ? 'flex' : 'none';
  }

  if (state.currentUser) {
    if (loggedInContainer) loggedInContainer.style.display = 'flex';
    if (guestContainer) guestContainer.style.display = 'none';
    if (headerBtnLogin) headerBtnLogin.style.display = 'none';

    if (nameEl) nameEl.textContent = state.currentUser.full_name || 'Người dùng';
    if (emailEl) emailEl.textContent = state.currentUser.email || '';

    if (roleBadge) {
      roleBadge.style.display = 'inline-block';
      if (state.currentUser.is_superuser) {
        roleBadge.textContent = 'Admin';
        roleBadge.className = 'badge badge-purple';
        roleBadge.title = 'Tài khoản Quản trị viên tối cao (Superuser)';
      } else {
        roleBadge.textContent = 'Ứng viên';
        roleBadge.className = 'badge badge-blue';
        roleBadge.title = 'Tài khoản Ứng viên';
      }
    }
  } else {
    if (loggedInContainer) loggedInContainer.style.display = 'none';
    if (guestContainer) guestContainer.style.display = 'flex';
    if (headerBtnLogin) headerBtnLogin.style.display = 'inline-flex';
  }

  refreshIcons();
}

export function openAuthModal(defaultTab = 'login', redirectView = null) {
  pendingRedirectView = redirectView;
  switchAuthTab(defaultTab);

  const modal = document.getElementById('auth-modal');
  if (modal) {
    modal.classList.add('active');
  }

  const quickDevContainer = document.getElementById('quick-dev-login-container');
  if (quickDevContainer) {
    quickDevContainer.style.display = isLocalDevEnvironment() ? 'flex' : 'none';
  }

  refreshIcons();
}

export function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

export function switchAuthTab(tab) {
  const tabLogin = document.getElementById('tab-btn-auth-login');
  const tabReg = document.getElementById('tab-btn-auth-register');
  const formLogin = document.getElementById('form-auth-login');
  const formReg = document.getElementById('form-auth-register');
  const title = document.getElementById('auth-modal-title');

  if (tab === 'register') {
    if (tabLogin) tabLogin.classList.remove('active');
    if (tabReg) tabReg.classList.add('active');
    if (formLogin) formLogin.style.display = 'none';
    if (formReg) formReg.style.display = 'block';
    if (title) title.textContent = 'Tạo tài khoản mới';
  } else {
    if (tabLogin) tabLogin.classList.add('active');
    if (tabReg) tabReg.classList.remove('active');
    if (formLogin) formLogin.style.display = 'block';
    if (formReg) formReg.style.display = 'none';
    if (title) title.textContent = 'Đăng nhập hệ thống';
  }

  refreshIcons();
}

export async function handleAuthLogin(e) {
  if (e && e.preventDefault) e.preventDefault();
  const emailInput = document.getElementById('auth-login-email');
  const passInput = document.getElementById('auth-login-password');
  const submitBtn = document.getElementById('btn-submit-auth-login');

  const email = emailInput?.value.trim();
  const password = passInput?.value;

  if (!email || !password) {
    showToast('Vui lòng nhập đầy đủ Email và Mật khẩu!', 'warning');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner"></div><span>Đang kiểm tra...</span>';
  }

  try {
    const res = await api.login(email, password);
    api.setToken(res.access_token);
    state.currentUser = res.user;
    updateAuthUI();
    closeAuthModal();

    showToast(`Đăng nhập thành công! Chào mừng ${res.user.full_name || res.user.email}.`, 'success');
    events.emit(APP_EVENTS.AUTH_LOGIN_SUCCESS, res.user);

    const targetView = pendingRedirectView || state.activeView;
    pendingRedirectView = null;
    doNavigate(targetView, false);
  } catch (err) {
    showToast(`Đăng nhập thất bại: ${err.message}`, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i data-lucide="log-in" class="icon-sm"></i><span>Đăng nhập hệ thống</span>';
      refreshIcons();
    }
  }
}

export async function handleAuthRegister(e) {
  if (e && e.preventDefault) e.preventDefault();
  const nameInput = document.getElementById('auth-reg-name');
  const emailInput = document.getElementById('auth-reg-email');
  const passInput = document.getElementById('auth-reg-password');
  const submitBtn = document.getElementById('btn-submit-auth-reg');

  const fullName = nameInput?.value.trim();
  const email = emailInput?.value.trim();
  const password = passInput?.value;

  if (!fullName || !email || !password) {
    showToast('Vui lòng điền đầy đủ các thông tin đăng ký!', 'warning');
    return;
  }

  if (password.length < 6) {
    showToast('Mật khẩu cần tối thiểu 6 ký tự!', 'warning');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner"></div><span>Đang tạo tài khoản...</span>';
  }

  try {
    const res = await api.register(email, password, fullName);
    api.setToken(res.access_token);
    state.currentUser = res.user;
    updateAuthUI();
    closeAuthModal();

    showToast(`Tạo tài khoản thành công! Quyền: ${res.user.is_superuser ? 'Quản trị viên (Superuser)' : 'Ứng viên'}.`, 'success');
    events.emit(APP_EVENTS.AUTH_LOGIN_SUCCESS, res.user);

    const targetView = pendingRedirectView || state.activeView;
    pendingRedirectView = null;
    doNavigate(targetView, false);
  } catch (err) {
    showToast(`Đăng ký thất bại: ${err.message}`, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i data-lucide="user-plus" class="icon-sm"></i><span>Tạo tài khoản & Bắt đầu</span>';
      refreshIcons();
    }
  }
}

export async function handleQuickAdminLogin() {
  if (!isLocalDevEnvironment()) {
    showToast('Tính năng này chỉ khả dụng trong môi trường Localhost!', 'warning');
    return;
  }

  const email = 'vyquochuy3005@gmail.com';
  const password = 'vyquochuy300600';

  showToast('Đang thực hiện đăng nhập nhanh tài khoản Admin...', 'info');

  try {
    let res;
    try {
      res = await api.login(email, password);
    } catch (loginErr) {
      // Bootstrap via register if not exists
      res = await api.register(email, password, 'Vy Quoc Huy');
    }

    api.setToken(res.access_token);
    state.currentUser = res.user;
    updateAuthUI();
    closeAuthModal();

    showToast('Đã đăng nhập nhanh thành công với quyền Quản trị viên tối cao (Superuser)!', 'success');
    events.emit(APP_EVENTS.AUTH_LOGIN_SUCCESS, res.user);

    const targetView = pendingRedirectView || state.activeView;
    pendingRedirectView = null;
    doNavigate(targetView, false);
  } catch (err) {
    showToast(`Đăng nhập nhanh thất bại: ${err.message}`, 'error');
  }
}

export function handleLogout() {
  api.logout();
  resetUserState();
  updateAuthUI();
  showToast('Đã đăng xuất khỏi tài khoản thành công.', 'info');
  events.emit(APP_EVENTS.AUTH_LOGOUT);

  const protectedViews = ['recommendations', 'resume', 'applications', 'profile'];
  if (protectedViews.includes(state.activeView)) {
    doNavigate('dashboard');
  } else {
    doNavigate(state.activeView, false);
  }
}
