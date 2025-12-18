import type {
  Chapter,
  ChapterListResponse,
  Project,
  ProjectCreateResponse,
  TranscriptLine,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || 'Request failed');
  }
  return res.json();
}

export async function createProjectFromTranscript(payload: {
  title: string;
  platform?: string | null;
  max_chapters?: number | null;
  transcript_txt: string;
}): Promise<ProjectCreateResponse> {
  const res = await fetch(`${API_BASE}/projects/from-transcript-txt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<ProjectCreateResponse>(res);
}

export async function fetchProject(projectId: number): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`);
  return handleResponse<Project>(res);
}

export async function fetchTranscript(projectId: number): Promise<TranscriptLine[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/transcript`);
  return handleResponse<TranscriptLine[]>(res);
}

export async function fetchChapters(projectId: number): Promise<ChapterListResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/chapters`);
  return handleResponse<ChapterListResponse>(res);
}

export async function generateChapters(projectId: number): Promise<ChapterListResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/generate_chapters`, {
    method: 'POST',
  });
  return handleResponse<ChapterListResponse>(res);
}

export async function updateChapter(
  chapterId: number,
  payload: Partial<Pick<Chapter, 'title' | 'summary' | 'start_sec' | 'end_sec' | 'order'>>,
): Promise<Chapter> {
  const res = await fetch(`${API_BASE}/chapters/${chapterId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Chapter>(res);
}

export async function regenerateChapter(chapterId: number, newStartSec: number): Promise<Chapter> {
  const res = await fetch(`${API_BASE}/chapters/${chapterId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_start_sec: newStartSec }),
  });
  return handleResponse<Chapter>(res);
}

export async function exportBilibili(projectId: number): Promise<string> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/export/bilibili`);
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || 'Export failed');
  }
  return res.text();
}
