import React, { useState } from 'react';
import { File, Folder, ChevronRight, RefreshCw, Lock, Unlock } from 'lucide-react';
import { useAgentStore } from '../store/agentStore';
import { useAgentStream } from '../hooks/useAgentStream';

export const FileBrowser: React.FC = () => {
    const {
        filesBySession,
        activeFileBySession,
        activeSessionId,
        setActiveFile,
        lockedFilesBySession,
        toggleFileLock,
    } = useAgentStore();
    const { refreshSandbox } = useAgentStream();
    const [isRefreshing, setIsRefreshing] = useState(false);
    
    // Get files and active file for current session
    const files = filesBySession[activeSessionId] || {};
    const activeFile = activeFileBySession[activeSessionId] || null;
    const lockedFiles = lockedFilesBySession[activeSessionId] || [];
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
                        {fileList.map((path) => {
                            const isLocked = lockedFiles.includes(path);
                            return (
                                <div 
                                    key={path}
                                    className={`group flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-colors ${
                                        activeFile === path ? 'bg-brand/20 text-brand font-medium' : 'text-text hover:bg-surface-hover'
                                    }`}
                                >
                                    <div 
                                        className="flex items-center gap-2 flex-1 min-w-0"
                                        onClick={() => setActiveFile(path)}
                                    >
                                        <ChevronRight size={12} className={activeFile === path ? 'opacity-100' : 'opacity-0'} />
                                        <File size={14} className={isLocked ? 'text-amber-500' : 'text-text-muted'} />
                                        <span className="truncate">{path}</span>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleFileLock(path, activeSessionId);
                                        }}
                                        className={`p-1 rounded hover:bg-surface-hover transition-colors ${
                                            isLocked 
                                                ? 'text-amber-500 opacity-100' 
                                                : 'text-text-muted opacity-0 group-hover:opacity-100 hover:text-brand'
                                        }`}
                                        title={isLocked ? "Unlock File (Allow modifications)" : "Lock File (Prevent modifications)"}
                                    >
                                        {isLocked ? <Lock size={12} /> : <Unlock size={12} />}
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};
