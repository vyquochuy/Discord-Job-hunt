/**
 * Job Hunter Platform — Candidate Profile Page Controller
 */

import { state } from '../../core/store.js';
import { api } from '../../api/index.js';
import { refreshIcons, setVal } from '../../utils/dom.js';
import { showToast } from '../../components/common/toast.js';
import { openAuthModal } from '../../components/common/auth-modal.js';

export async function loadProfile() {
  const authReqEl = document.getElementById('profile-auth-required');
  const authContentEl = document.getElementById('profile-authenticated-content');

  if (!state.currentUser) {
    if (authReqEl) authReqEl.style.display = 'block';
    if (authContentEl) authContentEl.style.display = 'none';
    refreshIcons();
    return;
  }

  if (authReqEl) authReqEl.style.display = 'none';
  if (authContentEl) authContentEl.style.display = 'block';

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

export async function saveProfileChanges() {
  if (!state.currentUser) {
    showToast('Vui lòng đăng nhập để lưu thay đổi hồ sơ!', 'warning');
    openAuthModal('login', 'profile');
    return;
  }

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

export async function syncProfileContext() {
  if (!state.currentUser) {
    showToast('Vui lòng đăng nhập để đồng bộ hồ sơ ứng viên!', 'warning');
    openAuthModal('login', 'profile');
    return;
  }

  try {
    showToast('Đang đồng bộ hồ sơ từ context file...', 'info');
    const res = await api.syncProfileFromContext();
    showToast(`Đã đồng bộ ${res.skills_imported} kỹ năng, ${res.experiences_imported} kinh nghiệm, ${res.projects_imported} dự án!`, 'success');
    loadProfile();
  } catch (err) {
    showToast(`Đồng bộ thất bại: ${err.message}`, 'error');
  }
}

export async function handleResumeFileUpload(event) {
  if (!state.currentUser) {
    showToast('Vui lòng đăng nhập để tải lên và trích xuất hồ sơ CV!', 'warning');
    openAuthModal('login', 'profile');
    return;
  }

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
