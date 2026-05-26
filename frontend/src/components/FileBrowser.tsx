import React, { useState } from 'react';
import { File, Folder, ChevronRight, RefreshCw } from 'lucide-react';
import { useAgentStore } from '../store/agentStore';
import { useAgentStream } from '../hooks/useAgentStream';

export const FileBrowser: React.FC = () => {
    const { filesBySession, activeFileBySession, activeSessionId, setActiveFile } = useAgentStore();
    const { refreshSandbox } = useAgentStream();
    const [isRefreshing, setIsRefreshing] = useState(false);
    
    // Get files and active file for current session
    const files = filesBySession[activeSessionId] || {};
    const activeFile = activeFileBySession[activeSessionId] || null;
    const fileList = Object.keys(files).sort();

    const handleRefresh = async () => {
        if (!activeSessionId || isRefreshing) return;
        setIsRefreshing(true);
        try {
            await refreshSandbox(activeSessionId);
        } finally {
            setIsRefreshing(false);
        }
    };

    return (
        <div className="h-full bg-surface border-r border-border text-sm flex flex-col">
            <div className="p-3 border-b border-border font-semibold text-text uppercase tracking-wider text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Folder size={14} className="text-brand" />
                    Workspace
                </div>
                <button
                    onClick={handleRefresh}
                    className={`p-1 hover:text-brand transition-colors rounded hover:bg-surface-hover ${
                        isRefreshing ? 'animate-spin text-brand' : 'text-text-muted'
                    }`}
                    title="Refresh Workspace Files"
                    disabled={!activeSessionId || isRefreshing}
                >
                    <RefreshCw size={12} />
                </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
                {fileList.length === 0 ? (
                    <div className="text-text-muted italic p-2 text-xs">No files generated yet...</div>
                ) : (
                    <div className="space-y-1">
                        {fileList.map((path) => (
                            <div 
                                key={path}
                                onClick={() => setActiveFile(path)}
                                className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors ${
                                    activeFile === path ? 'bg-brand/20 text-brand font-medium' : 'text-text hover:bg-surface-hover'
                                }`}
                            >
                                <ChevronRight size={12} className={activeFile === path ? 'opacity-100' : 'opacity-0'} />
                                <File size={14} />
                                <span className="truncate">{path}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
