import React, { useState } from 'react';
import { BrainCircuit, Sparkles, Send, CheckCircle2, HelpCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export const ChannelBrain: React.FC = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    data_basis: any;
    interpretation: string;
    actionable_suggestions: string[];
    confidence_rating: string;
  } | null>(null);

  const presetQuestions = [
    'What content patterns have performed well recently?',
    'Which video structures retained the highest audience attention?',
    'What topic gaps should I investigate for upcoming videos?',
    'Give me data-grounded ideas based on my existing content catalog.',
  ];

  const handleSearch = async (questionText: string) => {
    if (!questionText) return;
    try {
      setLoading(true);
      const res = await api.queryBrain(questionText);
      setResult(res);
    } catch (e: any) {
      alert(`Error querying Channel Brain: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Channel Brain</h1>
        <p className="text-xs text-slate-400 mt-1">
          AI analytical intelligence grounded in your historical channel data. Explicitly separates verified Data from Interpretation and Actionable Suggestions.
        </p>
      </div>

      {/* Query Bar */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4 shadow-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query);
          }}
          className="flex items-center space-x-3"
        >
          <div className="relative flex-1">
            <BrainCircuit className="w-5 h-5 text-indigo-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask Channel Brain about your performance, viewer retention, or topics..."
              className="w-full bg-[#161a27] border border-[#23293d] rounded-xl pl-11 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors flex items-center space-x-2 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>Analyze</span>
          </button>
        </form>

        {/* Preset Questions */}
        <div className="flex flex-wrap gap-2 pt-2">
          {presetQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(q);
                handleSearch(q);
              }}
              className="px-3 py-1.5 rounded-lg bg-[#151926] border border-[#212638] text-[11px] text-slate-300 hover:text-indigo-300 hover:border-indigo-500/40 transition-colors"
            >
              "{q}"
            </button>
          ))}
        </div>
      </div>

      {/* Structured AI Analysis Output (Data vs Interpretation vs Suggestions) */}
      {result && (
        <div className="space-y-4 animate-fade-in">
          {/* 1. DATA (Grounding facts) */}
          <div className="p-5 rounded-xl bg-[#11141e] border border-blue-500/30 space-y-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-blue-400 block">
              1. VERIFIED DATA BASIS
            </span>
            <div className="p-3 rounded-lg bg-[#141825] border border-blue-500/20 font-mono text-xs text-slate-300">
              {JSON.stringify(result.data_basis, null, 2)}
            </div>
          </div>

          {/* 2. INTERPRETATION */}
          <div className="p-5 rounded-xl bg-[#11141e] border border-indigo-500/30 space-y-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 block">
              2. ANALYTICAL INTERPRETATION
            </span>
            <p className="text-xs text-slate-200 leading-relaxed p-3 rounded-lg bg-[#151927]">
              {result.interpretation}
            </p>
          </div>

          {/* 3. SUGGESTIONS */}
          <div className="p-5 rounded-xl bg-[#11141e] border border-emerald-500/30 space-y-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400 block">
              3. ACTIONABLE SUGGESTIONS
            </span>
            <div className="space-y-2 pt-1">
              {result.actionable_suggestions.map((s, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-[#151927] border border-emerald-500/20 text-xs text-emerald-300 flex items-start space-x-2"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
