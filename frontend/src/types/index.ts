export type VideoStatus =
  | 'INBOX'
  | 'PROCESSING'
  | 'READY_FOR_APPROVAL'
  | 'APPROVED'
  | 'UPLOADING'
  | 'UPLOADED'
  | 'FAILED'
  | 'CANCELLED';

export type QualityStatus = 'READY' | 'WARNING' | 'BLOCKED' | 'ERROR' | 'PENDING';

export interface VideoFile {
  sha256_hash: string;
  file_size_bytes: number;
  duration_seconds: number;
  width?: number;
  height?: number;
  fps?: number;
  video_codec?: string;
  audio_codec?: string;
  has_audio: boolean;
  container_format?: string;
}

export interface TitleCandidate {
  id?: string;
  candidate_index: number;
  title_text: string;
  reasoning?: string;
  estimated_intent?: string;
  character_length: number;
  is_selected: boolean;
}

export interface DescriptionRecord {
  short_description?: string;
  long_description: string;
  call_to_action?: string;
  links_placeholder?: string;
  hashtags: string[];
  chapters: Array<{ timestamp: string; title: string }>;
}

export interface TagRecord {
  primary_keywords: string[];
  secondary_keywords: string[];
  long_tail_keywords: string[];
  combined_tags_string?: string;
  tag_count: number;
}

export interface ThumbnailRecord {
  id?: string;
  concept_title?: string;
  text_suggestions?: string;
  visual_composition?: string;
  preview_url?: string;
  local_file_path?: string;
  is_selected: boolean;
  status: string;
}

export interface QualityCheckItem {
  name: string;
  passed: boolean;
  status: 'VALID' | 'WARNING' | 'BLOCKED' | 'ERROR';
  message: string;
}

export interface QualityCheckResult {
  overall_status: QualityStatus;
  can_upload: boolean;
  checks: QualityCheckItem[];
}

export interface VideoDetail {
  id: string;
  title: string;
  status: VideoStatus;
  publishing_mode: string;
  quality_status: QualityStatus;
  original_filename: string;
  source_path: string;
  current_folder_path: string;
  youtube_video_id?: string;
  youtube_url?: string;
  privacy_status: string;
  created_at: string;
  updated_at: string;
  file_info?: VideoFile;
  titles: TitleCandidate[];
  description?: DescriptionRecord;
  tags?: TagRecord;
  thumbnails: ThumbnailRecord[];
  quality_check?: QualityCheckResult;
  transcript_summary?: string;
}

export interface VideoListItem {
  id: string;
  title: string;
  status: VideoStatus;
  publishing_mode: string;
  quality_status: QualityStatus;
  original_filename: string;
  duration_seconds: number;
  file_size_bytes: number;
  created_at: string;
  youtube_video_id?: string;
  selected_thumbnail?: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  database_connected: boolean;
  agent_active: boolean;
  watch_folder: string;
  timestamp: string;
}

export interface FolderStats {
  root: string;
  inbox_count: number;
  processing_count: number;
  approved_count: number;
  uploading_count: number;
  uploaded_count: number;
  failed_count: number;
  archive_count: number;
}

export interface StudioNotification {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
  deep_link?: string;
  is_read: boolean;
  created_at: string;
}

export interface ChannelInfo {
  is_connected: boolean;
  channel_id?: string;
  title?: string;
  custom_url?: string;
  thumbnail_url?: string;
  subscriber_count?: number;
  video_count?: number;
  view_count?: number;
  message?: string;
}

export interface ContentIdea {
  id: string;
  topic: string;
  title_concept: string;
  hook?: string;
  video_structure?: string;
  target_audience?: string;
  production_difficulty: string;
  estimated_length_minutes: number;
  status: string;
  created_at: string;
}

export interface CalendarItem {
  id: string;
  title: string;
  scheduled_datetime: string;
  status: string;
  color_code: string;
  video_id?: string;
  notes?: string;
}

export interface AutomationSettings {
  folder_monitoring: boolean;
  ai_analysis: boolean;
  metadata_generation: boolean;
  thumbnail_generation: boolean;
  approval_required: boolean;
  auto_upload: boolean;
  auto_scheduling: boolean;
  analytics_sync: boolean;
  ai_insights: boolean;
  watch_folder_root: string;
  default_ai_provider: string;
  ai_cost_preset: string;
}
