import React, { useState, useEffect } from 'react';
import { DollarSign, ShieldAlert, CheckCircle2, Lock, Users, Clock, Flame } from 'lucide-react';
import { api } from '../services/api';

export const Monetization: React.FC = () => {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getMonetization();
        setData(res);
      } catch (e) {
        console.error(e);
      }
    };
    load();
  }, []);

  const thresholds = data?.thresholds;

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Monetization Tracker</h1>
        <p className="text-xs text-slate-400 mt-1">
          Official YouTube Partner Program (YPP) milestone evaluation and application readiness.
        </p>
      </div>

      {/* Official YouTube Policy Disclaimer */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start space-x-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold text-amber-200">Official Policy Requirement</h4>
          <p className="leading-relaxed">
            Meeting eligibility criteria allows you to apply for the YouTube Partner Program. Monetization is never guaranteed and requires manual and automated review by YouTube for compliance with Community Guidelines and copyright laws.
          </p>
        </div>
      </div>

      {/* Threshold Progress Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Subscribers */}
        <div className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
              <Users className="w-4 h-4 text-indigo-400" /> Subscribers
            </span>
            <span className="text-xs font-bold text-indigo-400">
              {thresholds?.subscribers?.progress_percent || 0}%
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-black text-white">
              {thresholds?.subscribers?.current || 0}
            </span>
            <span className="text-xs text-slate-500">/ 1,000 required</span>
          </div>
          <div className="w-full h-2 rounded-full bg-[#181d2c] overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-500"
              style={{ width: `${thresholds?.subscribers?.progress_percent || 0}%` }}
            />
          </div>
        </div>

        {/* Watch Hours */}
        <div className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-emerald-400" /> Watch Hours
            </span>
            <span className="text-xs font-bold text-emerald-400">
              {thresholds?.watch_hours?.progress_percent || 0}%
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-black text-white">
              {thresholds?.watch_hours?.current || 0}
            </span>
            <span className="text-xs text-slate-500">/ 4,000 required</span>
          </div>
          <div className="w-full h-2 rounded-full bg-[#181d2c] overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${thresholds?.watch_hours?.progress_percent || 0}%` }}
            />
          </div>
        </div>

        {/* Shorts Views */}
        <div className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
              <Flame className="w-4 h-4 text-rose-400" /> Shorts Views
            </span>
            <span className="text-xs font-bold text-rose-400">
              {thresholds?.shorts_views?.progress_percent || 0}%
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-black text-white">
              {thresholds?.shorts_views?.current || 0}
            </span>
            <span className="text-xs text-slate-500">/ 10M required</span>
          </div>
          <div className="w-full h-2 rounded-full bg-[#181d2c] overflow-hidden">
            <div
              className="h-full bg-rose-500 rounded-full transition-all duration-500"
              style={{ width: `${thresholds?.shorts_views?.progress_percent || 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* YPP 4-Step Process Pipeline */}
      <div className="p-6 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Partner Program Milestones
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          {data?.stages?.map((st: any) => (
            <div key={st.step} className="p-4 rounded-xl bg-[#151926] border border-[#212638] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-500">STEP {st.step}</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-semibold">
                  {st.status}
                </span>
              </div>
              <h4 className="font-bold text-white">{st.name}</h4>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
