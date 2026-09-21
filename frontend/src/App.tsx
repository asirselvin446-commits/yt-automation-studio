import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { NotificationDrawer } from './components/layout/NotificationDrawer';
import { api } from './services/api';
import { StudioNotification } from './types';

// Pages
import { Dashboard } from './pages/Dashboard';
import { Inbox } from './pages/Inbox';
import { Processing } from './pages/Processing';
import { UploadQueue } from './pages/UploadQueue';
import { Videos } from './pages/Videos';
import { VideoDetail } from './pages/VideoDetail';
import { ContentCalendar } from './pages/ContentCalendar';
import { Thumbnails } from './pages/Thumbnails';
import { Ideas } from './pages/Ideas';
import { Analytics } from './pages/Analytics';
import { ChannelBrain } from './pages/ChannelBrain';
import { Monetization } from './pages/Monetization';
import { Automation } from './pages/Automation';
import { AutoSource } from './pages/AutoSource';
import { Settings } from './pages/Settings';

const pageTitles: Record<string, string> = {
  '/': 'Uploads',
  '/inbox': 'Video Inbox',
  '/processing': 'Processing Pipeline',
  '/upload-queue': 'Uploads',
  '/videos': 'Video Library',
  '/calendar': 'Content Calendar',
  '/thumbnails': 'Thumbnail Workspace',
  '/ideas': 'AI Idea Lab',
  '/analytics': 'Channel Analytics',
  '/channel-brain': 'Channel Brain AI',
  '/monetization': 'Monetization Progress',
  '/automation': 'Automation Center',
  '/auto-source': 'Auto-Source Engine',
  '/settings': 'Settings',
};

const AppContent: React.FC = () => {
  const location = useLocation();
  const [notifications, setNotifications] = useState<StudioNotification[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [cloudIngestActive, setCloudIngestActive] = useState(false);
  const [channelConnected, setChannelConnected] = useState(false);

  const loadStatus = async () => {
    try {
      const [health, notifs, ch] = await Promise.all([
        api.getHealth(),
        api.getNotifications(),
        api.getChannelStatus(),
      ]);
      setCloudIngestActive(health.cloud_ingest_active);
      setNotifications(notifs);
      setChannelConnected(ch.is_connected);
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

  // Determine active title
  const currentTitle =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith('/videos/') ? 'Video Review Workspace' : 'YT Automation Studio');

  return (
    <div className="flex h-screen bg-[#090a0f] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar cloudIngestActive={cloudIngestActive} channelConnected={channelConnected} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          title={currentTitle}
          notifications={notifications}
          onOpenNotifications={() => setIsDrawerOpen(true)}
          approvalRequired={true}
        />

        <main className="flex-1 overflow-y-auto bg-gradient-to-b from-[#090a0f] to-[#0c0e15]">
          <Routes>
            <Route path="/" element={<UploadQueue />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/processing" element={<Processing />} />
            <Route path="/upload-queue" element={<UploadQueue />} />
            <Route path="/videos" element={<Videos />} />
            <Route path="/videos/:id" element={<VideoDetail />} />
            <Route path="/calendar" element={<ContentCalendar />} />
            <Route path="/thumbnails" element={<Thumbnails />} />
            <Route path="/ideas" element={<Ideas />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/channel-brain" element={<ChannelBrain />} />
            <Route path="/monetization" element={<Monetization />} />
            <Route path="/automation" element={<Automation />} />
            <Route path="/auto-source" element={<AutoSource />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>

      {/* Slide-out Notification Drawer */}
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
