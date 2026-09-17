import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, HardDrive, Sparkles, CheckCircle2, Shield, Radio, FolderOpen, UploadCloud } from 'lucide-react';
import { YoutubeIcon } from '../components/common/YoutubeIcon';
import { api } from '../services/api';

declare global {
  interface Window {
    pywebview?: { api?: { select_folder?: () => Promise<string | null> } };
  }
}

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Form states
  const [defaultProvider, setDefaultProvider] = useState('gemini');
  const [costPreset, setCostPreset] = useState('balanced');
  const [geminiKey, setGeminiKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [localAiUrl, setLocalAiUrl] = useState('http://localhost:11434/v1');
  const [uploadFolder, setUploadFolder] = useState<string | null>(null);
  const [folderMsg, setFolderMsg] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await api.getSettings();
      setSettings(res);
      setDefaultProvider(res.default_ai_provider || 'gemini');
      setCostPreset(res.ai_cost_preset || 'balanced');
      setLocalAiUrl(res.local_ai_url || 'http://localhost:11434/v1');
      setUploadFolder(res.custom_upload_folder || null);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
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

  const saveFolder = async (path: string) => {
    try {
      setFolderMsg(null);
      const res = await api.setUploadFolder(path);
      setUploadFolder(res.custom_upload_folder);
      setFolderMsg('Upload folder set. New videos here will auto-upload to YouTube.');
      load();
    } catch (e: any) {
      alert(`Could not set folder: ${e.message}`);
    }
  };

  const handleSelectFolder = async () => {
    const picker = window.pywebview?.api?.select_folder;
    if (picker) {
      const path = await picker();
      if (path) await saveFolder(path);
    } else {
      // Fallback for running in a normal browser (no native dialog).
      const path = prompt('Enter the full path of the folder to auto-upload from:');
      if (path) await saveFolder(path);
    }
  };

  const handleConnectYouTube = async () => {
    try {
      const res = await api.getConnectUrl();
      if (res.url) {
        window.open(res.url, '_blank');
      } else {
        alert(res.error || 'Google Client ID not configured.');
      }
    } catch (e: any) {
      alert(`OAuth error: ${e.message}`);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Studio Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Manage AI providers, local folder automation paths, and YouTube Google OAuth credentials.
        </p>
      </div>

      {saveMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{saveMsg}</span>
        </div>
      )}

      {/* 1. YouTube Integration Card */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <div className="flex items-center justify-between border-b border-[#1f2434] pb-3">
          <div className="flex items-center space-x-2.5">
            <YoutubeIcon className="w-5 h-5 text-rose-500" />
            <h2 className="text-sm font-bold text-white">YouTube Channel Authentication</h2>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              settings?.youtube_client_configured
                ? 'bg-emerald-500/15 text-emerald-400'
                : 'bg-amber-500/15 text-amber-400'
            }`}
          >
            {settings?.youtube_client_configured ? 'OAUTH CONFIGURED' : 'CREDENTIALS NEEDED'}
          </span>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          Google OAuth 2.0 connection is required for live subscriber analytics, channel view tracking, and publishing approved videos to YouTube.
        </p>

        <div className="pt-2 flex items-center justify-between">
          <div className="text-[11px] text-slate-500 font-mono">
            Redirect URI: http://127.0.0.1:8000/api/v1/youtube/oauth2callback
          </div>
          <button
            onClick={handleConnectYouTube}
            className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors shadow-md shadow-rose-600/20"
          >
            Authenticate with Google
          </button>
        </div>
      </div>

      {/* 2. AI Provider Settings */}
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
              <label className="text-xs text-slate-300 font-medium block mb-1">
                Active AI Provider
              </label>
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
              <label className="text-xs text-slate-300 font-medium block mb-1">
                Cost & Quality Preset
              </label>
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
              <label className="text-[11px] text-slate-400 block mb-1">
                Local AI Base URL (Ollama / vLLM)
              </label>
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

      {/* 3. Auto-Upload Folder (Cloud) */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <div className="flex items-center justify-between border-b border-[#1f2434] pb-3">
          <div className="flex items-center space-x-2.5">
            <UploadCloud className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-white">Auto-Upload Folder</h2>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              uploadFolder ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'
            }`}
          >
            {uploadFolder ? 'ACTIVE' : 'NOT SET'}
          </span>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          Pick a folder on this PC. Any video you drop in is sent to the cloud and
          uploaded to YouTube automatically — even after you shut down your laptop.
          Files are removed locally and from the cloud once uploaded.
        </p>

        {folderMsg && (
          <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-[11px]">
            {folderMsg}
          </div>
        )}

        <div className="flex items-center justify-between gap-3">
          <div className="flex-1 text-[11px] font-mono px-3 py-2.5 rounded bg-[#161a27] text-white truncate">
            {uploadFolder || 'No folder selected'}
          </div>
          <button
            onClick={handleSelectFolder}
            className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors shadow-md shadow-emerald-600/20 flex items-center space-x-2 shrink-0"
          >
            <FolderOpen className="w-4 h-4" />
            <span>{uploadFolder ? 'Change Folder' : 'Select Folder'}</span>
          </button>
        </div>

        {settings?.upload_status && (
          <div className="grid grid-cols-3 gap-2 text-center pt-1">
            <div className="p-2 rounded bg-[#161a27]">
              <div className="text-sm font-bold text-amber-400">{settings.upload_status.queued ?? 0}</div>
              <div className="text-[10px] text-slate-500">Queued</div>
            </div>
            <div className="p-2 rounded bg-[#161a27]">
              <div className="text-sm font-bold text-emerald-400">{settings.upload_status.uploaded ?? 0}</div>
              <div className="text-[10px] text-slate-500">Uploaded</div>
            </div>
            <div className="p-2 rounded bg-[#161a27]">
              <div className="text-sm font-bold text-rose-400">{settings.upload_status.failed ?? 0}</div>
              <div className="text-[10px] text-slate-500">Failed</div>
            </div>
          </div>
        )}
        {settings && !settings.supabase_configured && (
          <div className="text-[11px] text-amber-400">Supabase is not configured — set SUPABASE_URL and the service-role key.</div>
        )}
      </div>

      {/* 4. Folder Automation Directories */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
        <div className="flex items-center space-x-2.5 border-b border-[#1f2434] pb-3">
          <HardDrive className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-bold text-white">Local Windows Storage Pipeline</h2>
        </div>
        <div className="space-y-2 text-xs text-slate-400 font-mono">
          <div className="flex justify-between p-2.5 rounded bg-[#161a27]">
            <span className="text-slate-500">Root Directory:</span>
            <span className="text-white">{settings?.watch_folder_root || 'Loading...'}</span>
          </div>
          <div className="flex justify-between p-2.5 rounded bg-[#161a27]">
            <span className="text-slate-500">Watched INBOX:</span>
            <span className="text-indigo-400 font-bold">{settings?.inbox_path || 'Loading...'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
