import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User } from '../types/auth';
import { client } from '../api/client';
import * as authApi from '../api/auth.api';
import { useToast } from './ToastContext';

interface AuthContextValue {
  currentUser: User | null;
  isAuthenticated: boolean;
  isSuperuser: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshCurrentUser: () => Promise<void>;

  // Auth modal control
  isAuthModalOpen: boolean;
  authModalTab: 'login' | 'register';
  authRedirectTarget: string | null;
  openAuthModal: (tab?: 'login' | 'register', redirectTarget?: string) => void;
  closeAuthModal: () => void;
  setAuthModalTab: (tab: 'login' | 'register') => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState<'login' | 'register'>('login');
  const [authRedirectTarget, setAuthRedirectTarget] = useState<string | null>(null);

  const { showToast } = useToast();

  const refreshCurrentUser = useCallback(async () => {
    if (!client.hasToken()) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }

    try {
      const me = await authApi.getMe();
      setCurrentUser(me);
    } catch (err) {
      console.warn('Invalid session, logging out:', err);
      await client.logout();
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCurrentUser();

    // Listen to expired auth events emitted by ApiClient
    const unsubscribe = client.onAuthExpired(() => {
      setCurrentUser(null);
      showToast('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.', 'warning');
    });

    const unregWaking = client.onBackendWaking((detail) => {
      showToast(
        `Đang kết nối lại máy chủ (thử lần ${detail.attempt}/${detail.maxAttempts}). Vui lòng đợi trong giây lát...`,
        'info'
      );
    });

    const unregReady = client.onBackendReady(() => {
      showToast('Máy chủ Backend đã sẵn sàng!', 'success');
    });

    return () => {
      unsubscribe();
      unregWaking();
      unregReady();
    };
  }, [refreshCurrentUser, showToast]);

  const login = async (email: string, password: string) => {
    const tokens = await authApi.login(email, password);
    client.setTokens(tokens.access_token, tokens.refresh_token);
    await refreshCurrentUser();
    showToast('Đăng nhập thành công!', 'success');
    setIsAuthModalOpen(false);
  };

  const register = async (email: string, password: string, fullName: string) => {
    const res = await authApi.register(email, password, fullName);
    client.setTokens(res.access_token, res.refresh_token);
    if (res.user) {
      setCurrentUser(res.user);
    } else {
      await refreshCurrentUser();
    }
    showToast('Đăng ký tài khoản thành công!', 'success');
    setIsAuthModalOpen(false);
  };

  const logout = async () => {
    await client.logout();
    setCurrentUser(null);
    showToast('Đã đăng xuất khỏi hệ thống.', 'info');
  };

  const openAuthModal = (tab: 'login' | 'register' = 'login', redirectTarget?: string) => {
    setAuthModalTab(tab);
    if (redirectTarget) {
      setAuthRedirectTarget(redirectTarget);
    } else {
      setAuthRedirectTarget(null);
    }
    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        isAuthenticated: !!currentUser,
        isSuperuser: !!currentUser?.is_superuser,
        loading,
        login,
        register,
        logout,
        refreshCurrentUser,
        isAuthModalOpen,
        authModalTab,
        authRedirectTarget,
        openAuthModal,
        closeAuthModal,
        setAuthModalTab,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
