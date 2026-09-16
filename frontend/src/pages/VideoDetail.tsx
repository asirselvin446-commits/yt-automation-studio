import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Film,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  ArrowLeft,
  ShieldCheck,
  Tag,
  FileText,
  Image,
  RefreshCw,
  Clock,
  Radio,
  Share2,
} from 'lucide-react';
import { api } from '../services/api';
import { VideoDetail as IVideoDetail } from '../types';

export const VideoDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [video, setVideo] = useState<IVideoDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadVideo = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await api.getVideo(id);
      setVideo(res);
    } catch (e: any) {
      console.error(e);
      setMessage(`Error loading video: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideo();
  }, [id]);

  const handleSelectTitle = async (titleId: string) => {
    if (!id) return;
    try {
      await api.selectTitle(id, titleId);
      loadVideo();
    } catch (e: any) {
      alert(`Error selecting title: ${e.message}`);
    }
  };

  const handleApprove = async () => {
    if (!id) return;
    try {
      setActionLoading(true);
      await api.approveVideo(id);
      setMessage('Video approved successfully! Moved to upload staging.');
      loadVideo();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    const reason = prompt('Please enter a rejection reason:');
    if (reason === null) return;
    try {
      setActionLoading(true);
      await api.rejectVideo(id, reason);
      setMessage('Video rejected and archived.');
      loadVideo();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerAi = async () => {
    if (!id) return;
    try {
      setActionLoading(true);
      await api.triggerAi(id);
      setMessage('AI metadata regenerated.');
      loadVideo();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 text-xs">
        Loading video workspace...
      </div>
    );
  }

  if (!video) {
    return (
      <div className="p-12 text-center space-y-4">
        <p className="text-slate-400 text-sm">Video not found.</p>
        <Link to="/videos" className="text-indigo-400 text-xs hover:underline">
          Back to library
        </Link>
      </div>
    );
  }

  const qc = video.quality_check;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Back button & Title header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg bg-[#141724] border border-[#22283a] text-slate-300 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-white tracking-tight">{video.title}</h1>
              <span
                className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                  video.status === 'READY_FOR_APPROVAL'
                    ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                    : video.status === 'APPROVED'
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'bg-slate-700/20 text-slate-400 border border-slate-700/40'
                }`}
              >
                {video.status.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              {video.original_filename} • {video.file_info?.duration_seconds.toFixed(1)}s •{' '}
              {video.file_info?.width}x{video.file_info?.height}
            </p>
          </div>
        </div>

        {/* Global Review Actions */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={handleTriggerAi}
            disabled={actionLoading}
            className="px-3.5 py-2 rounded-lg bg-[#161a27] border border-[#242b3e] text-slate-300 hover:text-white text-xs font-semibold flex items-center space-x-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Regenerate AI</span>
          </button>

          {video.status === 'READY_FOR_APPROVAL' && (
            <>
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="px-3.5 py-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-400 hover:bg-rose-900/40 text-xs font-semibold"
              >
                Reject
              </button>
              <button
                onClick={handleApprove}
                disabled={actionLoading || !qc?.can_upload}
                className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-md ${
                  qc?.can_upload
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                }`}
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Approve & Upload</span>
              </button>
            </>
          )}
        </div>
      </div>

      {message && (
        <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* Main Grid: Left details & Right Quality Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Content & Metadata Workspace */}
        <div className="lg:col-span-2 space-y-6">
          {/* 1. Title Candidates Picker */}
          <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
            <div className="flex items-center justify-between border-b border-[#1f2434] pb-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                AI Title Candidates (Choose 1)
              </h2>
              <span className="text-[11px] text-slate-500 font-medium">5 Generated</span>
            </div>

            <div className="space-y-3">
              {video.titles.map((t) => (
                <div
                  key={t.id || t.candidate_index}
                  onClick={() => t.id && handleSelectTitle(t.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    t.is_selected
                      ? 'bg-indigo-950/20 border-indigo-500/60 shadow-md shadow-indigo-950/20'
                      : 'bg-[#151926] border-[#212638] hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#1e2436] text-slate-400">
                          Option {t.candidate_index}
                        </span>
                        <span className="text-[10px] font-medium text-slate-500 font-mono">
                          {t.character_length} chars
                        </span>
                        <span className="text-[10px] font-medium text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                          {t.estimated_intent}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-white">{t.title_text}</h3>
                      {t.reasoning && (
                        <p className="text-[11px] text-slate-400 leading-relaxed mt-1">
                          {t.reasoning}
                        </p>
                      )}
                    </div>
                    <div
                      className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 mt-1 ${
                        t.is_selected
                          ? 'border-indigo-400 bg-indigo-500'
                          : 'border-slate-600'
                      }`}
                    >
                      {t.is_selected && <div className="w-1.5 h-1.5 bg-white rounded-full" />}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 2. Description & Chapters */}
          <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              Generated Description & Chapters
            </h2>
            <div className="space-y-3">
              <div>
                <span className="text-[11px] text-slate-500 font-semibold block mb-1">
                  Short Hook (Above Fold)
                </span>
                <p className="text-xs text-slate-300 p-3 rounded-lg bg-[#151926] border border-[#212638]">
                  {video.description?.short_description || 'N/A'}
                </p>
              </div>
              <div>
                <span className="text-[11px] text-slate-500 font-semibold block mb-1">
                  Long Description
                </span>
                <p className="text-xs text-slate-300 p-3 rounded-lg bg-[#151926] border border-[#212638] whitespace-pre-line leading-relaxed">
                  {video.description?.long_description || 'N/A'}
                </p>
              </div>
              {video.description?.chapters && video.description.chapters.length > 0 && (
                <div>
                  <span className="text-[11px] text-slate-500 font-semibold block mb-1">
                    Detected Chapters
                  </span>
                  <div className="grid grid-cols-2 gap-2">
                    {video.description.chapters.map((ch, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-[#151926] border border-[#212638] text-[11px] flex items-center space-x-2 font-mono"
                      >
                        <span className="text-indigo-400 font-bold">{ch.timestamp}</span>
                        <span className="text-slate-300 truncate">{ch.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 3. Tags & Keywords */}
          <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Tag className="w-4 h-4 text-amber-400" />
              SEO Tags & Search Keywords
            </h2>
            <div className="flex flex-wrap gap-2">
              {video.tags?.primary_keywords.map((tg, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-md bg-[#161b29] border border-amber-500/20 text-amber-300 text-xs font-mono"
                >
                  {tg}
                </span>
              ))}
              {video.tags?.secondary_keywords.map((tg, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-md bg-[#161b29] border border-[#232a3e] text-slate-400 text-xs font-mono"
                >
                  {tg}
                </span>
              ))}
            </div>
          </div>

          {/* 4. Thumbnail Concepts */}
          <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Image className="w-4 h-4 text-rose-400" />
              Thumbnail Concepts Workspace
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {video.thumbnails.map((th, idx) => (
                <div
                  key={th.id || idx}
                  className={`p-4 rounded-xl border space-y-2 ${
                    th.is_selected
                      ? 'bg-indigo-950/20 border-indigo-500/50'
                      : 'bg-[#151926] border-[#212638]'
                  }`}
                >
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#1e2436] text-slate-400">
                    Concept {idx + 1}
                  </span>
                  <h4 className="text-xs font-bold text-white">{th.concept_title}</h4>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {th.visual_composition}
                  </p>
                  {th.text_suggestions && (
                    <div className="pt-1">
                      <span className="text-[10px] text-slate-500 block">Text Overlay Idea:</span>
                      <span className="text-[11px] font-bold text-amber-400 font-mono">
                        "{th.text_suggestions}"
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Quality Check Matrix */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-5 sticky top-24 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#1f2434] pb-4">
              <div>
                <h3 className="text-sm font-bold text-white">Quality Inspection</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">Pre-upload rule matrix</p>
              </div>
              <span
                className={`px-2.5 py-1 rounded text-xs font-black tracking-wider ${
                  qc?.overall_status === 'READY'
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : qc?.overall_status === 'WARNING'
                    ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                    : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                }`}
              >
                {qc?.overall_status || 'PENDING'}
              </span>
            </div>

            {/* Checklist Matrix */}
            <div className="space-y-3">
              {qc?.checks.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-[#151926] border border-[#212638] flex items-start space-x-3 text-xs"
                >
                  <div className="mt-0.5 shrink-0">
                    {item.status === 'VALID' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : item.status === 'WARNING' ? (
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-400" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-white">{item.name}</span>
                      <span
                        className={`text-[9px] font-bold px-1 rounded ${
                          item.status === 'VALID'
                            ? 'text-emerald-400'
                            : item.status === 'WARNING'
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">{item.message}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Upload blocker status note */}
            <div className="p-3 rounded-lg bg-[#141724] border border-[#22283a] text-[11px] text-slate-400">
              {qc?.can_upload ? (
                <span className="text-emerald-400 font-medium">
                  ✓ Passed verification. Ready for creator approval.
                </span>
              ) : (
                <span className="text-rose-400 font-medium">
                  ⚠ Upload blocked. Resolve BLOCKED items above before publishing.
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
