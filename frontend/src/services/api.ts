import {
  SystemHealth,
  FolderStats,
  StudioNotification,
  VideoListItem,
  VideoDetail,
  ChannelInfo,
  ContentIdea,
  CalendarItem,
  AutomationSettings,
} from '../types';

const BASE_URL = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API Error (${res.status}): ${errText}`);
  }
  return res.json();
}

export const api = {
  // System
  getHealth: () => fetchJson<SystemHealth>(`${BASE_URL}/system/health`),
  getFolderStats: () => fetchJson<FolderStats>(`${BASE_URL}/system/folder-stats`),
  getNotifications: () => fetchJson<StudioNotification[]>(`${BASE_URL}/system/notifications`),
  markNotificationRead: (id: string) => fetchJson<{ success: boolean }>(`${BASE_URL}/system/notifications/${id}/read`, { method: 'POST' }),

  // Videos
  listVideos: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return fetchJson<VideoListItem[]>(`${BASE_URL}/videos${query}`);
  },
  getVideo: (id: string) => fetchJson<VideoDetail>(`${BASE_URL}/videos/${id}`),
  approveVideo: (id: string) => fetchJson<{ success: boolean; status: string }>(`${BASE_URL}/videos/${id}/approve`, { method: 'POST' }),
  triggerUpload: (id: string) => fetchJson<{ success: boolean; message: string }>(`${BASE_URL}/videos/${id}/upload`, { method: 'POST' }),
  rejectVideo: (id: string, reason?: string) =>
    fetchJson<{ success: boolean }>(`${BASE_URL}/videos/${id}/reject?reason=${encodeURIComponent(reason || 'Rejected')}`, { method: 'POST' }),
  selectTitle: (videoId: string, titleId: string) =>
    fetchJson<{ success: boolean }>(`${BASE_URL}/videos/${videoId}/select-title/${titleId}`, { method: 'POST' }),
  triggerAi: (videoId: string) => fetchJson<{ success: boolean }>(`${BASE_URL}/videos/${videoId}/trigger-ai`, { method: 'POST' }),
  manualIngest: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/videos/manual-ingest`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // YouTube Channel
  getChannelStatus: () => fetchJson<ChannelInfo>(`${BASE_URL}/youtube/status`),
  getConnectUrl: () => fetchJson<{ url?: string; error?: string }>(`${BASE_URL}/youtube/connect-url`),
  disconnectChannel: () => fetchJson<{ success: boolean }>(`${BASE_URL}/youtube/disconnect`, { method: 'POST' }),

  // Analytics
  getAnalytics: (timeframe: string = '28d') => fetchJson<any>(`${BASE_URL}/analytics?timeframe=${timeframe}`),

  // Channel Brain
  queryBrain: (question: string) =>
    fetchJson<{ data_basis: any; interpretation: string; actionable_suggestions: string[]; confidence_rating: string }>(
      `${BASE_URL}/brain/query`,
      {
        method: 'POST',
        body: JSON.stringify({ question }),
      }
    ),
  getBrainHistory: () => fetchJson<any[]>(`${BASE_URL}/brain/history`),

  // Content Ideas
  listIdeas: () => fetchJson<ContentIdea[]>(`${BASE_URL}/ideas`),
  generateIdeas: (topic: string, niche?: string, audience?: string, length?: number) =>
    fetchJson<{ success: boolean; count: number }>(`${BASE_URL}/ideas/generate`, {
      method: 'POST',
      body: JSON.stringify({
        topic,
        niche,
        target_audience: audience,
        estimated_length_minutes: length || 10,
      }),
    }),
  updateIdeaStatus: (id: string, status: string) =>
    fetchJson<{ success: boolean }>(`${BASE_URL}/ideas/${id}/status?status=${status}`, { method: 'PATCH' }),
  deleteIdea: (id: string) => fetchJson<{ success: boolean }>(`${BASE_URL}/ideas/${id}`, { method: 'DELETE' }),

  // Calendar
  listCalendar: () => fetchJson<CalendarItem[]>(`${BASE_URL}/calendar`),
  createCalendarEntry: (title: string, scheduled_datetime: string, notes?: string) =>
    fetchJson<{ success: boolean; id: string }>(
      `${BASE_URL}/calendar?title=${encodeURIComponent(title)}&scheduled_datetime=${encodeURIComponent(scheduled_datetime)}&notes=${encodeURIComponent(notes || '')}`,
      { method: 'POST' }
    ),

  // Monetization
  getMonetization: () => fetchJson<any>(`${BASE_URL}/monetization`),

  // Automation
  getAutomationSettings: () => fetchJson<AutomationSettings>(`${BASE_URL}/automation`),
  updateAutomationSettings: (payload: AutomationSettings) =>
    fetchJson<AutomationSettings>(`${BASE_URL}/automation`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Settings
  getSettings: () => fetchJson<any>(`${BASE_URL}/settings`),
  updateAiSettings: (payload: any) =>
    fetchJson<{ success: boolean }>(`${BASE_URL}/settings/ai`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  setUploadFolder: (path: string) =>
    fetchJson<{ success: boolean; custom_upload_folder: string; upload_status: any }>(
      `${BASE_URL}/settings/upload-folder`,
      { method: 'POST', body: JSON.stringify({ path }) },
    ),
  setPublishMode: (mode: 'auto' | 'review') =>
    fetchJson<{ success: boolean; publish_mode: string }>(
      `${BASE_URL}/settings/publish-mode`,
      { method: 'POST', body: JSON.stringify({ mode }) },
    ),
  setPublishing: (payload: { visibility?: string; schedule_per_day?: number }) =>
    fetchJson<{ success: boolean; visibility: string; schedule_per_day: number }>(
      `${BASE_URL}/settings/publishing`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),
  publishHeld: () =>
    fetchJson<{ success: boolean; released: number; upload_status: any }>(
      `${BASE_URL}/settings/publish-held`,
      { method: 'POST' },
    ),

  // Live cloud pipeline
  listUploads: () =>
    fetchJson<{ items: any[]; summary: Record<string, number>; configured: boolean }>(
      `${BASE_URL}/uploads`,
    ),
  publishUpload: (id: string) =>
    fetchJson<{ success: boolean }>(`${BASE_URL}/uploads/${id}/publish`, { method: 'POST' }),
  retryUpload: (id: string) =>
    fetchJson<{ success: boolean }>(`${BASE_URL}/uploads/${id}/retry`, { method: 'POST' }),

  // Auto-Source engine (cloud content generation)
  getAutosource: () => fetchJson<any>(`${BASE_URL}/autosource`),
  setAutosourceConfig: (payload: {
    enabled?: boolean;
    niche?: string;
    per_day?: number;
    format?: 'shorts' | 'landscape';
    provider?: 'edge' | 'fish';
    voice?: string;
    fish_api_key?: string;
    fish_voice?: string;
    pexels_api_key?: string;
  }) =>
    fetchJson<{ success: boolean; config: any }>(`${BASE_URL}/autosource/config`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  generateAutosource: () =>
    fetchJson<{ started: boolean; reason: string }>(`${BASE_URL}/autosource/generate`, {
      method: 'POST',
    }),
};
