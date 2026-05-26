import React from 'react';
import { Editor } from '@monaco-editor/react';
import { useAgentStore } from '../store/agentStore';

const langMap: Record<string, string> = {
    py: 'python', js: 'javascript', ts: 'typescript',
    tsx: 'typescriptreact', jsx: 'javascriptreact',
    rs: 'rust', go: 'go', json: 'json', html: 'html', css: 'css',
    abap: 'abap'
};

export const CodeEditor: React.FC = () => {
    const { activeFileBySession, filesBySession, activeSessionId, setFile } = useAgentStore();
    
    // Get files for current session
    const files = filesBySession[activeSessionId] || {};
    const activeFile = activeFileBySession[activeSessionId] || null;
    
    if (!activeFile) {
        return (
            <div className="h-full w-full flex items-center justify-center text-text-muted bg-[#1e1e1e]">
                <p>Select a file to view code</p>
            </div>
        );
    }
    
    const content = files[activeFile] || '';
    const ext = activeFile.split('.').pop() || '';
    const lang = langMap[ext] || 'plaintext';

    return (
        <div className="h-full w-full relative">
            <div className="absolute top-0 left-0 right-0 bg-[#252526] text-[#cccccc] text-xs py-1 px-4 border-b border-[#3c3c3c] z-10 flex justify-between items-center">
                <span>{activeFile}</span>
                <span className="text-brand text-[10px]">{lang}</span>
            </div>
            <div className="pt-6 h-full w-full">
                <Editor
                    language={lang}
                    value={content}
                    onChange={(val) => setFile(activeFile, val || '')}
                    theme="vs-dark"
                    options={{
                        fontSize: 14,
                        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                        minimap: { enabled: false },
                        automaticLayout: true,
                        scrollBeyondLastLine: false,
                        padding: { top: 16 },
                        wordWrap: "on"
                    }}
                />
            </div>
        </div>
    );
};
