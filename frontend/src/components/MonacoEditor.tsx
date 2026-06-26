import React from 'react';
import { Editor } from '@monaco-editor/react';
import { useAgentStore } from '../store/agentStore';
import { api } from '../api/backend';
import { Save, Loader2, Lock, Unlock } from 'lucide-react';

const langMap: Record<string, string> = {
    py: 'python', js: 'javascript', ts: 'typescript',
    tsx: 'typescriptreact', jsx: 'javascriptreact',
    rs: 'rust', go: 'go', json: 'json', html: 'html', css: 'css',
    abap: 'abap'
};

export const CodeEditor: React.FC = () => {
    const {
        activeFileBySession,
        filesBySession,
        activeSessionId,
        setFile,
        addLog,
        streamingFileBySession,
        lockedFilesBySession,
        toggleFileLock,
    } = useAgentStore();
    const [isSaving, setIsSaving] = React.useState(false);
    const [isDirty, setIsDirty] = React.useState(false);
    const editorRef = React.useRef<any>(null);
    
    // Get files for current session
    const files = filesBySession[activeSessionId] || {};
    const activeFile = activeFileBySession[activeSessionId] || null;
    
    // Streaming state
    const streamingFile = streamingFileBySession[activeSessionId];
    const isStreaming = !!(streamingFile?.isStreaming && streamingFile?.path === activeFile);
    
    const lockedFiles = lockedFilesBySession[activeSessionId] || [];
    const isLocked = activeFile ? lockedFiles.includes(activeFile) : false;
    
    const content = activeFile ? files[activeFile] || '' : '';
    const contentRef = React.useRef(content);
    contentRef.current = content;

    const handleSave = React.useCallback(async () => {
        if (!activeFile || isSaving) return;
        setIsSaving(true);
        try {
            await api.sandbox.writeFile(activeSessionId, activeFile, contentRef.current);
            addLog(`> Saved changes to ${activeFile}`, activeSessionId);
            setIsDirty(false);
        } catch (err) {
            console.error(err);
            addLog(`> ❌ Failed to save ${activeFile}: ${err instanceof Error ? err.message : String(err)}`, activeSessionId);
        } finally {
            setIsSaving(false);
        }
    }, [activeFile, activeSessionId, isSaving, addLog]);

    const handleSaveRef = React.useRef(handleSave);
    handleSaveRef.current = handleSave;

    // Track active file change to reset dirty state
    React.useEffect(() => {
        setIsDirty(false);
    }, [activeFile]);

    // Auto-scroll to bottom during streaming
    React.useEffect(() => {
        if (isStreaming && editorRef.current) {
            const model = editorRef.current.getModel();
            if (model) {
                const lineCount = model.getLineCount();
                editorRef.current.revealLine(lineCount);
            }
        }
    }, [content, isStreaming]);

    if (!activeFile) {
        return (
            <div className="h-full w-full flex items-center justify-center text-text-muted bg-[#1e1e1e]">
                <p>Select a file to view or edit code</p>
            </div>
        );
    }
    
    const ext = activeFile.split('.').pop() || '';
    const lang = langMap[ext] || 'plaintext';

    const handleEditorDidMount = (editor: any, monaco: any) => {
        editorRef.current = editor;
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            handleSaveRef.current?.();
        });
    };

    const handleChange = (val: string | undefined) => {
        if (isStreaming) return; // Don't track user edits during streaming
        setFile(activeFile, val || '');
        setIsDirty(true);
    };

    const lineCount = content.split('\n').length;

    return (
        <div className="h-full w-full relative">
            <div className="absolute top-0 left-0 right-0 bg-[#252526] text-[#cccccc] text-xs py-1 px-4 border-b border-[#3c3c3c] z-10 flex justify-between items-center">
                <span className="flex items-center gap-1.5">
                    {activeFile}
                    {isDirty && <span className="text-yellow-500 font-bold">*</span>}
                    {isLocked && (
                        <span className="flex items-center gap-1 text-amber-500 font-medium ml-1.5" title="Locked (AI cannot modify)">
                            <Lock size={11} />
                            <span className="text-[10px] uppercase tracking-wider">Locked</span>
                        </span>
                    )}
                    {isStreaming && (
                        <span className="flex items-center gap-1.5 text-green-400 text-[10px] ml-2">
                            <span className="animate-pulse">●</span> 
                            AI writing...
                        </span>
                    )}
                </span>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => activeFile && toggleFileLock(activeFile, activeSessionId)}
                        className={`p-1 rounded transition-colors ${
                            isLocked 
                                ? 'text-amber-500 hover:text-amber-400 hover:bg-[#333333]' 
                                : 'text-[#cccccc] hover:text-brand hover:bg-[#333333]'
                        }`}
                        title={isLocked ? "Unlock file (Allow AI edits)" : "Lock file (Prevent AI edits)"}
                    >
                        {isLocked ? <Lock size={12} /> : <Unlock size={12} />}
                    </button>
                    {isStreaming && (
                        <span className="text-green-400 text-[10px] font-mono">
                            {lineCount} lines
                        </span>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={isSaving || isStreaming}
                        className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors flex items-center gap-1 text-white ${
                            isDirty && !isStreaming
                                ? 'bg-green-600 hover:bg-green-700' 
                                : 'bg-gray-700 hover:bg-gray-600 opacity-80'
                        }`}
                    >
                        <Save size={10} />
                        {isSaving ? 'Saving...' : 'Save'}
                    </button>
                    <span className="text-brand text-[10px]">{lang}</span>
                </div>
            </div>
            <div className="pt-6 h-full w-full">
                <Editor
                    language={lang}
                    value={content}
                    onChange={handleChange}
                    onMount={handleEditorDidMount}
                    theme="vs-dark"
                    options={{
                        fontSize: 14,
                        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                        minimap: { enabled: false },
                        automaticLayout: true,
                        scrollBeyondLastLine: false,
                        padding: { top: 16 },
                        wordWrap: "on",
                        readOnly: isStreaming,
                    }}
                />
            </div>

            {/* Streaming progress overlay */}
            {isStreaming && (
                <div className="absolute bottom-3 right-4 bg-green-900/80 text-green-300 
                                text-xs px-3 py-1.5 rounded-full flex items-center gap-2
                                border border-green-700/50 backdrop-blur-sm shadow-lg">
                    <Loader2 size={12} className="animate-spin" />
                    <span>{lineCount} lines</span>
                    <span className="text-green-500/60">|</span>
                    <span className="text-green-400/80">{content.length} chars</span>
                </div>
            )}
        </div>
    );
};
