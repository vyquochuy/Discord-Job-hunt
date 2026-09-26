import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import * as profileApi from '../api/profile.api';
import { CandidateProfile } from '../types/candidate';
import { PageHeader } from '../components/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { EmptyState } from '../components/ui/empty-state';
import {
  User,
  UploadCloud,
  Save,
  RefreshCw,
  LogIn,
  Loader2,
} from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { isAuthenticated, openAuthModal, refreshCurrentUser } = useAuth();
  const { showToast } = useToast();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Form fields
  const [fullName, setFullName] = useState('');
  const [headline, setHeadline] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('');
  const [targetRoles, setTargetRoles] = useState('');
  const [targetLocations, setTargetLocations] = useState('');
  const [summary, setSummary] = useState('');

  const fetchProfile = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await profileApi.getProfile();
      setFullName(data.full_name || '');
      setHeadline(data.headline || '');
      setEmail(data.email || '');
      setPhone(data.phone || '');
      setLocation(data.location || '');
      setSummary(data.summary || '');
      setTargetRoles((data.target_roles || []).join(', '));
      setTargetLocations((data.target_locations || []).join(', '));
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể tải hồ sơ: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, showToast]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleSaveProfile = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSaving(true);
    try {
      const payload: Partial<CandidateProfile> = {
        full_name: fullName.trim(),
        headline: headline.trim(),
        email: email.trim(),
        phone: phone.trim(),
        location: location.trim(),
        summary: summary.trim(),
        target_roles: targetRoles
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        target_locations: targetLocations
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      };

      await profileApi.updateProfile(payload);
      await refreshCurrentUser();
      showToast('Thông tin hồ sơ ứng viên đã được lưu thành công!', 'success');
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Lưu hồ sơ thất bại: ${error.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSyncContext = async () => {
    setSyncing(true);
    try {
      showToast('Đang đồng bộ hồ sơ từ context file...', 'info');
      const res = await profileApi.syncProfileFromContext();
      showToast(
        `Đã đồng bộ ${res.skills_imported} kỹ năng, ${res.experiences_imported} kinh nghiệm, ${res.projects_imported} dự án!`,
        'success'
      );
      fetchProfile();
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Đồng bộ thất bại: ${error.message}`, 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      showToast(`Đang trích xuất nội dung từ ${file.name}...`, 'info');
      const res = await profileApi.uploadResumeFile(file);
      showToast('Đã trích xuất và nạp hồ sơ thành công!', 'success');
      if (res.full_name) setFullName(res.full_name);
      if (res.headline) setHeadline(res.headline);
      if (res.email) setEmail(res.email);
      if (res.phone) setPhone(res.phone);
      if (res.location) setLocation(res.location);
      if (res.summary) setSummary(res.summary);
      if (res.target_roles) setTargetRoles(res.target_roles.join(', '));
      if (res.target_locations) setTargetLocations(res.target_locations.join(', '));
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Tải file thất bại: ${error.message}`, 'error');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Hồ sơ ứng viên"
          description="Dữ liệu kỹ năng, kinh nghiệm và dự án làm nguồn tham chiếu duy nhất."
        />
        <EmptyState
          icon={<User className="w-6 h-6 text-primary" />}
          title="Yêu cầu Đăng nhập"
          description="Vui lòng đăng nhập để xem, chỉnh sửa và đồng bộ hóa hồ sơ năng lực của bạn."
          action={
            <Button variant="primary" size="sm" onClick={() => openAuthModal('login', 'profile')}>
              <LogIn className="w-3.5 h-3.5" />
              <span>Đăng nhập hoặc Đăng ký</span>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Hồ sơ Ứng viên (Single Source of Truth)"
        description="Dữ liệu lưu trữ tập trung và là nguồn tham chiếu duy nhất để hệ thống tạo CV tạo thiết kế chuẩn xác."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncContext}
              loading={syncing}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              <span>Đồng bộ từ Context</span>
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleSaveProfile()}
              loading={saving}
              icon={<Save className="w-3.5 h-3.5" />}
            >
              <span>Lưu thay đổi</span>
            </Button>
          </div>
        }
      />

      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3 text-text-muted">
          <Loader2 className="w-7 h-7 text-primary animate-spin" />
          <p className="text-sm font-medium">Đang tải dữ liệu hồ sơ ứng viên...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Section 1: Resume Upload Dropzone */}
          <Card>
            <CardHeader>
              <CardTitle>Tải lên Hồ sơ gốc (PDF, TeX, YAML, Markdown)</CardTitle>
              <CardDescription>
                Hệ thống tự động trích xuất cấu trúc thông tin, danh sách kỹ năng, dự án và kinh nghiệm để nạp vào DB.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.tex,.yaml,.yml,.md,.txt"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />

              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-6 sm:p-8 rounded-lg border-2 border-dashed text-center cursor-pointer transition-all ${
                  dragOver
                    ? 'border-primary bg-primary-50/50'
                    : 'border-border hover:border-primary/60 hover:bg-slate-50/50'
                }`}
              >
                {uploading ? (
                  <div className="flex flex-col items-center gap-2 text-primary py-2">
                    <Loader2 className="w-8 h-8 animate-spin" />
                    <span className="text-sm font-medium">Đang tải lên và phân tích tài liệu...</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center mb-1">
                      <UploadCloud className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-semibold text-text-primary">
                      Kéo thả tệp tin hồ sơ hoặc nhấn vào đây để tải lên
                    </p>
                    <p className="text-xs text-text-muted">
                      Định dạng hỗ trợ: <strong className="text-slate-700">.PDF, .TeX, .YAML, .MD, .TXT</strong> (Tối đa 15MB)
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Candidate Info Form */}
          <form onSubmit={handleSaveProfile}>
            <Card>
              <CardHeader>
                <CardTitle>Thông tin năng lực & Định hướng</CardTitle>
                <CardDescription>
                  Dữ liệu được dùng làm bằng chứng (Fact) đối soát chống ảo giác trong mọi phiên tạo hồ sơ.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Họ và tên ứng viên"
                    placeholder="Nguyễn Văn A"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <Input
                    label="Chức danh / Định hướng chuyên môn"
                    placeholder="Backend Developer / DevOps Engineer"
                    value={headline}
                    onChange={(e) => setHeadline(e.target.value)}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    type="email"
                    label="Email liên hệ"
                    placeholder="name@domain.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Input
                    type="tel"
                    label="Số điện thoại"
                    placeholder="+84 901 234 567"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>

                <Input
                  label="Địa điểm cư trú"
                  placeholder="TP. Hồ Chí Minh, Việt Nam"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />

                <Input
                  label="Vị trí mục tiêu (Phân cách bằng dấu phẩy)"
                  placeholder="Backend Developer, DevOps Engineer, Golang Engineer"
                  value={targetRoles}
                  onChange={(e) => setTargetRoles(e.target.value)}
                  helperText="Các từ khóa này được dùng để lọc và tăng điểm ưu tiên khi đối soát JD."
                />

                <Input
                  label="Khu vực làm việc mong muốn (Phân cách bằng dấu phẩy)"
                  placeholder="Ho Chi Minh City, Remote, Ha Noi"
                  value={targetLocations}
                  onChange={(e) => setTargetLocations(e.target.value)}
                />

                <div className="space-y-1.5">
                  <label htmlFor="prof-summary" className="block text-xs font-semibold text-text-primary">
                    Tóm tắt năng lực & Mục tiêu nghề nghiệp
                  </label>
                  <textarea
                    id="prof-summary"
                    rows={5}
                    value={summary}
                    onChange={(e) => setSummary(e.target.value)}
                    placeholder="Tóm tắt ngắn gọn năng lực cốt lõi, kinh nghiệm nổi bật và định hướng công việc..."
                    className="w-full p-3 bg-white border border-border rounded-md text-xs sm:text-sm font-sans leading-relaxed placeholder:text-text-muted/60 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                </div>
              </CardContent>

              <CardFooter className="justify-end">
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  loading={saving}
                  icon={<Save className="w-3.5 h-3.5" />}
                >
                  <span>Lưu thông tin hồ sơ</span>
                </Button>
              </CardFooter>
            </Card>
          </form>
        </div>
      )}
    </div>
  );
};
