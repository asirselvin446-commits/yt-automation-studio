import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { NotificationDrawer } from './components/layout/NotificationDrawer';
import { api } from './services/api';
import { StudioNotification } from './types';

// Pages
import { UploadQueue } from './pages/UploadQueue';
import { AutoSource } from './pages/AutoSource';
import { Accounts } from './pages/Accounts';
import { Ideas } from './pages/Ideas';
import { ChannelBrain } from './pages/ChannelBrain';
import { Settings } from './pages/Settings';

const pageTitles: Record<string, string> = {
  '/': 'Uploads',
  '/auto-source': 'Auto-Source Engine',
  '/accounts': 'YouTube Accounts',
  '/ideas': 'AI Idea Lab',
  '/channel-brain': 'Channel Brain AI',
  '/settings': 'Settings',
};

const AppContent: React.FC = () => {
  const location = useLocation();
  const [notifications, setNotifications] = useState<StudioNotification[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [cloudIngestActive, setCloudIngestActive] = useState(false);
  const [accountCount, setAccountCount] = useState(0);

  const loadStatus = async () => {
    try {
      const [health, notifs, accts] = await Promise.all([
        api.getHealth(),
        api.getNotifications(),
        api.listAccounts().catch(() => ({ accounts: [] })),
      ]);
      setCloudIngestActive(health.cloud_ingest_active);
      setNotifications(notifs);
      setAccountCount((accts.accounts || []).length);
    } catch (e) {
      console.error('Status fetch error:', e);
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch (e) {
      console.error(e);
    }
  };

  const currentTitle = pageTitles[location.pathname] || 'YT Automation Studio';

  return (
    <div className="flex h-screen bg-[#090a0f] text-slate-100 overflow-hidden font-sans">
      <Sidebar cloudIngestActive={cloudIngestActive} accountCount={accountCount} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          title={currentTitle}
          notifications={notifications}
          onOpenNotifications={() => setIsDrawerOpen(true)}
        />

        <main className="flex-1 overflow-y-auto bg-gradient-to-b from-[#090a0f] to-[#0c0e15]">
          <Routes>
            <Route path="/" element={<UploadQueue />} />
            <Route path="/auto-source" element={<AutoSource />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/ideas" element={<Ideas />} />
            <Route path="/channel-brain" element={<ChannelBrain />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>

      <NotificationDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        notifications={notifications}
        onMarkRead={handleMarkRead}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <Router>
      <AppContent />
    </Router>
  );
};

export default App;
