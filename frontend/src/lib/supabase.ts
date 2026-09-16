import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://hnlcybldzcavmnwolwrk.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_7IHHcA2wozrzu6M8TGMyDQ_aE0fdtf4';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
