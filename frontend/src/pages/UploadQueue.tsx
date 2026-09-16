import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Film,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { VideoListItem } from '../types';

export const UploadQueue: React.FC = () => {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const allVideos = await api.listVideos();
      // Filter for items awaiting approval or scheduled
      const queue = allVideos.filter(
        (v) => v.status === 'READY_FOR_APPROVAL' || v.status === 'APPROVED' || v.status === 'UPLOADING'
      );
      setVideos(queue);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (id: string) => {
    try {
      const res = await api.approveVideo(id);
      setActionMsg('Video approved! Moved to upload staging.');
      loadData();
    } catch (e: any) {
      setActionMsg(`Approval error: ${e.message}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.rejectVideo(id, 'Rejected from queue');
      setActionMsg('Video rejected and moved to FAILED directory.');
      loadData();
    } catch (e: any) {
      setActionMsg(`Rejection error: ${e.message}`);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Upload & Approval Queue</h1>
          <p className="text-xs text-slate-400 mt-1">
            Human-in-the-loop review workstation. Inspect AI metadata, verify quality checks, and approve uploads.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>Default: Approval Required</span>
          </div>
          <button
            onClick={loadData}
            className="p-2 rounded-lg bg-[#141724] border border-[#22283a] text-slate-300 hover:text-white"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {/* Queue Items */}
      {videos.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
          <CheckCircle2 className="w-8 h-8 text-emerald-500/50 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">Approval queue is empty</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Videos ready for review will appear here once AI metadata and technical checks finish processing.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {videos.map((v) => (
            <div
              key={v.id}
              className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] hover:border-[#2b334a] transition-all space-y-4 shadow-lg"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start space-x-4">
                  <div className="w-14 h-14 rounded-xl bg-[#181d2c] border border-[#252c42] flex items-center justify-center text-indigo-400 shrink-0">
                    <Film className="w-7 h-7" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2.5">
                      <h3 className="text-sm font-bold text-white">{v.title}</h3>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          v.status === 'READY_FOR_APPROVAL'
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                            : v.status === 'APPROVED'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                        }`}
                      >
                        {v.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-1">
                      {v.original_filename} • {(v.duration_seconds || 0).toFixed(1)}s •{' '}
                      {((v.file_size_bytes || 0) / (1024 * 1024)).toFixed(1)} MB
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2.5 shrink-0">
                  <Link
                    to={`/videos/${v.id}`}
                    className="px-3.5 py-2 rounded-lg bg-[#181d2c] border border-[#252c42] text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#20273b] transition-colors"
                  >
                    Inspect & Edit
                  </Link>
                  {v.status === 'READY_FOR_APPROVAL' && (
                    <>
                      <button
                        onClick={() => handleReject(v.id)}
                        className="px-3.5 py-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-400 hover:bg-rose-900/40 text-xs font-semibold transition-colors"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleApprove(v.id)}
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md transition-colors flex items-center space-x-1.5"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Approve & Stage</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
