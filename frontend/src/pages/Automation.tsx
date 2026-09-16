import React, { useState, useEffect } from 'react';
import { Sliders, ShieldCheck, AlertTriangle, CheckCircle2, HardDrive, Cpu, UploadCloud, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { AutomationSettings } from '../types';

export const Automation: React.FC = () => {
  const [settings, setSettings] = useState<AutomationSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const res = await api.getAutomationSettings();
      setSettings(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleToggle = (key: keyof AutomationSettings) => {
    if (!settings) return;

    // Safety guard: automatic upload warning
    if (key === 'auto_upload' && !settings.auto_upload) {
      const confirm = window.confirm(
        'CAUTION: Enabling Automatic Upload will allow videos to publish directly to your YouTube channel without human review. Are you sure?'
      );
      if (!confirm) return;
    }

    setSettings({
      ...settings,
      [key]: !settings[key],
    });
  };

  const handleSave = async () => {
    if (!settings) return;
    try {
      setSaving(true);
      setSaveMsg(null);
      await api.updateAutomationSettings(settings);
      setSaveMsg('Automation settings updated successfully.');
    } catch (e: any) {
      alert(`Save error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return <div className="p-8 text-xs text-slate-400">Loading automation settings...</div>;
  }

  const toggles = [
    {
      key: 'folder_monitoring' as const,
      label: 'Folder Monitoring (Watchdog)',
      desc: 'Continuously observe the local INBOX folder for newly dropped or rendered video files.',
      category: 'Ingestion',
    },
    {
      key: 'ai_analysis' as const,
      label: 'Automated AI Content Analysis',
      desc: 'Automatically run FFmpeg inspection and transcript-level content understanding upon file detection.',
      category: 'Ingestion',
    },
    {
      key: 'metadata_generation' as const,
      label: 'AI Title, Description & Tag Generation',
      desc: 'Synthesize 5 title candidates, description with chapters, and SEO keyword tags.',
      category: 'Content',
    },
    {
      key: 'thumbnail_generation' as const,
      label: 'Thumbnail Concept Generation',
      desc: 'Generate layout composition, focal rules, and text overlay ideas for thumbnails.',
      category: 'Content',
    },
    {
      key: 'approval_required' as const,
      label: 'Approval Required (Default)',
      desc: 'Strict safety: Require creator review and explicit approval before any YouTube upload action.',
      category: 'Safety',
      recommended: true,
    },
    {
      key: 'auto_upload' as const,
      label: 'Automatic Publishing',
      desc: 'Bypass human review and upload directly to YouTube when analysis completes. (Use with caution).',
      category: 'Safety',
      danger: true,
    },
    {
      key: 'analytics_sync' as const,
      label: 'YouTube Analytics Synchronization',
      desc: 'Automatically poll and archive official channel view, retention, and subscriber metrics.',
      category: 'Intelligence',
    },
    {
      key: 'ai_insights' as const,
      label: 'Channel Brain Insight Mining',
      desc: 'Periodically evaluate historical videos and generate actionable retention and topic suggestions.',
      category: 'Intelligence',
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Automation Center</h1>
          <p className="text-xs text-slate-400 mt-1">
            Configure pipeline autonomy rules, folder monitoring behaviors, and human-in-the-loop safety guards.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors shadow-md shadow-indigo-600/20"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {saveMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{saveMsg}</span>
        </div>
      )}

      {/* Safety Banner */}
      <div className="p-4 rounded-xl bg-[#11141e] border border-indigo-500/30 flex items-center space-x-3.5">
        <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-xs font-bold text-white">Default Mode: Human Approval Required</h4>
          <p className="text-[11px] text-slate-400 mt-0.5">
            The studio never blindly publishes videos unless you explicitly activate Automatic Publishing and confirm the danger warning.
          </p>
        </div>
      </div>

      {/* Toggles List */}
      <div className="space-y-3">
        {toggles.map((item) => {
          const isActive = Boolean(settings[item.key]);
          return (
            <div
              key={item.key}
              className={`p-5 rounded-xl border transition-all flex items-center justify-between gap-4 ${
                item.danger && isActive
                  ? 'bg-rose-950/20 border-rose-500/40'
                  : 'bg-[#11141e] border-[#1f2434]'
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <h3 className="text-xs font-bold text-white">{item.label}</h3>
                  {item.recommended && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      RECOMMENDED
                    </span>
                  )}
                  {item.danger && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      HIGH RISK
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed max-w-xl">{item.desc}</p>
              </div>

              {/* Toggle Switch */}
              <button
                onClick={() => handleToggle(item.key)}
                className={`w-12 h-6 rounded-full transition-colors relative shrink-0 p-0.5 ${
                  isActive ? (item.danger ? 'bg-rose-600' : 'bg-indigo-600') : 'bg-[#212638]'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white transition-transform ${
                    isActive ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
