import React from 'react';
import { Bell, Folder, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react';
import { StudioNotification } from '../../types';

interface HeaderProps {
  title: string;
  inboxPath?: string;
  notifications: StudioNotification[];
  onOpenNotifications: () => void;
  approvalRequired?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  inboxPath = 'D:\\YT-Automation\\INBOX',
  notifications,
  onOpenNotifications,
  approvalRequired = true,
}) => {
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <header className="h-16 px-6 bg-[#0c0e16]/80 backdrop-blur-md border-b border-[#1f2433] flex items-center justify-between sticky top-0 z-10">
      {/* Title & Path */}
      <div className="flex items-center space-x-4">
        <h2 className="text-lg font-bold text-white tracking-tight">{title}</h2>
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#151824] border border-[#23293d] text-[11px] text-slate-400 font-mono">
          <Folder className="w-3.5 h-3.5 text-indigo-400" />
          <span className="truncate max-w-xs">{inboxPath}</span>
        </div>
      </div>

      {/* Badges & Actions */}
      <div className="flex items-center space-x-3">
        {/* Safety Mode Badge */}
        <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>{approvalRequired ? 'Approval Required' : 'Auto-Publish'}</span>
        </div>

        {/* Notification Bell */}
        <button
          onClick={onOpenNotifications}
          className="relative p-2 rounded-lg bg-[#151824] border border-[#23293d] text-slate-300 hover:text-white hover:bg-[#1a1f30] transition-colors"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-indigo-600 text-white rounded-full text-[10px] font-bold flex items-center justify-center animate-pulse">
              {unreadCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};
