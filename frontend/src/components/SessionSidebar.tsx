import { Plus, MessageSquare } from 'lucide-react';
import { useAgentStore } from '../store/agentStore';

export function SessionSidebar() {
    const { sessions, activeSessionId, createNewSession, setActiveSession } = useAgentStore();

    return (
        <aside className="w-56 shrink-0 border-r border-border bg-surface flex flex-col">
            <div className="h-12 px-3 border-b border-border flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">Sessions</span>
                <button
                    type="button"
                    onClick={createNewSession}
                    className="p-1.5 rounded hover:bg-surface-hover text-text"
                    title="New session"
                >
                    <Plus size={16} />
                </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {sessions.map((session) => (
                    <button
                        key={session.id}
                        type="button"
                        onClick={() => setActiveSession(session.id)}
                        className={`w-full text-left px-2 py-2 rounded text-sm flex gap-2 items-start ${
                            activeSessionId === session.id
                                ? 'bg-brand-muted text-brand border border-brand/30'
                                : 'text-text hover:bg-surface-hover'
                        }`}
                    >
                        <MessageSquare size={14} className="mt-0.5 shrink-0" />
                        <span className="truncate">{session.title}</span>
                    </button>
                ))}
            </div>
        </aside>
    );
}
