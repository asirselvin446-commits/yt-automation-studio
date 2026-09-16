import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Cpu, RefreshCw, Film, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { VideoListItem } from '../types';

export const Processing: React.FC = () => {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.listVideos('PROCESSING');
      setVideos(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Processing Queue</h1>
          <p className="text-xs text-slate-400 mt-1">
            Media currently undergoing FFmpeg technical inspection, transcription, and AI metadata generation.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141724] border border-[#22283a] text-slate-300 hover:text-white text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {videos.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
          <Cpu className="w-8 h-8 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No active processing jobs</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Drop a video file into your INBOX folder to automatically trigger the media analysis and AI pipeline.
          </p>
          <Link
            to="/inbox"
            className="inline-block mt-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
          >
            Go to Inbox
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {videos.map((v) => (
            <div
              key={v.id}
              className="p-5 rounded-xl bg-[#11141e] border border-blue-500/30 space-y-4 shadow-lg shadow-blue-950/10"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{v.title}</h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      {v.original_filename} • {(v.duration_seconds || 0).toFixed(1)}s
                    </p>
                  </div>
                </div>
                <Link
                  to={`/videos/${v.id}`}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#181d2c] border border-[#262e44] text-xs text-indigo-400 hover:text-white"
                >
                  <span>View Details</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Progress Steps */}
              <div className="grid grid-cols-4 gap-2 pt-2 text-[11px]">
                <div className="p-2.5 rounded-lg bg-[#141824] border border-emerald-500/20 text-emerald-400 flex items-center space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>FFmpeg Validation</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#141824] border border-emerald-500/20 text-emerald-400 flex items-center space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>Deduplication</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#141824] border border-blue-500/30 text-blue-300 flex items-center space-x-2 animate-pulse">
                  <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
                  <span>AI Metadata</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#141824] border border-[#1f2538] text-slate-500 flex items-center space-x-2">
                  <span className="w-3.5 h-3.5 rounded-full border border-slate-600 inline-block shrink-0" />
                  <span>Thumbnail Gen</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
