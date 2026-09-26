import React, { useState } from 'react';
import { Sidebar, ViewType } from './Sidebar';
import { Topbar } from './Topbar';
import { Sheet, SheetContent } from '../ui/sheet';
import { AuthModal } from '../common/AuthModal';

export interface AppShellProps {
  activeView: ViewType;
  onNavigate: (view: ViewType) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ activeView, onNavigate, children }) => {
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background text-text-primary overflow-hidden font-sans antialiased">
      {/* Desktop Sidebar (hidden on < 1024px) */}
      <div className="hidden lg:block h-full flex-shrink-0 z-20">
        <Sidebar activeView={activeView} onNavigate={onNavigate} />
      </div>

      {/* Mobile Drawer Navigation (< 1024px) */}
      <Sheet open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
        <SheetContent side="left" className="p-0 w-[260px] overflow-hidden">
          <Sidebar
            activeView={activeView}
            onNavigate={onNavigate}
            onCloseMobileDrawer={() => setMobileDrawerOpen(false)}
            className="w-full border-r-0"
          />
        </SheetContent>
      </Sheet>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Topbar
          activeView={activeView}
          onOpenMobileDrawer={() => setMobileDrawerOpen(true)}
          onNavigateToJobs={() => onNavigate('jobs')}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto w-full">{children}</div>
        </main>
      </div>

      {/* Global Auth Modal */}
      <AuthModal />
    </div>
  );
};
