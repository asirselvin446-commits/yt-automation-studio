import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCircle2, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { api } from '../services/api';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // AI provider form state
  const [defaultProvider, setDefaultProvider] = useState('gemini');
  const [costPreset, setCostPreset] = useState('balanced');
  const [geminiKey, setGeminiKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [localAiUrl, setLocalAiUrl] = useState('http://localhost:11434/v1');

  const load = async () => {
    try {
      const res = await api.getSettings();
      setSettings(res);
      setDefaultProvider(res.default_ai_provider || 'gemini');
      setCostPreset(res.ai_cost_preset || 'balanced');
      setLocalAiUrl(res.local_ai_url || 'http://localhost:11434/v1');
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
        default_provider: defaultProvider,
        ai_cost_preset: costPreset,
        gemini_key: geminiKey || undefined,
        openai_key: openaiKey || undefined,
        anthropic_key: anthropicKey || undefined,
        local_ai_url: localAiUrl || undefined,
      });
      setSaveMsg('AI Settings saved successfully.');
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">Active AI Provider</label>
              <select
                value={defaultProvider}
                onChange={(e) => setDefaultProvider(e.target.value)}
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="gemini">Google Gemini (Default)</option>
                <option value="openai">OpenAI (GPT-4o)</option>
                <option value="anthropic">Anthropic (Claude 3.5)</option>
                <option value="local">Local AI (Ollama / LocalAI)</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">Cost & Quality Preset</label>
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
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="text-[11px] text-slate-400 block mb-1">
                Gemini API Key {settings?.gemini_configured && '✓ (Active)'}
              </label>
              <input
                type="password"
                placeholder={settings?.gemini_configured ? '••••••••••••••••' : 'Enter Gemini API key'}
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[11px] text-slate-400 block mb-1">
                OpenAI API Key {settings?.openai_configured && '✓ (Active)'}
              </label>
              <input
                type="password"
                placeholder={settings?.openai_configured ? '••••••••••••••••' : 'Enter OpenAI API key'}
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Anthropic API Key {settings?.anthropic_configured && '✓ (Active)'}</label>
              <input
                type="password"
                placeholder={settings?.anthropic_configured ? '••••••••••••••••' : 'Enter Anthropic API key'}
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Local AI Base URL (Ollama / vLLM)</label>
              <input
                type="text"
                placeholder="http://localhost:11434/v1"
                value={localAiUrl}
                onChange={(e) => setLocalAiUrl(e.target.value)}
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors shadow-md shadow-indigo-600/20"
            >
              {saving ? 'Saving...' : 'Save AI Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
