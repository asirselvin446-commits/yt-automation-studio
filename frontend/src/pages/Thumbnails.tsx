import React, { useState, useEffect } from 'react';
import { Image as ImageIcon, Sparkles, Film, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { VideoListItem } from '../types';

export const Thumbnails: React.FC = () => {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.listVideos();
        setVideos(res);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Thumbnail Workspace</h1>
        <p className="text-xs text-slate-400 mt-1">
          Review AI-generated composition concepts, focal layouts, and text overlays for each video.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {videos.map((v) => (
          <div
            key={v.id}
            className="p-5 rounded-2xl bg-[#11141e] border border-[#1f2434] space-y-3 flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-full h-40 rounded-xl bg-[#151928] border border-[#21263c] flex flex-col items-center justify-center text-slate-500 space-y-2">
                <ImageIcon className="w-8 h-8 text-indigo-400 opacity-60" />
                <span className="text-[11px] text-slate-400 font-medium">Concept Frame</span>
              </div>
              <h3 className="text-xs font-bold text-white line-clamp-2">{v.title}</h3>
              <p className="text-[11px] text-slate-400 font-mono">{v.original_filename}</p>
            </div>

            <Link
              to={`/videos/${v.id}`}
              className="pt-3 border-t border-[#1d2233] flex items-center justify-between text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
            >
              <span>Manage Thumbnails</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};
