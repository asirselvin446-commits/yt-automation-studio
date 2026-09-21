import React, { useEffect, useRef, useState } from 'react';
import {
  Users,
  Plus,
  Trash2,
  Loader2,
  FolderPlus,
  Tv,
  CheckCircle2,
  AlertTriangle,
  Star,
  Link2,
} from 'lucide-react';
import { api } from '../services/api';

export const Accounts: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [folders, setFolders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [newAccountId, setNewAccountId] = useState<string>('');
  const [msg, setMsg] = useState<string | null>(null);
  const poll = useRef<any>(null);

  const load = async () => {
    try {
      const res = await api.listAccounts();
      setAccounts(res.accounts || []);
      setFolders(res.folders || []);
      if (!newAccountId && res.accounts?.length) setNewAccountId(res.accounts[0].id);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    return () => poll.current && clearInterval(poll.current);
  }, []);

  const addAccount = async () => {
    setMsg(null);
    try {
      const res = await api.connectAccount();
      if (!res.auth_url) return;
      (window as any).electronAPI?.openExternal(res.auth_url);
      setConnecting(true);
      setMsg('A Google sign-in opened in your browser — pick the account and allow access.');
      poll.current && clearInterval(poll.current);
      poll.current = setInterval(async () => {
        try {
          const s = await api.accountConnectStatus();
          if (s.state === 'connected') {
            clearInterval(poll.current);
            setConnecting(false);
            setMsg(`Connected ${s.account?.title || 'account'}.`);
            load();
          } else if (s.state === 'error') {
            clearInterval(poll.current);
            setConnecting(false);
            setMsg(s.message || 'Connection failed.');
          }
        } catch { /* keep polling */ }
      }, 2000);
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const removeAccount = async (id: string) => {
    setBusy(id);
    try {
      await api.removeAccount(id);
      await load();
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(null);
    }
  };

  const addFolder = async () => {
    setMsg(null);
    if (!newAccountId) {
      setMsg('Add a YouTube account first.');
      return;
    }
    const path = await (window as any).electronAPI?.selectFolder();
    if (!path) return;
    const acct = accounts.find((a) => a.id === newAccountId);
    setBusy('folder');
    try {
      const res = await api.setFolderMapping(path, newAccountId, acct?.title);
      setFolders(res.folders || []);
      setMsg('Folder linked. Drop videos in it and they upload to that account.');
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(null);
    }
  };

  const removeFolder = async (path: string) => {
    setBusy(path);
    try {
      const res = await api.removeFolderMapping(path);
      setFolders(res.folders || []);
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading accounts…
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
          <Users className="w-6 h-6 text-indigo-400" /> YouTube Accounts
        </h1>
        <p className="text-xs text-slate-400 mt-1 max-w-2xl">
          Connect multiple channels and route uploads by folder — drop a video in a folder and it
          goes to that folder's account, laptop on or off.
        </p>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" /> {msg}
        </div>
      )}

      {/* Accounts list */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white">Connected accounts</h2>
          <button
            onClick={addAccount}
            disabled={connecting}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-2 disabled:opacity-60"
          >
            {connecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {connecting ? 'Waiting for sign-in…' : 'Add account'}
          </button>
        </div>

        {accounts.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No accounts yet. Click <b>Add account</b> and sign in with a Google/YouTube account to authorize uploads.
          </div>
        ) : (
          <div className="space-y-2">
            {accounts.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-3 rounded-xl bg-[#0d0f17] border border-[#1f2434]">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-red-600/15 border border-red-500/30 flex items-center justify-center text-red-500 shrink-0">
                    <Tv className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-white truncate flex items-center gap-2">
                      {a.title}
                      {a.is_primary && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                          <Star className="w-3 h-3" /> Primary
                        </span>
                      )}
                    </div>
                    {a.channel_id && <p className="text-[11px] text-slate-500 font-mono truncate">{a.channel_id}</p>}
                  </div>
                </div>
                <button
                  onClick={() => removeAccount(a.id)}
                  disabled={busy === a.id}
                  className="p-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300 hover:bg-rose-900/40 disabled:opacity-60"
                  title="Remove account"
                >
                  {busy === a.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Folder → account mapping */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <div>
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Link2 className="w-4 h-4 text-indigo-400" /> Upload folders
          </h2>
          <p className="text-[11px] text-slate-500 mt-1">
            Link a folder to an account. Any video dropped there uploads to that account automatically.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={newAccountId}
            onChange={(e) => setNewAccountId(e.target.value)}
            disabled={accounts.length === 0}
            className="flex-1 px-3 py-2.5 rounded-lg bg-[#0d0f17] border border-[#252c42] text-sm text-white focus:border-indigo-500 outline-none disabled:opacity-50"
          >
            {accounts.length === 0 ? (
              <option>Add an account first</option>
            ) : (
              accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.title}</option>
              ))
            )}
          </select>
          <button
            onClick={addFolder}
            disabled={busy === 'folder' || accounts.length === 0}
            className="px-4 py-2.5 rounded-lg bg-[#1a1f2e] border border-[#2b334a] text-slate-200 hover:text-white hover:border-indigo-500/40 text-xs font-bold flex items-center gap-2 disabled:opacity-50"
          >
            {busy === 'folder' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FolderPlus className="w-4 h-4" />}
            Link a folder
          </button>
        </div>

        {folders.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500">No folders linked yet.</div>
        ) : (
          <div className="space-y-2">
            {folders.map((f) => (
              <div key={f.path} className="flex items-center justify-between p-3 rounded-xl bg-[#0d0f17] border border-[#1f2434]">
                <div className="min-w-0">
                  <p className="text-xs text-white font-mono truncate">{f.path}</p>
                  <p className="text-[11px] text-indigo-400 mt-0.5 flex items-center gap-1">
                    <Tv className="w-3 h-3" /> {f.account_title || f.account_id}
                  </p>
                </div>
                <button
                  onClick={() => removeFolder(f.path)}
                  disabled={busy === f.path}
                  className="p-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300 hover:bg-rose-900/40 disabled:opacity-60"
                  title="Unlink folder"
                >
                  {busy === f.path ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/20 text-amber-300/80 text-[11px] flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          Each account needs a one-time Google sign-in (the "Add account" button). Uploads then run in
          the cloud even with your laptop off.
        </div>
      </div>
    </div>
  );
};
