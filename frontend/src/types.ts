export interface Project {
  id: number;
  title: string;
  platform?: string | null;
  duration_sec?: number | null;
  max_chapters: number;
  created_at: string;
  updated_at: string;
}

export interface TranscriptLine {
  id: number;
  project_id: number;
  start_sec: number;
  end_sec?: number | null;
  text: string;
  source: string;
}

export interface Chapter {
  id: number;
  project_id: number;
  title: string;
  start_sec: number;
  end_sec?: number | null;
  summary?: string | null;
  tags?: string | null;
  source: string;
  confidence?: number | null;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateResponse {
  project: Project;
  transcript_line_count: number;
}

export interface ChapterListResponse {
  chapters: Chapter[];
}
