import React, { useEffect, useRef, useState } from 'react';
import {
  Sparkles,
  Loader2,
  Play,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Wand2,
  Power,
  Cloud,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';

const EDGE_VOICES = [
  { id: 'en-US-AriaNeural', label: 'Aria — US female (warm)' },
  { id: 'en-US-GuyNeural', label: 'Guy — US male (clear)' },
  { id: 'en-US-JennyNeural', label: 'Jenny — US female (friendly)' },
  { id: 'en-GB-RyanNeural', label: 'Ryan — UK male' },
  { id: 'en-GB-SoniaNeural', label: 'Sonia — UK female' },
  { id: 'en-AU-NatashaNeural', label: 'Natasha — AU female' },
];

// Daily upload time is stored as UTC "HH:MM" but shown/edited in local time.
const utcToLocalTime = (utc: string): string => {
  if (!utc || !utc.includes(':')) return '';
  const [h, m] = utc.split(':').map(Number);
  const d = new Date();
  d.setUTCHours(h, m, 0, 0);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};
const localToUtcTime = (local: string): string => {
  if (!local || !local.includes(':')) return '';
  const [h, m] = local.split(':').map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

const statusBadge = (s: string) => {
  switch ((s || '').toUpperCase()) {
    case 'DONE':
    case 'UPLOADED':
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    case 'RUNNING':
      return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
    case 'FAILED':
      return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
    default:
      return 'bg-slate-700/20 text-slate-400 border-slate-700/40';
  }
};

export const AutoSource: React.FC = () => {
  const DEFAULT_CFG = {
    enabled: false, niche: 'amazing facts', per_day: 1, format: 'shorts',
    account_id: '', provider: 'edge', voice: 'en-US-AriaNeural',
    fish_voice: '', fish_api_key_set: false, pexels_api_key_set: false,
    post_time_utc: '',
  };
  const [cfg, setCfg] = useState<any>(DEFAULT_CFG);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [githubReady, setGithubReady] = useState(true);
  const [supabaseOk, setSupabaseOk] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const firstLoad = useRef(true);

  const load = async () => {
    try {
      const res = await api.getAutosource();
      // Preserve in-progress edits: only seed the form on first load.
      if (firstLoad.current) {
        setCfg(res.config);
        firstLoad.current = false;
      }
      setRuns(res.runs || []);
      setGithubReady(res.github_ready);
      setSupabaseOk(res.supabase_configured);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
    api.listAccounts().then((r) => setAccounts(r.accounts || [])).catch(() => {});
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, []);

  const patch = (k: string, v: any) => setCfg((c: any) => ({ ...c, [k]: v }));

  const save = async (overrides: Record<string, any> = {}) => {
    setSaving(true);
    setMsg(null);
    try {
      const payload = {
        enabled: cfg.enabled,
        niche: cfg.niche,
        per_day: cfg.per_day,
        format: cfg.format,
        account_id: cfg.account_id || '',
        post_time_utc: cfg.post_time_utc || '',
        provider: cfg.provider,
        voice: cfg.voice,
        fish_voice: cfg.fish_voice,
        ...(cfg._fishKey ? { fish_api_key: cfg._fishKey } : {}),
        ...(cfg._pexelsKey ? { pexels_api_key: cfg._pexelsKey } : {}),
        ...overrides,
      };
      const res = await api.setAutosourceConfig(payload);
      setCfg({ ...res.config, _fishKey: '', _pexelsKey: '' });
      setMsg('Saved.');
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async () => {
    const next = !cfg.enabled;
    patch('enabled', next);
    await save({ enabled: next });
  };

  const generate = async () => {
    setGenerating(true);
    setMsg(null);
    try {
      const res = await api.generateAutosource();
      setMsg(res.reason);
      setTimeout(load, 1500);
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-indigo-400" /> Auto-Source Engine
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Generates original, copyright-safe videos in the cloud and uploads them to
            YouTube on a schedule — running 24/7 even when this laptop is off.
          </p>
        </div>
        <button
          onClick={toggleEnabled}
          disabled={saving}
          className={`px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 border transition-all disabled:opacity-60 ${
            cfg.enabled
              ? 'bg-emerald-600/20 text-emerald-300 border-emerald-500/40 hover:bg-emerald-600/30'
              : 'bg-slate-700/20 text-slate-300 border-slate-600/40 hover:bg-slate-700/40'
          }`}
        >
          <Power className="w-4 h-4" />
          {cfg.enabled ? 'Engine ON' : 'Engine OFF'}
        </button>
      </div>

      {/* Setup warnings */}
      {!supabaseOk && (
        <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          Add your Supabase keys in Settings — the engine stores its config and status there.
        </div>
      )}
      {!githubReady && (
        <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          GitHub isn't connected (GITHUB_TOKEN / GITHUB_REPO). The daily schedule still works,
          but the "Generate one now" button needs it.
        </div>
      )}
      {msg && (
        <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" /> {msg}
        </div>
      )}

      {/* Config card */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-5">
        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Niche / topic</label>
            <input
              value={cfg.niche || ''}
              onChange={(e) => patch('niche', e.target.value)}
              placeholder="e.g. space facts, history mysteries, ocean life"
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
            />
            <p className="text-[11px] text-slate-500 mt-1.5">The engine picks a fresh topic in this niche each time.</p>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Videos per day</label>
            <select
              value={cfg.per_day}
              onChange={(e) => patch('per_day', Number(e.target.value))}
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
            >
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>{n} / day{n > 1 ? ' (drip-scheduled)' : ''}</option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500 mt-1.5">Extra videos are auto-spread across the day via YouTube scheduling.</p>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Format</label>
            <select
              value={cfg.format || 'shorts'}
              onChange={(e) => patch('format', e.target.value)}
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
            >
              <option value="shorts">Shorts — 9:16 vertical, under 60s</option>
              <option value="landscape">Landscape — 16:9 horizontal</option>
            </select>
            <p className="text-[11px] text-slate-500 mt-1.5">Shorts get the #Shorts tag automatically.</p>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Daily upload time</label>
            <input
              type="time"
              value={utcToLocalTime(cfg.post_time_utc || '')}
              onChange={(e) => patch('post_time_utc', localToUtcTime(e.target.value))}
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
            />
            <p className="text-[11px] text-slate-500 mt-1.5">
              {cfg.post_time_utc
                ? 'Your local time. Posts around then (checked hourly).'
                : 'Empty = as soon as possible each day.'}
            </p>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Post to account</label>
            <select
              value={cfg.account_id || ''}
              onChange={(e) => patch('account_id', e.target.value)}
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
            >
              <option value="">
                {accounts.find((a) => a.is_primary)?.title
                  ? `${accounts.find((a) => a.is_primary)?.title} (default)`
                  : 'Default account'}
              </option>
              {accounts.filter((a) => !a.is_primary).map((a) => (
                <option key={a.id} value={a.id}>{a.title}</option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500 mt-1.5">Add accounts on the Accounts page.</p>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Voice engine</label>
            <select
              value={cfg.provider}
              onChange={(e) => patch('provider', e.target.value)}
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
            >
              <option value="edge">edge-tts — free & unlimited</option>
              <option value="fish">Fish Audio — nicer (falls back to free)</option>
            </select>
          </div>

          {cfg.provider === 'edge' ? (
            <div>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Narration voice</label>
              <select
                value={cfg.voice || EDGE_VOICES[0].id}
                onChange={(e) => patch('voice', e.target.value)}
                className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
              >
                {EDGE_VOICES.map((v) => (
                  <option key={v.id} value={v.id}>{v.label}</option>
                ))}
              </select>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Fish Audio API key {cfg.fish_api_key_set && <span className="text-emerald-400">✓ saved</span>}
                </label>
                <input
                  type="password"
                  value={cfg._fishKey || ''}
                  onChange={(e) => patch('_fishKey', e.target.value)}
                  placeholder={cfg.fish_api_key_set ? '•••••• (leave blank to keep)' : 'paste key'}
                  className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Fish voice id (optional)</label>
                <input
                  value={cfg.fish_voice || ''}
                  onChange={(e) => patch('fish_voice', e.target.value)}
                  placeholder="reference_id"
                  className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Stock footage key — turns still images into real B-roll video */}
        <div className="p-4 rounded-xl bg-[#0d0f17] border border-[#1f2434]">
          <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Stock footage — Pexels API key {cfg.pexels_api_key_set && <span className="text-emerald-400">✓ saved</span>}
          </label>
          <input
            type="password"
            value={cfg._pexelsKey || ''}
            onChange={(e) => patch('_pexelsKey', e.target.value)}
            placeholder={cfg.pexels_api_key_set ? '•••••• (leave blank to keep)' : 'paste your free Pexels key'}
            className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#11141e] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none"
          />
          <p className="text-[11px] text-slate-500 mt-1.5">
            Free key from{' '}
            <a href="https://www.pexels.com/api/" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">pexels.com/api</a>.
            With a key, each line uses real licensed video footage. Without one, it falls back to AI images.
          </p>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={() => save()}
            disabled={saving}
            className="px-4 py-2.5 rounded-lg bg-[#1a1f2e] border border-[#2b334a] text-slate-200 hover:text-white hover:border-indigo-500/40 text-xs font-bold flex items-center gap-2 disabled:opacity-60"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Save settings
          </button>
          <button
            onClick={generate}
            disabled={generating || !cfg.enabled}
            title={!cfg.enabled ? 'Turn the engine on first' : 'Generate one video now'}
            className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-2 disabled:opacity-50"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
            Generate one now
          </button>
        </div>
      </div>

      {/* Live runs */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            Recent generations
            <span className="inline-flex items-center gap-1 text-emerald-400 text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
            </span>
          </h2>
          <button onClick={load} className="p-2 rounded-lg bg-[#141724] border border-[#22283a] text-slate-300 hover:text-white">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {runs.length === 0 ? (
          <div className="p-10 text-center rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-2">
            <Cloud className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs text-slate-500">
              No videos yet. Turn the engine on, pick a niche, and hit <b>Generate one now</b> —
              or wait for the daily run.
            </p>
          </div>
        ) : (
          runs.map((r) => (
            <div key={r.id} className="p-4 rounded-2xl bg-[#11141e] border border-[#1f2434] flex items-center justify-between gap-3">
              <div className="min-w-0 flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#181d2c] border border-[#252c42] flex items-center justify-center text-indigo-400 shrink-0">
                  {(r.status || '').toUpperCase() === 'RUNNING' ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-white truncate">{r.title || r.topic || r.niche || 'Generating…'}</h3>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border shrink-0 ${statusBadge(r.status)}`}>
                      {(r.status || '').toUpperCase()}
                    </span>
                  </div>
                  {(r.status || '').toUpperCase() === 'RUNNING' && r.stage && (
                    <p className="text-[11px] text-blue-300 mt-0.5 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {r.stage}…
                    </p>
                  )}
                  {r.publish_at && (r.status || '').toUpperCase() === 'DONE' && (
                    <p className="text-[11px] text-slate-500 mt-0.5">Scheduled public: {new Date(r.publish_at).toLocaleString()}</p>
                  )}
                  {(r.status || '').toUpperCase() === 'FAILED' && r.error && (
                    <p className="text-[11px] text-rose-400/80 mt-0.5 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 shrink-0" /> {String(r.error).slice(0, 120)}
                    </p>
                  )}
                </div>
              </div>
              {r.youtube_url && (
                <a
                  href={r.youtube_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold flex items-center gap-1.5 shrink-0"
                >
                  <Play className="w-4 h-4 fill-current" /> Watch
                </a>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
