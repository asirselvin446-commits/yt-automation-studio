import React, { useState, useEffect } from 'react';
import { BarChart3, Calendar, TrendingUp, Users, Eye, Clock, DollarSign } from 'lucide-react';
import { YoutubeIcon } from '../components/common/YoutubeIcon';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

export const Analytics: React.FC = () => {
  const [timeframe, setTimeframe] = useState('28d');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.getAnalytics(timeframe);
        setData(res);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [timeframe]);

  const periods = [
    { key: 'today', label: 'Today' },
    { key: '7d', label: '7 Days' },
    { key: '28d', label: '28 Days' },
    { key: '90d', label: '90 Days' },
    { key: 'lifetime', label: 'Lifetime' },
  ];

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Channel Analytics</h1>
          <p className="text-xs text-slate-400 mt-1">
            Official metrics retrieved from Google YouTube Data & Analytics APIs.
          </p>
        </div>

        {/* Timeframe Buttons */}
        <div className="flex items-center space-x-1.5 p-1 rounded-xl bg-[#11141e] border border-[#1f2434]">
          {periods.map((p) => (
            <button
              key={p.key}
              onClick={() => setTimeframe(p.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                timeframe === p.key
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-[#161a28]'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Disconnected Notice (Zero Fake Data Guarantee) */}
      {!data?.is_connected ? (
        <div className="p-12 text-center rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
          <div className="w-14 h-14 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center justify-center mx-auto">
            <YoutubeIcon className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Connect YouTube to View Live Channel Analytics</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Per studio policy, fake numbers and simulated engagement statistics are never displayed. Authenticate with Google OAuth in Settings to see official metrics.
            </p>
          </div>
          <Link
            to="/settings"
            className="inline-block px-5 py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-md shadow-rose-600/20"
          >
            Connect YouTube Channel
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl bg-[#11141e] border border-[#1f2434]">
              <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                <Users className="w-4 h-4 text-indigo-400" /> Subscribers
              </span>
              <p className="text-2xl font-black text-white mt-2">
                {data.metrics?.subscribers?.toLocaleString() || 0}
              </p>
            </div>
            <div className="p-5 rounded-xl bg-[#11141e] border border-[#1f2434]">
              <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                <Eye className="w-4 h-4 text-emerald-400" /> Views
              </span>
              <p className="text-2xl font-black text-white mt-2">
                {data.metrics?.total_views?.toLocaleString() || 0}
              </p>
            </div>
            <div className="p-5 rounded-xl bg-[#11141e] border border-[#1f2434]">
              <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-amber-400" /> Avg. Retention
              </span>
              <p className="text-2xl font-black text-white mt-2">
                {data.metrics?.average_retention || '0%'}
              </p>
            </div>
            <div className="p-5 rounded-xl bg-[#11141e] border border-[#1f2434]">
              <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-rose-400" /> Est. Revenue
              </span>
              <p className="text-2xl font-black text-white mt-2">
                ${data.metrics?.estimated_revenue || '0.00'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
