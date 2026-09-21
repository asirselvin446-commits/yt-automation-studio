import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  UploadCloud,
  Lightbulb,
  BrainCircuit,
  Settings,
  Radio,
  Sparkles,
  Users,
} from 'lucide-react';
import { YoutubeIcon } from '../common/YoutubeIcon';

interface SidebarProps {
  cloudIngestActive?: boolean;
  channelConnected?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ cloudIngestActive = true, channelConnected = false }) => {
  const navGroups = [
    {
      title: 'STUDIO',
      items: [
        { path: '/', label: 'Uploads', icon: UploadCloud },
        { path: '/auto-source', label: 'Auto-Source', icon: Sparkles },
        { path: '/accounts', label: 'Accounts', icon: Users },
        { path: '/ideas', label: 'Idea Lab', icon: Lightbulb },
        { path: '/channel-brain', label: 'Channel Brain', icon: BrainCircuit },
        { path: '/settings', label: 'Settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 h-screen bg-[#0d0f17] border-r border-[#1f2433] flex flex-col justify-between select-none z-20">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-[#1f2433] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-rose-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <YoutubeIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-wide text-white flex items-center gap-1.5">
                YT STUDIO
                <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-semibold border border-indigo-500/30">
                  DESKTOP
                </span>
              </h1>
              <p className="text-[11px] text-slate-400 font-medium">Cloud Studio Automation</p>
            </div>
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="p-3 space-y-6 overflow-y-auto max-h-[calc(100vh-180px)]">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-1">
              <p className="px-3 text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                {group.title}
              </p>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    className={({ isActive }) =>
                      `flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 ${
                        isActive
                          ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 shadow-sm'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-[#141824]'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* System Status Indicators */}
      <div className="p-3 border-t border-[#1f2433] bg-[#090b12] space-y-2">
        {/* Cloud Ingest Status */}
        <div className="flex items-center justify-between px-3 py-2 rounded-md bg-[#131622] border border-[#1e2336] text-[11px]">
          <div className="flex items-center space-x-2">
            <Radio className={`w-3.5 h-3.5 ${cloudIngestActive ? 'text-emerald-400 animate-pulse' : 'text-slate-400'}`} />
            <span className="text-slate-300 font-medium">Cloud Ingest</span>
          </div>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
              cloudIngestActive ? 'bg-emerald-500/15 text-emerald-400' : 'bg-slate-700/30 text-slate-400'
            }`}
          >
            {cloudIngestActive ? 'ACTIVE' : 'STANDBY'}
          </span>
        </div>

        {/* YouTube Status */}
        <div className="flex items-center justify-between px-3 py-2 rounded-md bg-[#131622] border border-[#1e2336] text-[11px]">
          <div className="flex items-center space-x-2">
            <YoutubeIcon className={`w-3.5 h-3.5 ${channelConnected ? 'text-rose-500' : 'text-slate-500'}`} />
            <span className="text-slate-300 font-medium">YouTube</span>
          </div>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
              channelConnected ? 'bg-rose-500/15 text-rose-400' : 'bg-slate-700/30 text-slate-400'
            }`}
          >
            {channelConnected ? 'CONNECTED' : 'STANDBY'}
          </span>
        </div>
      </div>
    </aside>
  );
};
