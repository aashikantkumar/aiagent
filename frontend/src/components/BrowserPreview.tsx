import { Globe } from 'lucide-react';
import { useAgentStore } from '../store/agentStore';

export function BrowserPreview() {
    const { previewUrlBySession, activeSessionId } = useAgentStore();
    const previewUrl = previewUrlBySession[activeSessionId] || null;

    return (
        <div className="h-full bg-background border-l border-border flex flex-col">
            <div className="h-9 px-3 border-b border-border bg-surface flex items-center gap-2 text-xs text-text-muted">
                <Globe size={14} className="text-brand" />
                <span className="truncate">{previewUrl || 'No preview running'}</span>
            </div>
            <div className="flex-1 bg-white">
                {previewUrl ? (
                    <iframe title="Sandbox preview" src={previewUrl} className="w-full h-full border-0" />
                ) : (
                    <div className="h-full bg-background text-text-muted flex items-center justify-center text-sm">
                        Run a generated app to see the browser preview.
                    </div>
                )}
            </div>
        </div>
    );
}
