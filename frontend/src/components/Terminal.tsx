import React, { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { useAgentStore } from '../store/agentStore';
import { useAgentStream } from '../hooks/useAgentStream';
import '@xterm/xterm/css/xterm.css';
import { Terminal as TerminalIcon, Activity } from 'lucide-react';

const AgentLogsViewer: React.FC = () => {
    const termRef = useRef<HTMLDivElement>(null);
    const xtermRef = useRef<XTerm | null>(null);
    const { logsBySession, activeSessionId } = useAgentStore();
    const logs = logsBySession[activeSessionId] || '';
    const lastLogsLength = useRef(0);
    const lastSessionId = useRef(activeSessionId);

    useEffect(() => {
        if (!termRef.current) return;

        const term = new XTerm({
            theme: {
                background: '#0f1115',
                foreground: '#9ca3af',
                cursor: 'transparent'
            },
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontSize: 12,
            disableStdin: true,
            convertEol: true,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(termRef.current);
        fitAddon.fit();
        xtermRef.current = term;

        term.writeln('\x1b[35m[Sandbox Environment Initialized]\x1b[0m');

        const resizeObserver = new ResizeObserver(() => {
            try {
                fitAddon.fit();
            } catch (e) {}
        });
        resizeObserver.observe(termRef.current);

        return () => {
            resizeObserver.disconnect();
            term.dispose();
        };
    }, []);

    // Reset terminal when session changes
    useEffect(() => {
        if (lastSessionId.current !== activeSessionId) {
            if (xtermRef.current) {
                xtermRef.current.clear();
                xtermRef.current.writeln('\x1b[35m[Sandbox Environment Initialized]\x1b[0m');
                lastLogsLength.current = 0;
                
                // Write all logs for the new session
                if (logs) {
                    xtermRef.current.write(logs);
                    lastLogsLength.current = logs.length;
                }
            }
            lastSessionId.current = activeSessionId;
        }
    }, [activeSessionId, logs]);

    useEffect(() => {
        if (xtermRef.current && logs.length > lastLogsLength.current) {
            const newLogs = logs.substring(lastLogsLength.current);
            xtermRef.current.write(newLogs);
            lastLogsLength.current = logs.length;
        }
    }, [logs]);

    return <div ref={termRef} className="h-full w-full" />;
};

const InteractiveTerminal: React.FC = () => {
    const termRef = useRef<HTMLDivElement>(null);
    const xtermRef = useRef<XTerm | null>(null);
    const socketRef = useRef<WebSocket | null>(null);
    const { activeSessionId } = useAgentStore();
    const { refreshSandbox } = useAgentStream();

    useEffect(() => {
        if (!termRef.current || !activeSessionId) return;

        const term = new XTerm({
            theme: {
                background: '#0f1115',
                foreground: '#f3f4f6',
                cursor: '#38bdf8',
                cursorAccent: '#0f1115'
            },
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontSize: 12,
            cursorBlink: true,
            convertEol: true,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(termRef.current);
        fitAddon.fit();
        xtermRef.current = term;

        term.writeln('\x1b[36mConnecting to sandbox terminal...\x1b[0m');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = '8000';
        const wsUrl = `${protocol}//${host}:${port}/api/agent/sandbox/${activeSessionId}/terminal`;
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
            term.clear();
            term.writeln('\x1b[32mConnected to sandbox terminal!\x1b[0m\r\n');
            const dims = fitAddon.proposeDimensions();
            if (dims) {
                ws.send(JSON.stringify({
                    type: 'resize',
                    cols: dims.cols,
                    rows: dims.rows
                }));
            }
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'output') {
                    term.write(msg.data);
                }
            } catch (e) {
                term.write(event.data);
            }
        };

        ws.onerror = () => {
            term.writeln('\x1b[31mTerminal connection error.\x1b[0m');
        };

        ws.onclose = () => {
            term.writeln('\x1b[31mTerminal connection closed.\x1b[0m');
        };

        const onDataDisposable = term.onData((data) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'input',
                    data: data
                }));

                // Trigger a sandbox refresh 600ms after pressing Enter
                if (data.includes('\r') || data.includes('\n')) {
                    setTimeout(() => {
                        refreshSandbox(activeSessionId);
                    }, 600);
                }
            }
        });

        const resizeObserver = new ResizeObserver(() => {
            try {
                fitAddon.fit();
                const dims = fitAddon.proposeDimensions();
                if (dims && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'resize',
                        cols: dims.cols,
                        rows: dims.rows
                    }));
                }
            } catch (e) {}
        });
        resizeObserver.observe(termRef.current);

        return () => {
            onDataDisposable.dispose();
            resizeObserver.disconnect();
            ws.close();
            term.dispose();
        };
    }, [activeSessionId, refreshSandbox]);

    return <div ref={termRef} className="h-full w-full" />;
};

export const TerminalLog: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'logs' | 'interactive'>('logs');

    return (
        <div className="h-full w-full bg-[#0f1115] flex flex-col relative overflow-hidden">
            {/* Tab Header */}
            <div className="flex items-center justify-between border-b border-[#1e293b] px-4 py-1.5 shrink-0 bg-[#07080a]">
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab('logs')}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold transition-all ${
                            activeTab === 'logs'
                                ? 'bg-[#1e293b] text-brand border border-brand/20'
                                : 'text-gray-400 hover:text-gray-200'
                        }`}
                    >
                        <Activity size={13} />
                        <span>Agent Logs</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('interactive')}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold transition-all ${
                            activeTab === 'interactive'
                                ? 'bg-[#1e293b] text-brand border border-brand/20'
                                : 'text-gray-400 hover:text-gray-200'
                        }`}
                    >
                        <TerminalIcon size={13} />
                        <span>Interactive Terminal</span>
                    </button>
                </div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider">
                    {activeTab === 'logs' ? 'Read-Only' : 'Read-Write (User)'}
                </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 p-2 min-h-0 relative">
                {activeTab === 'logs' ? (
                    <AgentLogsViewer />
                ) : (
                    <InteractiveTerminal />
                )}
            </div>
        </div>
    );
};
