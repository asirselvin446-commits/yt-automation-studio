import React from 'react';
import { X, Check, Bell, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';
import { StudioNotification } from '../../types';

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: StudioNotification[];
  onMarkRead: (id: string) => void;
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  isOpen,
  onClose,
  notifications,
  onMarkRead,
}) => {
  if (!isOpen) return null;

  const getIcon = (type: string, severity: string) => {
    if (severity === 'ERROR') return <AlertTriangle className="w-4 h-4 text-rose-400" />;
    if (severity === 'WARNING') return <AlertTriangle className="w-4 h-4 text-amber-400" />;
    if (severity === 'SUCCESS') return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    return <Info className="w-4 h-4 text-indigo-400" />;
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="w-96 h-full bg-[#10131d] border-l border-[#222738] shadow-2xl flex flex-col justify-between">
        {/* Header */}
        <div className="p-4 border-b border-[#222738] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Bell className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-sm text-white">Notifications</h3>
            <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-medium">
              {notifications.length}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-[#1a1f30]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {notifications.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No recent notifications.
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`p-3 rounded-lg border transition-all ${
                  n.is_read
                    ? 'bg-[#141724]/40 border-[#1f2438]/50 opacity-70'
                    : 'bg-[#151928] border-indigo-500/30 shadow-sm'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start space-x-2">
                    <div className="mt-0.5">{getIcon(n.notification_type, n.severity)}</div>
                    <div>
                      <h4 className="text-xs font-semibold text-white">{n.title}</h4>
                      <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{n.message}</p>
                      <span className="text-[10px] text-slate-500 block mt-2">
                        {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                  {!n.is_read && (
                    <button
                      onClick={() => onMarkRead(n.id)}
                      className="p-1 rounded text-slate-400 hover:text-emerald-400 hover:bg-[#1f263d] transition-colors"
                      title="Mark as read"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[#222738] bg-[#0c0e17] text-center text-[11px] text-slate-500">
          Studio Notification Stream
        </div>
      </div>
    </div>
  );
};
