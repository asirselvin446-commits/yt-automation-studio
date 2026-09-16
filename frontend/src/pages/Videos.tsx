import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Film, Search, Filter, ArrowRight, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { VideoListItem } from '../types';

export const Videos: React.FC = () => {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.listVideos(filter === 'ALL' ? undefined : filter);
        setVideos(res);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filter]);

  const filteredVideos = videos.filter((v) =>
    v.title.toLowerCase().includes(search.toLowerCase()) ||
    v.original_filename.toLowerCase().includes(search.toLowerCase())
  );

  const statuses = ['ALL', 'INBOX', 'PROCESSING', 'READY_FOR_APPROVAL', 'APPROVED', 'UPLOADED', 'FAILED'];

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Video Library</h1>
          <p className="text-xs text-slate-400 mt-1">
            Complete catalogue of all ingested, staged, and uploaded YouTube videos.
          </p>
        </div>
        <Link
          to="/inbox"
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors shrink-0"
        >
          + Add New Video
        </Link>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-[#11141e] border border-[#1f2434]">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by title or filename..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#161a27] border border-[#23293d] rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Status Filter Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          {statuses.map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                filter === st
                  ? 'bg-indigo-600 text-white'
                  : 'bg-[#161a27] text-slate-400 hover:text-white hover:bg-[#1d2233]'
              }`}
            >
              {st.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Videos Grid */}
      {filteredVideos.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#11141e] border border-[#1f2434] text-slate-500 text-xs">
          No videos found matching your filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredVideos.map((v) => (
            <Link
              key={v.id}
              to={`/videos/${v.id}`}
              className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] hover:border-indigo-500/40 studio-card-glow transition-all duration-200 flex flex-col justify-between space-y-4 group"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      v.status === 'UPLOADED'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                        : v.status === 'READY_FOR_APPROVAL'
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                        : 'bg-slate-700/20 text-slate-400 border border-slate-700/30'
                    }`}
                  >
                    {v.status.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {(v.duration_seconds || 0).toFixed(1)}s
                  </span>
                </div>
                <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-2">
                  {v.title}
                </h3>
                <p className="text-xs text-slate-400 font-mono truncate">{v.original_filename}</p>
              </div>

              <div className="pt-3 border-t border-[#1d2233] flex items-center justify-between text-xs text-slate-400">
                <span>{new Date(v.created_at).toLocaleDateString()}</span>
                <div className="flex items-center space-x-1 text-indigo-400 group-hover:translate-x-1 transition-transform">
                  <span>Manage</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
