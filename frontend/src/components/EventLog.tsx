import { Activity } from 'lucide-react';
import { useAgentStore } from '../store/agentStore';

export function EventLog() {
    const { activeSessionId, eventsBySession } = useAgentStore();
    const events = eventsBySession[activeSessionId] || [];

    return (
        <div className="h-full bg-surface border-l border-border flex flex-col">
            <div className="h-9 px-3 border-b border-border flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                <Activity size={14} className="text-brand" />
                Events
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1 text-xs">
                {events.length === 0 ? (
                    <div className="text-text-muted p-2">No events yet.</div>
                ) : events.slice(-80).map((event) => (
                    <div key={event.id} className="border border-border rounded p-2 bg-background/50">
                        <div className="flex justify-between gap-2">
                            <span className="text-brand">{event.type}</span>
                            <span className="text-text-muted truncate">{event.node || 'graph'}</span>
                        </div>
                        {event.chunk && <div className="text-text-muted truncate mt-1">{event.chunk}</div>}
                    </div>
                ))}
            </div>
        </div>
    );
}
