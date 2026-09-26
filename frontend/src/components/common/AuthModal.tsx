import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs';
import { ShieldCheck, LogIn, UserPlus, Lock } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const {
    isAuthModalOpen,
    closeAuthModal,
    authModalTab,
    setAuthModalTab,
    login,
    register,
  } = useAuth();

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
      setLoginPassword('');
    } catch (err: unknown) {
      const error = err as Error;
      setErrorMessage(error.message || 'Đăng nhập không thành công');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (regPassword.length < 6) {
      setErrorMessage('Mật khẩu tối thiểu phải có 6 ký tự.');
      return;
    }

    setLoading(true);
    try {
      await register(regEmail, regPassword, regName);
      setRegPassword('');
    } catch (err: unknown) {
      const error = err as Error;
      setErrorMessage(error.message || 'Đăng ký không thành công');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isAuthModalOpen} onOpenChange={(open) => !open && closeAuthModal()}>
      <DialogContent size="sm">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary-50 text-primary flex items-center justify-center flex-shrink-0">
              <ShieldCheck className="w-5 h-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Tài khoản & Xác thực</DialogTitle>
              <DialogDescription>
                Đăng nhập để lưu tin, nộp đơn và sử dụng các tính năng thông minh.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <DialogBody className="space-y-4">
          <Tabs
            value={authModalTab}
            onValueChange={(val) => {
              setErrorMessage(null);
              setAuthModalTab(val as 'login' | 'register');
            }}
          >
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="login" className="gap-2">
                <LogIn className="w-3.5 h-3.5" />
                <span>Đăng nhập</span>
              </TabsTrigger>
              <TabsTrigger value="register" className="gap-2">
                <UserPlus className="w-3.5 h-3.5" />
                <span>Tạo tài khoản</span>
              </TabsTrigger>
            </TabsList>

            {errorMessage && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-danger font-medium mt-3">
                {errorMessage}
              </div>
            )}

            {/* Login Tab */}
            <TabsContent value="login">
              <form onSubmit={handleLoginSubmit} className="space-y-3.5 mt-2">
                <Input
                  type="email"
                  label="Địa chỉ Email"
                  placeholder="name@example.com"
                  required
                  autoComplete="username"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                />
                <Input
                  type="password"
                  label="Mật khẩu"
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                />

                <Button
                  type="submit"
                  variant="primary"
                  className="w-full justify-center mt-2"
                  loading={loading}
                >
                  <LogIn className="w-4 h-4" />
                  <span>Đăng nhập hệ thống</span>
                </Button>
              </form>
            </TabsContent>

            {/* Register Tab */}
            <TabsContent value="register">
              <form onSubmit={handleRegisterSubmit} className="space-y-3.5 mt-2">
                <Input
                  type="text"
                  label="Họ và tên"
                  placeholder="Nguyễn Văn A"
                  required
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                />
                <Input
                  type="email"
                  label="Địa chỉ Email"
                  placeholder="name@example.com"
                  required
                  autoComplete="username"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                />
                <Input
                  type="password"
                  label="Mật khẩu (Tối thiểu 6 ký tự)"
                  placeholder="••••••••"
                  required
                  autoComplete="new-password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                />

                <Button
                  type="submit"
                  variant="primary"
                  className="w-full justify-center mt-2"
                  loading={loading}
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Tạo tài khoản & Bắt đầu</span>
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </DialogBody>

        <DialogFooter className="justify-between text-xs text-text-muted">
          <span className="flex items-center gap-1.5 text-xs text-text-muted">
            <Lock className="w-3 h-3 text-slate-400" />
            <span>Dual-Token JWT & Argon2id OWASP</span>
          </span>
          <Button variant="ghost" size="xs" onClick={closeAuthModal}>
            Đóng
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
