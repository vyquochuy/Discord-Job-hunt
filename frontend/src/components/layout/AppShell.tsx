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
    <div className="app-shell reference-shell flex h-screen overflow-hidden text-text-primary antialiased">
      <div className="app-shell__overlay" aria-hidden="true" />
      <div className="app-ambient app-ambient--one" aria-hidden="true" />
      <div className="app-ambient app-ambient--two" aria-hidden="true" />
      <div className="relative z-20 hidden h-full flex-shrink-0 lg:block">
        <Sidebar activeView={activeView} onNavigate={onNavigate} />
      </div>
      <Sheet open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
        <SheetContent side="left" className="reference-drawer p-0 w-[260px] overflow-hidden">
          <Sidebar
            activeView={activeView}
            onNavigate={onNavigate}
            onCloseMobileDrawer={() => setMobileDrawerOpen(false)}
            className="w-full border-r-0"
          />
        </SheetContent>
      </Sheet>
      <div className="relative z-10 flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Topbar activeView={activeView} onOpenMobileDrawer={() => setMobileDrawerOpen(true)} />
        <main className="reference-main flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-[1680px] mx-auto w-full">{children}</div>
        </main>
      </div>
      <AuthModal />
    </div>
  );
};