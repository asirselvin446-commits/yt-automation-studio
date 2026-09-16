import React, { useState, useEffect } from 'react';
import { FolderInput, Upload, FileVideo, CheckCircle, RefreshCw, HardDrive, Info } from 'lucide-react';
import { api } from '../services/api';
import { FolderStats } from '../types';

export const Inbox: React.FC = () => {
  const [stats, setStats] = useState<FolderStats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      const res = await api.getFolderStats();
      setStats(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      await uploadFile(file);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      await uploadFile(file);
    }
  };

  const uploadFile = async (file: File) => {
    try {
      setUploading(true);
      setUploadMsg(null);
      const res = await api.manualIngest(file);
      setUploadMsg(`Successfully deposited '${file.name}' into INBOX folder.`);
      loadStats();
    } catch (err: any) {
      setUploadMsg(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Video Inbox</h1>
        <p className="text-xs text-slate-400 mt-1">
          Drop video files into your local Windows folder or directly upload here to initiate AI analysis.
        </p>
      </div>

      {/* Local Folder Location Card */}
      <div className="p-5 rounded-xl bg-[#11141e] border border-[#1f2434] flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider block">
              Watched Windows INBOX Directory
            </span>
            <p className="text-xs font-mono text-white mt-0.5">
              {stats?.root ? `${stats.root}\\INBOX` : 'Configuring...'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className="px-3 py-1 rounded-full bg-blue-500/15 text-blue-400 text-xs font-semibold border border-blue-500/20">
            {stats?.inbox_count || 0} Files in INBOX
          </span>
          <button
            onClick={loadStats}
            className="p-2 rounded-lg bg-[#151926] border border-[#212638] text-slate-300 hover:text-white"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className="p-12 border-2 border-dashed border-[#262c42] hover:border-indigo-500/50 rounded-2xl bg-[#0f111a]/70 flex flex-col items-center justify-center space-y-4 transition-all duration-200 group cursor-pointer relative"
      >
        <input
          type="file"
          accept=".mp4,.mov,.mkv,.avi,.webm"
          onChange={handleFileChange}
          className="absolute inset-0 opacity-0 cursor-pointer"
          disabled={uploading}
        />
        <div className="w-16 h-16 rounded-full bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 group-hover:bg-indigo-600/20 transition-all">
          <Upload className="w-7 h-7" />
        </div>
        <div className="text-center">
          <h3 className="text-sm font-bold text-white">
            {uploading ? 'Ingesting Video...' : 'Drag & drop your video file here'}
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            or click to browse from Windows Explorer (MP4, MOV, MKV, AVI, WEBM)
          </p>
        </div>
        <div className="flex items-center space-x-2 text-[11px] text-slate-500">
          <FileVideo className="w-3.5 h-3.5" />
          <span>Windows Watcher automatically detects copied files and moves them to PROCESSING</span>
        </div>
      </div>

      {uploadMsg && (
        <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 text-indigo-300 text-xs flex items-center space-x-2">
          <CheckCircle className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>{uploadMsg}</span>
        </div>
      )}

      {/* Workflow Explainer */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Info className="w-4 h-4 text-indigo-400" />
          How INBOX Automation Operates
        </h3>
        <ul className="text-xs text-slate-400 space-y-2 list-disc list-inside leading-relaxed">
          <li>The Windows Watcher monitors the INBOX folder continuously.</li>
          <li>When you paste or render a video into INBOX, the system waits until Windows completes the file write.</li>
          <li>A SHA-256 hash is computed to verify duplicate prevention before any AI analysis starts.</li>
          <li>Media technical metadata is extracted using FFmpeg, and the file moves automatically to <span className="font-mono text-slate-300">PROCESSING</span>.</li>
        </ul>
      </div>
    </div>
  );
};
