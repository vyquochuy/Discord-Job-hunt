import React, { useState, useEffect, useCallback } from 'react';
import { ToastProvider, useToast } from './context/ToastContext';
import { AuthProvider } from './context/AuthContext';
import { AppShell } from './components/layout/AppShell';
import { ViewType } from './components/layout/Sidebar';

// Pages
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { RecommendationsPage } from './pages/RecommendationsPage';
import { ResumePage } from './pages/ResumePage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { ProfilePage } from './pages/ProfilePage';
import { SystemPage } from './pages/SystemPage';

// Modals
import { JobDetailModal } from './components/jobs/JobDetailModal';
import { JobScannerModal } from './components/jobs/JobScannerModal';
import { ManualIngestModal } from './components/jobs/ManualIngestModal';

// APIs
import * as resumeApi from './api/resume.api';
import * as applicationsApi from './api/applications.api';

const parseInitialRoute = (): { view: ViewType; resumeId: string | null; jobId: string | null } => {
  const path = window.location.pathname.toLowerCase();
  const searchParams = new URLSearchParams(window.location.search);
  const jobId = searchParams.get('job');

  if (path.startsWith('/jobs')) return { view: 'jobs', resumeId: null, jobId };
  if (path.startsWith('/recommendations')) return { view: 'recommendations', resumeId: null, jobId };
  if (path.startsWith('/resume')) {
    const parts = path.split('/').filter(Boolean);
    const resumeId = parts.length > 1 ? parts[1] : null;
    return { view: 'resume', resumeId, jobId };
  }
  if (path.startsWith('/applications')) return { view: 'applications', resumeId: null, jobId };
  if (path.startsWith('/profile')) return { view: 'profile', resumeId: null, jobId };
  if (path.startsWith('/system')) return { view: 'system', resumeId: null, jobId };
  return { view: 'dashboard', resumeId: null, jobId };
};

const AppContent: React.FC = () => {
  const { showToast } = useToast();

  const [activeView, setActiveView] = useState<ViewType>('dashboard');
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);

  // Global modals state
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobDetailOpen, setJobDetailOpen] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [manualIngestOpen, setManualIngestOpen] = useState(false);

  // Initialize route on mount
  useEffect(() => {
    const { view, resumeId, jobId } = parseInitialRoute();
    setActiveView(view);
    if (resumeId) setSelectedResumeId(resumeId);
    if (jobId) {
      setSelectedJobId(jobId);
      setJobDetailOpen(true);
    }

    const handlePopState = () => {
      const current = parseInitialRoute();
      setActiveView(current.view);
      setSelectedResumeId(current.resumeId);
      if (current.jobId) {
        setSelectedJobId(current.jobId);
        setJobDetailOpen(true);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = useCallback((view: ViewType, options?: { resumeId?: string | null }) => {
    setActiveView(view);
    if (options?.resumeId !== undefined) {
      setSelectedResumeId(options.resumeId);
    }

    let url = `/${view === 'dashboard' ? '' : view}`;
    if (view === 'resume' && options?.resumeId) {
      url = `/resume/${options.resumeId}`;
    }

    window.history.pushState(null, '', url || '/');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Modal handlers
  const handleOpenJobDetail = useCallback((jobId: string) => {
    setSelectedJobId(jobId);
    setJobDetailOpen(true);
  }, []);

  const handleCloseJobDetail = useCallback((open: boolean) => {
    setJobDetailOpen(open);
    if (!open) {
      setSelectedJobId(null);
    }
  }, []);

  const handleTailorResume = useCallback(
    async (jobId: string) => {
      try {
        showToast('Đang khởi tạo hồ sơ ứng tuyển từ tin tuyển dụng...', 'info');
        const tailored = await resumeApi.createTailoredResume(jobId);
        showToast('Khởi tạo hồ sơ thành công! Đang chuyển tới Workspace.', 'success');
        setJobDetailOpen(false);
        navigateTo('resume', { resumeId: tailored.id });
      } catch (err: unknown) {
        const e = err as Error;
        showToast(`Không thể tạo hồ sơ: ${e.message}`, 'error');
      }
    },
    [navigateTo, showToast]
  );

  const handleApplyJob = useCallback(
    async (jobId: string) => {
      try {
        await applicationsApi.createApplication({
          job_id: jobId,
          status: 'READY',
          notes: 'Tạo nhanh từ chi tiết công việc',
        });
        showToast('Đã lưu đơn ứng tuyển vào danh sách theo dõi!', 'success');
        setJobDetailOpen(false);
        navigateTo('applications');
      } catch (err: unknown) {
        const e = err as Error;
        showToast(`Không thể lưu đơn nộp: ${e.message}`, 'error');
      }
    },
    [navigateTo, showToast]
  );

  return (
    <AppShell activeView={activeView} onNavigate={navigateTo}>
      {activeView === 'dashboard' && (
        <DashboardPage
          onNavigate={navigateTo}
          onOpenJobDetail={handleOpenJobDetail}
          onOpenScanner={() => setScannerOpen(true)}
          onOpenManualIngest={() => setManualIngestOpen(true)}
        />
      )}

      {activeView === 'jobs' && (
        <JobsPage
          onOpenJobDetail={handleOpenJobDetail}
          onOpenManualIngest={() => setManualIngestOpen(true)}
          onOpenScanner={() => setScannerOpen(true)}
        />
      )}

      {activeView === 'recommendations' && (
        <RecommendationsPage
          onOpenJobDetail={handleOpenJobDetail}
          onOpenScanner={() => setScannerOpen(true)}
        />
      )}

      {activeView === 'resume' && (
        <ResumePage
          resumeId={selectedResumeId}
          onSelectResumeId={(id) => {
            setSelectedResumeId(id);
            if (id) {
              window.history.pushState(null, '', `/resume/${id}`);
            } else {
              window.history.pushState(null, '', '/resume');
            }
          }}
          onNavigateToJobs={() => navigateTo('jobs')}
          onOpenJobDetail={handleOpenJobDetail}
        />
      )}

      {activeView === 'applications' && <ApplicationsPage />}

      {activeView === 'profile' && <ProfilePage />}

      {activeView === 'system' && <SystemPage />}

      {/* Global Modals */}
      <JobDetailModal
        jobId={selectedJobId}
        open={jobDetailOpen}
        onOpenChange={handleCloseJobDetail}
        onTailorResume={handleTailorResume}
        onApplyJob={handleApplyJob}
      />

      <JobScannerModal
        open={scannerOpen}
        onOpenChange={setScannerOpen}
        onScanCompleted={() => {
          showToast('Quét tin tuyển dụng hoàn tất!', 'success');
        }}
      />

      <ManualIngestModal
        open={manualIngestOpen}
        onOpenChange={setManualIngestOpen}
        onIngestCompleted={() => {
          showToast('Đã nạp tin tuyển dụng thành công!', 'success');
        }}
      />
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;
