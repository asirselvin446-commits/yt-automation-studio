import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FolderInput,
  Cpu,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Clock,
  Eye,
  Users,
  Film,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { YoutubeIcon } from '../components/common/YoutubeIcon';
import { api } from '../services/api';
import { FolderStats, ChannelInfo, VideoListItem } from '../types';

export const Dashboard: React.FC = () => {
  const [folderStats, setFolderStats] = useState<FolderStats | null>(null);
  const [channel, setChannel] = useState<ChannelInfo | null>(null);
  const [recentVideos, setRecentVideos] = useState<VideoListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [stats, ch, vids] = await Promise.all([
        api.getFolderStats(),
        api.getChannelStatus(),
        api.listVideos(),
      ]);
      setFolderStats(stats);
      setChannel(ch);
      setRecentVideos(vids.slice(0, 5));
    } catch (err) {
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const pipelineCards = [
    {
      title: 'Inbox',
      count: folderStats?.inbox_count || 0,
      label: 'New Videos Detected',
      icon: FolderInput,
      path: '/inbox',
      color: 'from-blue-600/20 to-blue-500/5 text-blue-400 border-blue-500/30',
    },
    {
      title: 'Processing',
      count: folderStats?.processing_count || 0,
      label: 'AI & Media Analysis',
      icon: Cpu,
      path: '/processing',
      color: 'from-amber-600/20 to-amber-500/5 text-amber-400 border-amber-500/30',
    },
    {
      title: 'Upload Queue',
      count: folderStats?.approved_count || 0,
      label: 'Approved & Staged',
      icon: UploadCloud,
      path: '/upload-queue',
      color: 'from-indigo-600/20 to-indigo-500/5 text-indigo-400 border-indigo-500/30',
    },
    {
      title: 'Uploaded',
      count: folderStats?.uploaded_count || 0,
      label: 'Live on YouTube',
      icon: CheckCircle2,
      path: '/videos',
      color: 'from-emerald-600/20 to-emerald-500/5 text-emerald-400 border-emerald-500/30',
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner if YouTube Disconnected */}
      {!channel?.is_connected && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-rose-950/40 via-[#16131c] to-indigo-950/30 border border-rose-500/30 flex items-center justify-between shadow-lg">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30">
              <YoutubeIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-white">YouTube Channel Disconnected</h3>
              <p className="text-xs text-slate-400">
                Connect your YouTube channel in Settings to view official analytics and enable one-click uploads.
              </p>
            </div>
          </div>
          <Link
            to="/settings"
            className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md transition-colors"
          >
            Connect YouTube
          </Link>
        </div>
      )}

      {/* Header with Quick Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Studio Overview</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time status of your local video ingestion pipeline and channel workflow.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-[#141724] border border-[#22283a] text-slate-300 hover:text-white hover:bg-[#1a1f30] text-xs font-medium transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Ingestion Pipeline Funnel */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {pipelineCards.map((c) => {
          const Icon = c.icon;
          return (
            <Link
              key={c.title}
              to={c.path}
              className={`p-5 rounded-xl border bg-gradient-to-br ${c.color} studio-card-glow transition-all duration-200 block group`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wide uppercase text-slate-400">
                  {c.title}
                </span>
                <Icon className="w-4 h-4 opacity-80 group-hover:scale-110 transition-transform" />
              </div>
              <div className="mt-3">
                <span className="text-3xl font-extrabold text-white">{c.count}</span>
                <p className="text-[11px] text-slate-400 mt-1">{c.label}</p>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Official Channel Metrics (Zero Fake Stats) */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <div className="flex items-center justify-between border-b border-[#1f2434] pb-4">
          <div className="flex items-center space-x-2.5">
            <YoutubeIcon className="w-5 h-5 text-rose-500" />
            <h2 className="text-sm font-bold text-white tracking-wide">
              {channel?.is_connected ? channel.title : 'Channel Analytics'}
            </h2>
            {channel?.is_connected && (
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 text-[10px] font-semibold border border-emerald-500/20">
                LIVE API
              </span>
            )}
          </div>
          <Link
            to="/analytics"
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
          >
            <span>Full Analytics</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {channel?.is_connected ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-[#151926] border border-[#212638]">
              <div className="flex items-center space-x-2 text-slate-400 text-xs">
                <Users className="w-4 h-4 text-indigo-400" />
                <span>Subscribers</span>
              </div>
              <p className="text-xl font-bold text-white mt-2">
                {channel.subscriber_count?.toLocaleString() || '0'}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-[#151926] border border-[#212638]">
              <div className="flex items-center space-x-2 text-slate-400 text-xs">
                <Eye className="w-4 h-4 text-emerald-400" />
                <span>Total Views</span>
              </div>
              <p className="text-xl font-bold text-white mt-2">
                {channel.view_count?.toLocaleString() || '0'}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-[#151926] border border-[#212638]">
              <div className="flex items-center space-x-2 text-slate-400 text-xs">
                <Film className="w-4 h-4 text-amber-400" />
                <span>Total Videos</span>
              </div>
              <p className="text-xl font-bold text-white mt-2">{channel.video_count || 0}</p>
            </div>
            <div className="p-4 rounded-xl bg-[#151926] border border-[#212638]">
              <div className="flex items-center space-x-2 text-slate-400 text-xs">
                <Clock className="w-4 h-4 text-rose-400" />
                <span>Custom URL</span>
              </div>
              <p className="text-sm font-semibold text-white mt-2 truncate">
                {channel.custom_url || 'N/A'}
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-10 text-slate-400 space-y-2">
            <p className="text-sm">Connect your official YouTube account to view real subscriber count, views, and watch hours.</p>
            <p className="text-xs text-slate-500">No mock numbers or simulated metrics are displayed.</p>
          </div>
        )}
      </div>

      {/* Recent Videos List */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <div className="flex items-center justify-between border-b border-[#1f2434] pb-4">
          <h2 className="text-sm font-bold text-white tracking-wide">Recent Video Pipeline</h2>
          <Link
            to="/videos"
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {recentVideos.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No videos in pipeline yet. Drop an MP4, MOV, or MKV file into your watched INBOX folder.
          </div>
        ) : (
          <div className="divide-y divide-[#1f2434]">
            {recentVideos.map((v) => (
              <Link
                key={v.id}
                to={`/videos/${v.id}`}
                className="py-3.5 flex items-center justify-between hover:bg-[#151926] px-3 rounded-lg transition-colors group"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-lg bg-[#181d2e] border border-[#252b40] flex items-center justify-center text-slate-400 group-hover:text-indigo-400">
                    <Film className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-white group-hover:text-indigo-300 transition-colors">
                      {v.title}
                    </h4>
                    <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                      {v.original_filename} • {(v.duration_seconds || 0).toFixed(1)}s
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <span
                    className={`px-2.5 py-1 rounded text-[10px] font-bold ${
                      v.status === 'READY_FOR_APPROVAL'
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : v.status === 'UPLOADED'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : v.status === 'PROCESSING'
                        ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                        : 'bg-slate-700/20 text-slate-400 border border-slate-700/40'
                    }`}
                  >
                    {v.status.replace(/_/g, ' ')}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-white transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
