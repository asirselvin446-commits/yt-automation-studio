import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCircle2, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { api } from '../services/api';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // AI provider form state (Gemini is the only provider the app + cloud use)
  const [costPreset, setCostPreset] = useState('balanced');
  const [geminiKey, setGeminiKey] = useState('');

  const load = async () => {
    try {
      const res = await api.getSettings();
      setSettings(res);
      setCostPreset(res.ai_cost_preset || 'balanced');
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSaveAI = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setSaveMsg(null);
      await api.updateAiSettings({
        default_provider: 'gemini',
        ai_cost_preset: costPreset,
        gemini_key: geminiKey || undefined,
      });
      setSaveMsg('AI settings saved.');
      setGeminiKey('');
      load();
    } catch (e: any) {
      alert(`Error saving AI settings: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Studio Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Configure your AI providers. Manage YouTube accounts and upload folders on the{' '}
          <NavLink to="/accounts" className="text-indigo-400 hover:underline">Accounts</NavLink> page.
        </p>
      </div>

      {saveMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{saveMsg}</span>
        </div>
      )}

      {/* Pointer to Accounts for uploads */}
      <NavLink
        to="/accounts"
        className="flex items-center justify-between p-4 rounded-2xl bg-[#11141e] border border-[#1f2434] hover:border-indigo-500/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">YouTube Accounts & Upload Folders</div>
            <div className="text-[11px] text-slate-500">Connect channels, map folders to accounts, set visibility & schedule.</div>
          </div>
        </div>
        <span className="text-indigo-400 text-xs font-bold">Open →</span>
      </NavLink>

      {/* AI Provider Settings */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-5">
        <div className="flex items-center justify-between border-b border-[#1f2434] pb-3">
          <div className="flex items-center space-x-2.5">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-bold text-white">AI Provider Configuration</h2>
          </div>
        </div>

        <form onSubmit={handleSaveAI} className="space-y-4">
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">
              Gemini API Key {settings?.gemini_configured && <span className="text-emerald-400">✓ Active</span>}
            </label>
            <input
              type="password"
              placeholder={settings?.gemini_configured ? '•••••••••••••••• (leave blank to keep)' : 'Enter Gemini API key'}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
            />
            <p className="text-[11px] text-slate-500 mt-1.5">
              Powers titles, descriptions, tags and the Auto-Source scripts. The cloud worker uses its own
              key(s) set as GitHub secrets.
            </p>
          </div>

          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Quality preset</label>
            <select
              value={costPreset}
              onChange={(e) => setCostPreset(e.target.value)}
              className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="low_cost">Low Cost (Faster & Economical)</option>
              <option value="balanced">Balanced (Optimal Speed & Quality)</option>
              <option value="high_quality">High Quality (Max Detail & Depth)</option>
            </select>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors shadow-md shadow-indigo-600/20"
            >
              {saving ? 'Saving...' : 'Save AI settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
