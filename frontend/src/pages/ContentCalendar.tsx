import React, { useState, useEffect } from 'react';
import { Calendar as CalendarIcon, Plus, Clock, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { CalendarItem } from '../types';

export const ContentCalendar: React.FC = () => {
  const [items, setItems] = useState<CalendarItem[]>([]);
  const [title, setTitle] = useState('');
  const [datetime, setDatetime] = useState('');
  const [showModal, setShowModal] = useState(false);

  const load = async () => {
    try {
      const res = await api.listCalendar();
      setItems(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !datetime) return;
    try {
      await api.createCalendarEntry(title, datetime);
      setShowModal(false);
      setTitle('');
      setDatetime('');
      load();
    } catch (e: any) {
      alert(`Error creating schedule: ${e.message}`);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Content Calendar</h1>
          <p className="text-xs text-slate-400 mt-1">
            Schedule releases and synchronize your planned YouTube publishing timeline.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors flex items-center space-x-1.5"
        >
          <Plus className="w-4 h-4" />
          <span>Schedule Video</span>
        </button>
      </div>

      {showModal && (
        <div className="p-6 rounded-2xl bg-[#11141e] border border-indigo-500/40 space-y-4">
          <h3 className="text-sm font-bold text-white">Add Schedule Entry</h3>
          <form onSubmit={handleCreate} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Video / Content Title</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Masterclass on YouTube Automation"
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Date & Time</label>
              <input
                type="datetime-local"
                required
                value={datetime}
                onChange={(e) => setDatetime(e.target.value)}
                className="w-full bg-[#161a27] border border-[#23293d] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}

      {items.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#11141e] border border-[#1f2434] text-slate-500 text-xs">
          No scheduled releases yet. Click "Schedule Video" to plan your publishing calendar.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((it) => (
            <div
              key={it.id}
              className="p-4 rounded-xl bg-[#11141e] border border-[#1f2434] flex items-center justify-between"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <CalendarIcon className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white">{it.title}</h4>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {new Date(it.scheduled_datetime).toLocaleString()}
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-blue-500/15 text-blue-400 border border-blue-500/30">
                {it.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
