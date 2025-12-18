import type { FormEvent } from 'react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createProjectFromTranscript } from '../api';

const MAX_CHAPTERS_DEFAULT = 10;

function ProjectCreate() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [platform, setPlatform] = useState('');
  const [transcriptText, setTranscriptText] = useState('');
  const [fileError, setFileError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    try {
      const text = await file.text();
      setTranscriptText(text);
      setFileError(null);
    } catch (err) {
      setFileError('Failed to read file');
    }
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!transcriptText.trim()) {
      setError('Transcript text is required (paste or upload a .txt)');
      return;
    }
    setLoading(true);
    try {
      const resp = await createProjectFromTranscript({
        title: title.trim(),
        platform: platform.trim() || null,
        max_chapters: MAX_CHAPTERS_DEFAULT,
        transcript_txt: transcriptText,
      });
      navigate(`/projects/${resp.project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500">Chapter Generator</p>
          <h1 className="text-2xl font-semibold text-slate-800">New Project</h1>
        </div>
      </header>

      <div className="bg-white shadow-sm border border-slate-200 rounded-lg p-6">
        <form className="space-y-5" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-slate-700">Project title *</span>
              <input
                type="text"
                className="rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-300"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Market talk Q1"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-slate-700">Platform (optional)</span>
              <input
                type="text"
                className="rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-300"
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                placeholder="bilibili"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-slate-700">Transcript text *</span>
              <textarea
                className="min-h-[220px] rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-300"
                value={transcriptText}
                onChange={(e) => setTranscriptText(e.target.value)}
                placeholder="Paste transcript content here..."
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-slate-700">Or upload .txt</span>
              <input
                type="file"
                accept=".txt"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
                className="rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-300"
              />
              {fileError && <p className="text-sm text-red-600">{fileError}</p>}
              <p className="text-xs text-slate-500">
                Supports the timestamped format like <code>[00:00:00 --&gt; 00:00:01] text</code>.
              </p>
            </label>
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {loading ? 'Creating...' : 'Create project'}
            </button>
            <p className="text-sm text-slate-500">Chapters will be generated in the next step.</p>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ProjectCreate;
