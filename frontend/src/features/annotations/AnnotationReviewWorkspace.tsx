import React, { useState } from 'react';
import {
  Check,
  X,
  Edit2,
  Save,
  Clock,
  Download,
  Copy,
  FileSpreadsheet,
  Bookmark,
  BookmarkCheck,
  AlertTriangle,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { api } from '../../shared/api/client';
import {
  AnnotationReviewSession,
  EventReviewItem,
  QuestionReviewItem,
  ReviewStatus,
} from '../../shared/types';

interface AnnotationReviewWorkspaceProps {
  session: AnnotationReviewSession | null;
  onSessionUpdated: (updated: AnnotationReviewSession) => void;
  onOpenExportModal: () => void;
  onSeekInterval: (interval: { start: number; end: number }) => void;
  latestGenerationId?: string | null;
}

function getEffectiveStart(e: EventReviewItem): number {
  return e.edited_start_seconds ?? e.original_start_seconds;
}

function getEffectiveEnd(e: EventReviewItem): number {
  return e.edited_end_seconds ?? e.original_end_seconds;
}

function getEffectiveDescription(e: EventReviewItem): string {
  return e.edited_description ?? e.original_description;
}

function getEffectiveActor(e: EventReviewItem): string | null | undefined {
  return e.edited_actor ?? e.original_actor;
}

function getEffectiveQuestion(q: QuestionReviewItem): string {
  return q.edited_question ?? q.original_question;
}

function getEffectiveAnswer(q: QuestionReviewItem): string | null | undefined {
  return q.edited_answer ?? q.original_answer;
}

export const AnnotationReviewWorkspace: React.FC<AnnotationReviewWorkspaceProps> = ({
  session,
  onSessionUpdated,
  onOpenExportModal,
  onSeekInterval,
  latestGenerationId,
}) => {
  const [activeTab, setActiveTab] = useState<'events' | 'questions'>('events');
  const [editingEventIdx, setEditingEventIdx] = useState<number | null>(null);
  const [eventEditDraft, setEventEditDraft] = useState<Partial<EventReviewItem>>({});

  const [editingQuestionIdx, setEditingQuestionIdx] = useState<number | null>(null);
  const [questionEditDraft, setQuestionEditDraft] = useState<Partial<QuestionReviewItem>>({});

  const [copiedJson, setCopiedJson] = useState(false);
  const [isSavingPersistent, setIsSavingPersistent] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isSyncingQuestions, setIsSyncingQuestions] = useState(false);

  if (!session) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500">
        <p className="text-sm">No active annotation review session</p>
        <p className="text-xs text-slate-600 mt-1">Run video understanding or select an analysis to review annotations</p>
      </div>
    );
  }

  const handleEventStatus = async (idx: number, status: ReviewStatus, notes?: string) => {
    try {
      const updated = await api.updateEventReview(session.review_id, idx, {
        status,
        reviewer_notes: notes,
      });
      onSessionUpdated(updated);
    } catch (err) {
      console.error('Failed to update event review', err);
    }
  };

  const saveEventEdit = async (idx: number) => {
    try {
      const updated = await api.updateEventReview(session.review_id, idx, {
        ...eventEditDraft,
        status: 'edited',
      });
      onSessionUpdated(updated);
      setEditingEventIdx(null);
      setEventEditDraft({});
    } catch (err) {
      console.error('Failed to save event edits', err);
    }
  };

  const handleQuestionStatus = async (idx: number, status: ReviewStatus, notes?: string) => {
    try {
      const updated = await api.updateQuestionReview(session.review_id, idx, {
        status,
        reviewer_notes: notes,
      });
      onSessionUpdated(updated);
    } catch (err) {
      console.error('Failed to update question review', err);
    }
  };

  const saveQuestionEdit = async (idx: number) => {
    try {
      const updated = await api.updateQuestionReview(session.review_id, idx, {
        ...questionEditDraft,
        status: 'edited',
      });
      onSessionUpdated(updated);
      setEditingQuestionIdx(null);
      setQuestionEditDraft({});
    } catch (err) {
      console.error('Failed to save question edits', err);
    }
  };

  const handleCopyReviewJson = () => {
    navigator.clipboard.writeText(JSON.stringify(session, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const handleDownloadReviewJson = () => {
    const blob = new Blob([JSON.stringify(session, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `review_session_${session.review_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSavePersistent = async () => {
    if (isSavingPersistent) return;
    setIsSavingPersistent(true);
    try {
      const updated = await api.saveReviewSessionPersistent(session.review_id);
      onSessionUpdated(updated);
      setSaveSuccess(true);
    } catch (err) {
      console.error('Failed to save review session permanently', err);
    } finally {
      setIsSavingPersistent(false);
    }
  };

  const handleSyncQuestions = async (genId: string) => {
    setIsSyncingQuestions(true);
    try {
      const updated = await api.syncReviewSessionQuestions(session.review_id, genId);
      onSessionUpdated(updated);
    } catch (err) {
      console.error('Failed to sync questions', err);
    } finally {
      setIsSyncingQuestions(false);
    }
  };

  const totalItems = session.events.length + session.questions.length;
  const acceptedItems =
    session.events.filter((e) => e.status === 'accepted' || e.status === 'edited').length +
    session.questions.filter((q) => q.status === 'accepted' || q.status === 'edited').length;

  const isPersistent = session.is_persistent || saveSuccess;
  const hasNewerQuestions =
    latestGenerationId && latestGenerationId !== session.generation_id;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col space-y-4">
      {/* Prominent MOCK Notice Banner */}
      {session.is_mock && (
        <div
          data-testid="review-mock-banner"
          className="flex items-start space-x-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs"
        >
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold tracking-wide">MOCK REVIEW DATA — SIMULATED CANDIDATES</span>
            <p className="text-[11px] text-amber-400/80 mt-0.5">
              These candidate events and questions are derived from mock simulation. Review decisions will be exported with explicit mock test provenance and cannot be classified as verified ground truth.
            </p>
          </div>
        </div>
      )}

      {/* Legacy / Unverified Notice Banner */}
      {!session.is_mock && (session.inference_mode === 'legacy_unverified' || session.inference_mode === 'unknown') && (
        <div
          data-testid="review-legacy-banner"
          className="flex items-start space-x-2.5 p-3 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 text-xs"
        >
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold tracking-wide text-amber-300">HISTORICAL DATA — PROVENANCE UNVERIFIED</span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              These candidate items originate from historical archives without verified inference provenance. Exports will indicate unverified status to protect dataset integrity.
            </p>
          </div>
        </div>
      )}

      {/* Header with Stats & Export */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-3 gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold text-white">Whodunnit Review Workspace</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded font-mono">
              {acceptedItems}/{totalItems} Verified
            </span>
            {isPersistent && (
              <span
                data-testid="review-persistent-badge"
                className="text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded font-mono flex items-center space-x-1"
              >
                <BookmarkCheck className="w-3 h-3 text-emerald-400" />
                <span>Saved to Library</span>
              </span>
            )}
            {session.video_available === false && (
              <span
                data-testid="review-video-unavailable-badge"
                className="text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded font-mono flex items-center space-x-1"
              >
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                <span>Original clip expired (results preserved)</span>
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Human verification loop: accept, edit, or reject AI detections
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={handleCopyReviewJson}
            data-testid="copy-review-json-btn"
            className="flex items-center space-x-1 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
            title="Copy review session JSON"
          >
            {copiedJson ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedJson ? 'Copied JSON' : 'Copy JSON'}</span>
          </button>

          <button
            onClick={handleDownloadReviewJson}
            data-testid="download-review-json-btn"
            className="flex items-center space-x-1 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
            title="Download review session as JSON"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>JSON</span>
          </button>

          <a
            href={api.getWhodunnitCsvExportUrl(session.review_id)}
            download
            data-testid="download-review-csv-link"
            className="flex items-center space-x-1 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
            title="Download CSV spreadsheet"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>CSV</span>
          </a>

          {!isPersistent && (
            <button
              onClick={handleSavePersistent}
              disabled={isSavingPersistent}
              data-testid="save-review-persistent-btn"
              className="flex items-center space-x-1 text-xs text-indigo-200 hover:text-white bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-700/60 px-2.5 py-1.5 rounded-lg transition shadow-sm font-medium"
              title="Save review session permanently to library"
            >
              {isSavingPersistent ? (
                <span className="w-3 h-3 border-2 border-indigo-400/40 border-t-indigo-400 rounded-full animate-spin" />
              ) : (
                <Bookmark className="w-3.5 h-3.5 text-indigo-400" />
              )}
              <span>Save to Library</span>
            </button>
          )}

          <button
            onClick={onOpenExportModal}
            data-testid="open-whodunnit-export-btn"
            className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition shadow ml-1"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Whodunnit Package</span>
          </button>
        </div>
      </div>

      {/* Sync questions alert if newer questions exist */}
      {hasNewerQuestions && (
        <div
          data-testid="sync-questions-alert"
          className="bg-indigo-950/40 border border-indigo-800/50 rounded-lg p-2.5 flex items-center justify-between text-xs text-indigo-200"
        >
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
            <span>Newly generated questions are available ({latestGenerationId}).</span>
          </div>
          <button
            onClick={() => latestGenerationId && handleSyncQuestions(latestGenerationId)}
            disabled={isSyncingQuestions}
            className="flex items-center space-x-1 bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 rounded text-xs transition"
          >
            <RefreshCw className={`w-3 h-3 ${isSyncingQuestions ? 'animate-spin' : ''}`} />
            <span>Sync Questions</span>
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab('events')}
          data-testid="review-tab-events"
          className={`pb-2 px-3 text-xs font-medium border-b-2 transition ${
            activeTab === 'events'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Observable Events ({session.events.length})
        </button>

        <button
          onClick={() => setActiveTab('questions')}
          data-testid="review-tab-questions"
          className={`pb-2 px-3 text-xs font-medium border-b-2 transition ${
            activeTab === 'questions'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Whodunnit Questions ({session.questions.length})
        </button>
      </div>

      {/* Events Tab */}
      {activeTab === 'events' && (
        <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
          {session.events.map((e) => {
            const isEditing = editingEventIdx === e.event_index;

            return (
              <div
                key={e.event_index}
                data-testid={`event-review-item-${e.event_index}`}
                className={`p-3 rounded-lg border text-xs transition ${
                  e.status === 'accepted'
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : e.status === 'edited'
                    ? 'bg-indigo-950/20 border-indigo-800/40'
                    : e.status === 'rejected'
                    ? 'bg-rose-950/20 border-rose-800/40 opacity-70'
                    : 'bg-slate-950/60 border-slate-800'
                }`}
              >
                {isEditing ? (
                  /* Edit Form */
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-400">Start (seconds)</label>
                        <input
                          type="number"
                          step="0.1"
                          defaultValue={getEffectiveStart(e)}
                          onChange={(ev) =>
                            setEventEditDraft((d) => ({
                              ...d,
                              edited_start_seconds: parseFloat(ev.target.value),
                            }))
                          }
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400">End (seconds)</label>
                        <input
                          type="number"
                          step="0.1"
                          defaultValue={getEffectiveEnd(e)}
                          onChange={(ev) =>
                            setEventEditDraft((d) => ({
                              ...d,
                              edited_end_seconds: parseFloat(ev.target.value),
                            }))
                          }
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-[10px] text-slate-400">Description</label>
                      <input
                        type="text"
                        defaultValue={getEffectiveDescription(e)}
                        onChange={(ev) =>
                          setEventEditDraft((d) => ({
                            ...d,
                            edited_description: ev.target.value,
                          }))
                        }
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-400">Actor</label>
                        <input
                          type="text"
                          defaultValue={getEffectiveActor(e) || ''}
                          onChange={(ev) =>
                            setEventEditDraft((d) => ({
                              ...d,
                              edited_actor: ev.target.value,
                            }))
                          }
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400">Reviewer Notes</label>
                        <input
                          type="text"
                          defaultValue={e.reviewer_notes || ''}
                          onChange={(ev) =>
                            setEventEditDraft((d) => ({
                              ...d,
                              reviewer_notes: ev.target.value,
                            }))
                          }
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end space-x-2 pt-1">
                      <button
                        onClick={() => setEditingEventIdx(null)}
                        className="px-2.5 py-1 text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => saveEventEdit(e.event_index)}
                        className="flex items-center space-x-1 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded"
                      >
                        <Save className="w-3 h-3" />
                        <span>Save Edits</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  /* Display Row */
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() =>
                            onSeekInterval({
                              start: getEffectiveStart(e),
                              end: getEffectiveEnd(e),
                            })
                          }
                          className="font-mono text-indigo-400 hover:text-indigo-300 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/50 flex items-center space-x-1"
                        >
                          <Clock className="w-2.5 h-2.5" />
                          <span>
                            {getEffectiveStart(e).toFixed(1)}s - {getEffectiveEnd(e).toFixed(1)}s
                          </span>
                        </button>

                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase ${
                            e.status === 'accepted'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : e.status === 'edited'
                              ? 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                              : e.status === 'rejected'
                              ? 'bg-rose-950 text-rose-400 border border-rose-800'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {e.status}
                        </span>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleEventStatus(e.event_index, 'accepted')}
                          title="Accept"
                          data-testid={`accept-event-btn-${e.event_index}`}
                          className="p-1 rounded hover:bg-emerald-900/40 text-slate-400 hover:text-emerald-400 transition"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => {
                            setEditingEventIdx(e.event_index);
                            setEventEditDraft({
                              edited_start_seconds: getEffectiveStart(e),
                              edited_end_seconds: getEffectiveEnd(e),
                              edited_description: getEffectiveDescription(e),
                              edited_actor: getEffectiveActor(e),
                              reviewer_notes: e.reviewer_notes,
                            });
                          }}
                          title="Edit"
                          data-testid={`edit-event-btn-${e.event_index}`}
                          className="p-1 rounded hover:bg-indigo-900/40 text-slate-400 hover:text-indigo-400 transition"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => handleEventStatus(e.event_index, 'rejected')}
                          title="Reject"
                          data-testid={`reject-event-btn-${e.event_index}`}
                          className="p-1 rounded hover:bg-rose-900/40 text-slate-400 hover:text-rose-400 transition"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <p className="text-slate-200 font-medium">
                      {getEffectiveDescription(e)}
                    </p>

                    {e.reviewer_notes && (
                      <p className="text-[11px] text-slate-400 italic">
                        Notes: {e.reviewer_notes}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Questions Tab */}
      {activeTab === 'questions' && (
        <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
          {session.questions.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-6">
              No questions generated yet. Submit a question generation job first.
            </p>
          ) : (
            session.questions.map((q) => {
              const isEditing = editingQuestionIdx === q.question_index;

              return (
                <div
                  key={q.question_index}
                  data-testid={`question-review-item-${q.question_index}`}
                  className={`p-3 rounded-lg border text-xs transition ${
                    q.status === 'accepted'
                      ? 'bg-emerald-950/20 border-emerald-800/40'
                      : q.status === 'edited'
                      ? 'bg-indigo-950/20 border-indigo-800/40'
                      : q.status === 'rejected'
                      ? 'bg-rose-950/20 border-rose-800/40 opacity-70'
                      : 'bg-slate-950/60 border-slate-800'
                  }`}
                >
                  {isEditing ? (
                    <div className="space-y-2">
                      <div>
                        <label className="text-[10px] text-slate-400">Question Text</label>
                        <input
                          type="text"
                          defaultValue={getEffectiveQuestion(q)}
                          onChange={(ev) =>
                            setQuestionEditDraft((d) => ({
                              ...d,
                              edited_question: ev.target.value,
                            }))
                          }
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                        />
                      </div>

                      <div>
                        <label className="text-[10px] text-slate-400">Answer / Actor</label>
                        <input
                          type="text"
                          defaultValue={getEffectiveAnswer(q) || ''}
                          onChange={(ev) =>
                            setQuestionEditDraft((d) => ({
                              ...d,
                              edited_answer: ev.target.value,
                            }))
                          }
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs"
                        />
                      </div>

                      <div className="flex justify-end space-x-2 pt-1">
                        <button
                          onClick={() => setEditingQuestionIdx(null)}
                          className="px-2.5 py-1 text-slate-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => saveQuestionEdit(q.question_index)}
                          className="flex items-center space-x-1 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded"
                        >
                          <Save className="w-3 h-3" />
                          <span>Save</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase ${
                            q.status === 'accepted'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : q.status === 'edited'
                              ? 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                              : q.status === 'rejected'
                              ? 'bg-rose-950 text-rose-400 border border-rose-800'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {q.status}
                        </span>

                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => handleQuestionStatus(q.question_index, 'accepted')}
                            title="Accept"
                            data-testid={`accept-question-btn-${q.question_index}`}
                            className="p-1 rounded hover:bg-emerald-900/40 text-slate-400 hover:text-emerald-400 transition"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => {
                              setEditingQuestionIdx(q.question_index);
                              setQuestionEditDraft({
                                edited_question: getEffectiveQuestion(q),
                                edited_answer: getEffectiveAnswer(q),
                              });
                            }}
                            title="Edit"
                            data-testid={`edit-question-btn-${q.question_index}`}
                            className="p-1 rounded hover:bg-indigo-900/40 text-slate-400 hover:text-indigo-400 transition"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleQuestionStatus(q.question_index, 'rejected')}
                            title="Reject"
                            data-testid={`reject-question-btn-${q.question_index}`}
                            className="p-1 rounded hover:bg-rose-900/40 text-slate-400 hover:text-rose-400 transition"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <p className="text-slate-100 font-medium">{getEffectiveQuestion(q)}</p>

                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>Answer: <strong className="text-emerald-400">{getEffectiveAnswer(q) || q.actor_reference}</strong></span>
                        {q.evidence_start_seconds !== null &&
                          q.evidence_start_seconds !== undefined && (
                            <button
                              onClick={() =>
                                onSeekInterval({
                                  start: q.evidence_start_seconds!,
                                  end: q.evidence_end_seconds!,
                                })
                              }
                              className="font-mono text-indigo-400 hover:underline"
                            >
                              Interval: {q.evidence_start_seconds.toFixed(1)}s - {q.evidence_end_seconds?.toFixed(1)}s
                            </button>
                          )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};
