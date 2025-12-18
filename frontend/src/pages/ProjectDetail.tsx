import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  exportBilibili,
  fetchChapters,
  fetchProject,
  fetchTranscript,
  generateChapters,
  regenerateChapter,
  updateChapter,
} from '../api';
import type { Chapter, Project, TranscriptLine } from '../types';
import { formatHMS } from '../utils/time';

type Params = {
  id: string;
};

function ProjectDetail() {
  const { id } = useParams<Params>();
  const projectId = Number(id);

  const [project, setProject] = useState<Project | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapterId, setSelectedChapterId] = useState<number | null>(null);
  const [exportText, setExportText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingChapterId, setSavingChapterId] = useState<number | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [hoveredChapterId, setHoveredChapterId] = useState<number | null>(null);
  const transcriptRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!projectId) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [proj, transcriptRes, chaptersRes] = await Promise.all([
          fetchProject(projectId),
          fetchTranscript(projectId),
          fetchChapters(projectId),
        ]);
        setProject(proj);
        setTranscript(transcriptRes);
        setChapters(chaptersRes.chapters);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  const selectedChapter = useMemo(
    () => chapters.find((c) => c.id === selectedChapterId) || null,
    [chapters, selectedChapterId],
  );

  const findNearestLineBySec = (sec: number): TranscriptLine | null => {
    if (!transcript.length) return null;
    let nearest: TranscriptLine | null = null;
    let bestDiff = Number.POSITIVE_INFINITY;
    transcript.forEach((line) => {
      const diff = Math.abs(line.start_sec - sec);
      if (diff < bestDiff) {
        bestDiff = diff;
        nearest = line;
      }
    });
    return nearest;
  };

  const scrollToChapterStart = (chapter: Chapter) => {
    const nearestLine = findNearestLineBySec(chapter.start_sec);
    if (nearestLine) {
      const el = transcriptRefs.current[nearestLine.id];
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleChapterFieldChange = (chapterId: number, field: keyof Chapter, value: string | number) => {
    setChapters((prev) =>
      prev.map((c) => (c.id === chapterId ? { ...c, [field]: value } : c)),
    );
  };

  const refreshChapters = async () => {
    const chaptersRes = await fetchChapters(projectId);
    setChapters(chaptersRes.chapters);
  };

  const saveChapter = async (chapter: Chapter) => {
    setSavingChapterId(chapter.id);
    setError(null);
    try {
      const updated = await updateChapter(chapter.id, {
        title: chapter.title,
        summary: chapter.summary,
        start_sec: chapter.start_sec,
        end_sec: chapter.end_sec,
        order: chapter.order,
      });
      setChapters((prev) => prev.map((c) => (c.id === chapter.id ? updated : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update chapter');
    } finally {
      setSavingChapterId(null);
    }
  };

  const handleLineClick = async (line: TranscriptLine) => {
    if (!selectedChapter) return;
    setRegenerating(true);
    try {
      const updated = await regenerateChapter(selectedChapter.id, line.start_sec);
      setChapters((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate chapter');
    } finally {
      setRegenerating(false);
    }
  };

  const handleGenerate = async () => {
    if (!projectId) return;
    setGenerateLoading(true);
    setError(null);
    try {
      await generateChapters(projectId);
      await refreshChapters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate chapters');
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleExport = async () => {
    if (!projectId) return;
    setExportLoading(true);
    try {
      const text = await exportBilibili(projectId);
      setExportText(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export');
    } finally {
      setExportLoading(false);
    }
  };

  const setChapterStartFromLine = (line: TranscriptLine) => {
    if (!selectedChapter) return;
    handleChapterFieldChange(selectedChapter.id, 'start_sec', line.start_sec);
  };

  const setChapterEndFromLine = (line: TranscriptLine) => {
    if (!selectedChapter) return;
    handleChapterFieldChange(selectedChapter.id, 'end_sec', line.end_sec ?? line.start_sec);
  };

  const getChapterEffectiveEnd = (chapter: Chapter, all: Chapter[], lines: TranscriptLine[]) => {
    const sorted = [...all].sort((a, b) => a.start_sec - b.start_sec);
    const idx = sorted.findIndex((c) => c.id === chapter.id);
    const nextStart = idx >= 0 && idx + 1 < sorted.length ? sorted[idx + 1].start_sec : null;

    // base end: prefer explicit end, else next start, else transcript tail
    let baseEnd =
      chapter.end_sec != null
        ? chapter.end_sec
        : nextStart != null
          ? nextStart
          : lines.length
            ? lines[lines.length - 1].end_sec ?? lines[lines.length - 1].start_sec
            : chapter.start_sec;

    // continuous coverage: if there is a next chapter, clamp end up to its start
    if (nextStart != null) {
      baseEnd = Math.max(baseEnd, nextStart);
    }
    return baseEnd;
  };

  if (loading) {
    return (
      <div className="app-shell">
        <p className="text-slate-600">Loading project...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-shell space-y-4">
        <p className="text-red-600">{error}</p>
        <Link className="text-slate-600 underline" to="/">
          Back to new project
        </Link>
      </div>
    );
  }

  if (!project) return null;

  return (
    <div className="app-shell space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500">Project</p>
          <h1 className="text-2xl font-semibold text-slate-800">{project.title}</h1>
          {project.platform && <p className="text-sm text-slate-500">{project.platform}</p>}
        </div>
        <Link to="/" className="text-sm text-slate-600 underline">
          + New project
        </Link>
      </header>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_380px] gap-4 items-start">
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm flex flex-col h-[70vh]">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800">Transcript</h2>
            <p className="text-xs text-slate-500">
              Click a line to regenerate; or use Set Start/End buttons for manual range.
            </p>
          </div>
          <div className="overflow-auto px-4 py-3 space-y-2">
            {transcript.map((line) => {
              const isInRange =
                selectedChapter &&
                line.start_sec >= (selectedChapter.start_sec || 0) &&
                line.start_sec <= getChapterEffectiveEnd(selectedChapter, chapters, transcript);
              return (
                <div
                  key={line.id}
                  ref={(el) => {
                    transcriptRefs.current[line.id] = el;
                  }}
                  className={`relative rounded-md border px-3 py-2 transition ${
                    isInRange
                      ? 'border-indigo-300 bg-indigo-50'
                      : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <button
                    onClick={() => handleLineClick(line)}
                    className={`text-left flex-1 w-full ${
                      selectedChapter ? 'hover:text-slate-900' : 'cursor-default'
                    }`}
                    disabled={!selectedChapter || regenerating}
                  >
                    <span className="text-xs font-mono text-slate-500 mr-2">
                      [{formatHMS(line.start_sec)}]
                    </span>
                    <span className="text-sm text-slate-800">{line.text}</span>
                  </button>
                  {selectedChapter && (
                    <div className="absolute inset-y-0 right-1 flex items-center gap-1 opacity-0 hover:opacity-100 transition">
                      <button
                        onClick={() => setChapterStartFromLine(line)}
                        className="h-6 w-6 text-[10px] rounded bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 flex items-center justify-center"
                        title="Set Start"
                      >
                        S
                      </button>
                      <button
                        onClick={() => setChapterEndFromLine(line)}
                        className="h-6 w-6 text-[10px] rounded bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 flex items-center justify-center"
                        title="Set End"
                      >
                        E
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg shadow-sm flex flex-col h-[70vh] lg:max-w-md w-full justify-self-end">
          <div className="px-4 py-3 border-b border-slate-200 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">Chapters</h2>
                <p className="text-sm text-slate-500">
                  Chapters: {chapters.length} / {project.max_chapters}
                </p>
              </div>
              <button
                onClick={handleGenerate}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
                disabled={generateLoading}
              >
                {generateLoading ? 'Generating...' : 'Generate'}
              </button>
            </div>
            <button
              onClick={handleExport}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
              disabled={exportLoading}
            >
              {exportLoading ? 'Exporting...' : 'Export Bilibili chapters'}
            </button>
            {chapters.length > project.max_chapters && (
              <p className="text-sm text-red-600">Over max chapters limit</p>
            )}
          </div>

          <div className="overflow-auto px-4 py-3 space-y-2 flex-1">
            {chapters.length === 0 && (
              <p className="text-sm text-slate-500">No chapters yet. Generate on backend first.</p>
            )}
            {chapters.map((chapter, idx) => {
              const isSelected = selectedChapterId === chapter.id;
              return (
                <div
                  key={chapter.id}
                  className="relative"
                  onMouseEnter={() => setHoveredChapterId(chapter.id)}
                  onMouseLeave={() => setHoveredChapterId((prev) => (prev === chapter.id ? null : prev))}
                >
                  <button
                    onClick={() => {
                      setSelectedChapterId(chapter.id);
                      scrollToChapterStart(chapter);
                    }}
                    className={`w-full flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-100 bg-slate-50 hover:bg-slate-100'
                    }`}
                  >
                    <span className="w-6 text-xs font-semibold text-slate-600 text-right">{idx + 1}</span>
                    <div className="flex-1 min-w-0 flex items-center gap-2 text-sm text-slate-800 truncate">
                      <span className="font-mono text-xs text-slate-600">{formatHMS(chapter.start_sec)}</span>
                      <span className="text-slate-300">|</span>
                      {isSelected ? (
                        <input
                          type="text"
                          className="w-full rounded-md border border-slate-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200"
                          value={chapter.title}
                          onChange={(e) => handleChapterFieldChange(chapter.id, 'title', e.target.value)}
                        />
                      ) : (
                        <span className="truncate">{chapter.title}</span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500">{isSelected ? 'Selected' : 'Select'}</span>
                  </button>
                  {hoveredChapterId === chapter.id && (
                    <div className="absolute left-0 top-full mt-1 w-full rounded-md border border-slate-200 bg-white shadow-lg p-3 text-sm text-slate-700 z-10">
                      <div className="text-xs font-semibold text-slate-500 mb-1">AI Summary</div>
                      <p className="text-sm text-slate-700">
                        {chapter.summary ? chapter.summary : 'No summary available.'}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="border-t border-slate-200 px-4 py-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-800">Save changes</span>
              {selectedChapter && (
                <span className="text-xs text-slate-500">
                  {formatHMS(selectedChapter.start_sec)} · ID {selectedChapter.id}
                </span>
              )}
            </div>
            <button
              onClick={() => selectedChapter && saveChapter(selectedChapter)}
              disabled={!selectedChapter || savingChapterId === selectedChapter?.id}
              className="w-full text-sm rounded-md bg-slate-900 text-white px-3 py-2 hover:bg-slate-800 disabled:opacity-60"
            >
              {savingChapterId && selectedChapter && savingChapterId === selectedChapter.id
                ? 'Saving...'
                : selectedChapter
                  ? 'Save selected chapter title'
                  : 'Select a chapter to edit'}
            </button>
          </div>

          <div className="border-t border-slate-200 px-4 py-3">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-slate-700">Exported text</span>
              <textarea
                value={exportText}
                readOnly
                placeholder="Click Export to load Bilibili-formatted chapters"
                className="w-full min-h-[120px] rounded-md border border-slate-300 px-3 py-2 bg-slate-50 text-sm"
              />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectDetail;
