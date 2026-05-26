import React, { useState, useRef, useEffect } from 'react';
import { useAgentStore } from '../store/agentStore';
import { Send, Terminal, Loader2, Square } from 'lucide-react';
import { useAgentStream } from '../hooks/useAgentStream';
import { FileUpload } from './FileUpload';
import { ErrorAnalysisPanel } from './ErrorAnalysisPanel';
import { PlanTracker } from './PlanTracker';

export const Chat: React.FC = () => {
    const {
        activeSessionId,
        messagesBySession,
        pendingBySession,
        status,
        connectionState,
        error,
    } = useAgentStore();
    const { send, stop } = useAgentStream();
    const [input, setInput] = useState('');
    const endRef = useRef<HTMLDivElement>(null);
    const messages = messagesBySession[activeSessionId] || [];
    const pending = pendingBySession[activeSessionId] || [];

    const isRunning = connectionState === 'open' && status !== 'idle' && status !== 'error';

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            // If there's an uploaded SRS document, prepend its text to the message
            const srsText = useAgentStore.getState().consumeSrsText(activeSessionId);
            const fullMessage = srsText
                ? `[SRS DOCUMENT]\n${srsText}\n\n[USER INSTRUCTION]\n${input.trim()}`
                : input.trim();
            send(fullMessage);
            setInput('');
        }
    };

    return (
        <div className="flex flex-col h-full bg-surface">
            <div className="p-4 border-b border-border bg-surface-hover flex items-center gap-2">
                <Terminal size={18} className="text-brand" />
                <h2 className="font-semibold text-text text-sm tracking-wide">AGENT CONSOLE</h2>
                <div className="ml-auto flex items-center gap-2 text-xs">
                    {pending.length > 0 && <span className="text-yellow-400">{pending.length} queued</span>}
                    <span className="text-text-muted">Status:</span>
                    <span className={`px-2 py-0.5 rounded-full capitalize ${
                        status === 'idle' || connectionState === 'closed' ? 'bg-gray-800 text-gray-400' :
                        connectionState === 'open' ? 'bg-green-900/50 text-green-400 border border-green-800' :
                        connectionState === 'error' || status === 'error' ? 'bg-red-900/50 text-red-300 border border-red-800' :
                        'bg-brand-muted text-brand border border-brand/30 flex items-center gap-1'
                    }`}>
                        {(status.startsWith('running') || status === 'planning' || status === 'connecting') && <Loader2 size={10} className="animate-spin" />}
                        {connectionState === 'open' ? status : connectionState}
                    </span>
                </div>
            </div>
            
            <PlanTracker />

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {error && (
                    <div className="text-xs border border-red-800 bg-red-950/40 text-red-200 rounded p-2">
                        {error}
                    </div>
                )}
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-text-muted opacity-50">
                        <Terminal size={48} className="mb-4 text-brand" />
                        <p>Provide an SRS or idea to start generating.</p>
                    </div>
                )}
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-lg p-3 text-sm shadow-md ${
                            msg.role === 'user' 
                                ? 'bg-brand text-white rounded-br-none' 
                                : 'bg-surface-hover border border-border text-text rounded-bl-none'
                        }`}>
                            {msg.role === 'agent' ? (
                                <pre className="whitespace-pre-wrap font-sans">
                                    {/* Naively render think tags as dimmed */}
                                    {msg.content.split(/(<think>[\s\S]*?<\/think>)/g).map((part, idx) => {
                                        if (part.startsWith('<think>')) {
                                            return <div key={idx} className="text-gray-500 italic text-xs my-2 pl-2 border-l-2 border-gray-700 bg-black/20 p-2 rounded">{part.replace(/<\/?think>/g, '')}</div>;
                                        }
                                        // Colorize other tags if needed, or just render text
                                        return <span key={idx}>{part}</span>;
                                    })}
                                </pre>
                            ) : (
                                <span>{msg.content}</span>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={endRef} />
            </div>

            <form onSubmit={handleSubmit} className="p-3 border-t border-border bg-[#1a1b22] space-y-2">
                <FileUpload />
                <ErrorAnalysisPanel />
                <div className="relative flex items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Describe your app..."
                        className="w-full bg-surface border border-border rounded-lg pl-4 pr-12 py-3 text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand text-text transition-all"
                    />
                    {isRunning ? (
                        <button 
                            type="button" 
                            onClick={stop}
                            title="Stop Generation"
                            className="absolute right-2 p-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors"
                        >
                            <Square size={16} />
                        </button>
                    ) : (
                        <button 
                            type="submit" 
                            disabled={!input.trim() || connectionState === 'connecting'}
                            className="absolute right-2 p-2 bg-brand hover:bg-brand-hover text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Send size={16} />
                        </button>
                    )}
                </div>
            </form>
        </div>
    );
};
