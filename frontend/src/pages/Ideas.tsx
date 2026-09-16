import React, { useState, useEffect } from 'react';
import { Lightbulb, Sparkles, Plus, Trash2, ArrowRight, CheckCircle2, Archive, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { ContentIdea } from '../types';

export const Ideas: React.FC = () => {
  const [ideas, setIdeas] = useState<ContentIdea[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Form inputs
  const [topic, setTopic] = useState('');
  const [niche, setNiche] = useState('');
  const [audience, setAudience] = useState('');

  const loadIdeas = async () => {
    try {
      setLoading(true);
      const res = await api.listIdeas();
      setIdeas(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIdeas();
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic) return;
    try {
      setGenerating(true);
      await api.generateIdeas(topic, niche, audience);
      setTopic('');
      loadIdeas();
    } catch (e: any) {
      alert(`Generation error: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleStatus = async (id: string, status: string) => {
    try {
      await api.updateIdeaStatus(id, status);
      loadIdeas();
    } catch (e: any) {
      alert(`Error updating status: ${e.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteIdea(id);
      loadIdeas();
    } catch (e: any) {
      alert(`Error deleting idea: ${e.message}`);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">AI Idea Lab</h1>
        <p className="text-xs text-slate-400 mt-1">
          Generate 10 structured YouTube concepts with psychological hooks, structural outlines, and production difficulty ratings.
        </p>
      </div>

      {/* Generator Form */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          Content Strategy Brief
        </h3>
        <form onSubmit={handleGenerate} className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Core Topic / Theme *</label>
            <input
              type="text"
              required
              placeholder="e.g. Next.js 15 vs Remix"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Niche / Category</label>
            <input
              type="text"
              placeholder="e.g. Web Development"
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Target Audience</label>
            <input
              type="text"
              placeholder="e.g. Intermediate Developers"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="md:col-span-3 flex justify-end pt-2">
            <button
              type="submit"
              disabled={generating || !topic}
              className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors flex items-center space-x-2 shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              <span>{generating ? 'Synthesizing 10 Ideas...' : 'Generate 10 Ideas'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Ideas Grid */}
      <div className="space-y-4">
        {ideas.map((item) => (
          <div
            key={item.id}
            className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4 shadow-lg"
          >
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {item.topic}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      item.production_difficulty === 'Low'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : item.production_difficulty === 'High'
                        ? 'bg-rose-500/10 text-rose-400'
                        : 'bg-amber-500/10 text-amber-400'
                    }`}
                  >
                    Difficulty: {item.production_difficulty}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    Status: {item.status}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-white leading-snug">{item.title_concept}</h3>
              </div>

              {/* Status and Action Buttons */}
              <div className="flex items-center space-x-1.5 shrink-0">
                {item.status === 'IDEA' && (
                  <>
                    <button
                      onClick={() => handleStatus(item.id, 'SCRIPT')}
                      className="px-2.5 py-1 rounded bg-[#161a28] border border-[#242b3e] text-[11px] font-semibold text-slate-300 hover:text-white"
                    >
                      → Script
                    </button>
                    <button
                      onClick={() => handleStatus(item.id, 'IN_PRODUCTION')}
                      className="px-2.5 py-1 rounded bg-[#161a28] border border-[#242b3e] text-[11px] font-semibold text-slate-300 hover:text-white"
                    >
                      → Production
                    </button>
                  </>
                )}
                <button
                  onClick={() => handleDelete(item.id)}
                  className="p-1.5 rounded text-slate-500 hover:text-rose-400"
                  title="Delete"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Hook and Structure Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
              {item.hook && (
                <div className="p-3 rounded-xl bg-[#151926] border border-[#212638]">
                  <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
                    First 15s Hook
                  </span>
                  <p className="text-slate-300 italic">"{item.hook}"</p>
                </div>
              )}
              {item.video_structure && (
                <div className="p-3 rounded-xl bg-[#151926] border border-[#212638]">
                  <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
                    Video Outline
                  </span>
                  <p className="text-slate-300 whitespace-pre-line">{item.video_structure}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
