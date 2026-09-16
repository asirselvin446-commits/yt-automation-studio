-- ==============================================================================
-- YT AUTOMATION STUDIO — INITIAL SEED DATA
-- ==============================================================================

-- 1. Default Workspace Profile
INSERT INTO public.profiles (id, email, full_name, role)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'creator@ytautomation.local',
    'Studio Creator',
    'creator'
) ON CONFLICT (email) DO NOTHING;

-- 2. Default Automation Settings
INSERT INTO public.automation_settings (
    profile_id,
    folder_monitoring,
    ai_analysis,
    metadata_generation,
    thumbnail_generation,
    approval_required,
    auto_upload,
    auto_scheduling,
    analytics_sync,
    ai_insights,
    watch_folder_root,
    default_ai_provider,
    ai_cost_preset
) VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE, -- Human approval required by default
    FALSE,
    FALSE,
    TRUE,
    TRUE,
    'D:\YT-Automation',
    'gemini',
    'balanced'
) ON CONFLICT (profile_id) DO NOTHING;

-- 3. Initial Welcome Notification
INSERT INTO public.notifications (
    profile_id,
    title,
    message,
    notification_type,
    severity,
    deep_link,
    is_read
) VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Welcome to YT Automation Studio',
    'Your local-first YouTube automation system is ready. Set your inbox folder in Settings or drop videos into your configured INBOX directory.',
    'PROCESSING_COMPLETE',
    'SUCCESS',
    '/settings',
    FALSE
);
