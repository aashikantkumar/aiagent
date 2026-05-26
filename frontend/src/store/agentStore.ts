import { create } from 'zustand';

export interface Message {
    role: 'user' | 'agent' | 'system';
    content: string;
}

export interface AgentEvent {
    id: string;
    type: string;
    node?: string;
    data?: unknown;
    chunk?: string;
    timestamp: string;
}

export interface AgentSession {
    id: string;
    title: string;
    createdAt: string;
    updatedAt: string;
}

export interface SandboxInfo {
    session_id: string;
    container_name: string;
    container_ip: string;
    status: string;
    exposed_ports: { name: string; container_port: number; host_port: number }[];
    created_at: number;
}

export interface TokenUsageInfo {
    messageTokens: number;
    budgetTokens: number;
    usagePercent: number;
    activeModules: string[];
}

export interface ErrorAnalysisInfo {
    category: string;
    severity: string;
    errorType: string;
    message: string;
    file?: string;
    line?: number;
    suggestion?: string;
}

const SESSIONS_KEY = 'myaiagent.sessions';
const ACTIVE_SESSION_KEY = 'myaiagent.activeSessionId';

const createSession = (): AgentSession => {
    const now = new Date().toISOString();
    return {
        id: crypto.randomUUID(),
        title: 'New app',
        createdAt: now,
        updatedAt: now,
    };
};

const loadSessions = () => {
    try {
        const raw = localStorage.getItem(SESSIONS_KEY);
        const parsed = raw ? JSON.parse(raw) as AgentSession[] : [];
        return parsed.length ? parsed : [createSession()];
    } catch {
        return [createSession()];
    }
};

const initialSessions = loadSessions();
const initialActiveSessionId =
    localStorage.getItem(ACTIVE_SESSION_KEY) || initialSessions[0].id;

const persistSessions = (sessions: AgentSession[], activeSessionId: string) => {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
    localStorage.setItem(ACTIVE_SESSION_KEY, activeSessionId);
};

interface AgentStore {
    status: string;
    connectionState: 'idle' | 'connecting' | 'open' | 'closed' | 'error';
    sessions: AgentSession[];
    activeSessionId: string;
    messagesBySession: Record<string, Message[]>;
    eventsBySession: Record<string, AgentEvent[]>;
    pendingBySession: Record<string, string[]>;
    filesBySession: Record<string, Record<string, string>>;
    activeFileBySession: Record<string, string | null>;
    logsBySession: Record<string, string>;
    sandboxBySession: Record<string, SandboxInfo | null>;
    previewUrlBySession: Record<string, string | null>;
    tokenUsageBySession: Record<string, TokenUsageInfo | null>;
    errorAnalysisBySession: Record<string, ErrorAnalysisInfo[]>;
    uploadedDocBySession: Record<string, { filename: string; documentId: string } | null>;
    srsTextBySession: Record<string, string | null>;
    planBySession: Record<string, any | null>;
    error: string | null;

    setStatus: (s: string) => void;
    setConnectionState: (s: AgentStore['connectionState']) => void;
    setError: (error: string | null) => void;
    createNewSession: () => string;
    setActiveSession: (id: string) => void;
    renameActiveSession: (title: string) => void;
    addMessage: (m: Message, sessionId?: string) => void;
    updateLastMessage: (content: string, sessionId?: string) => void;
    addEvent: (event: Omit<AgentEvent, 'id' | 'timestamp'>, sessionId?: string) => void;
    queuePending: (message: string, sessionId?: string) => void;
    popPending: (sessionId?: string) => string | undefined;
    setFile: (path: string, content: string, sessionId?: string) => void;
    replaceFiles: (files: Record<string, string>, sessionId?: string) => void;
    setActiveFile: (path: string | null, sessionId?: string) => void;
    addLog: (log: string, sessionId?: string) => void;
    setSandbox: (sandbox: SandboxInfo | null, sessionId?: string) => void;
    setPreviewUrl: (url: string | null, sessionId?: string) => void;
    setTokenUsage: (usage: TokenUsageInfo, sessionId?: string) => void;
    addErrorAnalysis: (error: ErrorAnalysisInfo, sessionId?: string) => void;
    setUploadedDoc: (doc: { filename: string; documentId: string } | null, sessionId?: string) => void;
    setSrsText: (text: string | null, sessionId?: string) => void;
    consumeSrsText: (sessionId?: string) => string | null;
    setPlan: (plan: any, sessionId?: string) => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
    status: 'idle',
    connectionState: 'idle',
    sessions: initialSessions,
    activeSessionId: initialActiveSessionId,
    messagesBySession: {},
    eventsBySession: {},
    pendingBySession: {},
    filesBySession: {},
    activeFileBySession: {},
    logsBySession: {},
    sandboxBySession: {},
    previewUrlBySession: {},
    tokenUsageBySession: {},
    errorAnalysisBySession: {},
    uploadedDocBySession: {},
    srsTextBySession: {},
    planBySession: {},
    error: null,

    setStatus: (status) => set({ status }),
    setConnectionState: (connectionState) => set({ connectionState }),
    setError: (error) => set({ error }),

    createNewSession: () => {
        const session = createSession();
        set((state) => {
            const sessions = [session, ...state.sessions];
            persistSessions(sessions, session.id);
            return {
                sessions,
                activeSessionId: session.id,
                status: 'idle',
                connectionState: 'idle',
                error: null,
            };
        });
        return session.id;
    },

    setActiveSession: (id) => set((state) => {
        persistSessions(state.sessions, id);
        return {
            activeSessionId: id,
            status: 'idle',
            connectionState: 'idle',
            error: null,
        };
    }),

    renameActiveSession: (title) => set((state) => {
        const sessions = state.sessions.map((session) =>
            session.id === state.activeSessionId
                ? { ...session, title, updatedAt: new Date().toISOString() }
                : session
        );
        persistSessions(sessions, state.activeSessionId);
        return { sessions };
    }),

    addMessage: (m, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const messages = [...(state.messagesBySession[id] || []), m];
        const sessions = state.sessions.map((session) =>
            session.id === id
                ? {
                    ...session,
                    title: session.title === 'New app' && m.role === 'user'
                        ? m.content.slice(0, 42)
                        : session.title,
                    updatedAt: new Date().toISOString(),
                }
                : session
        );
        persistSessions(sessions, state.activeSessionId);
        return {
            sessions,
            messagesBySession: { ...state.messagesBySession, [id]: messages },
        };
    }),

    updateLastMessage: (content, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const msgs = [...(state.messagesBySession[id] || [])];
        if (msgs.length > 0) msgs[msgs.length - 1].content += content;
        return { messagesBySession: { ...state.messagesBySession, [id]: msgs } };
    }),

    addEvent: (event, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const events = [
            ...(state.eventsBySession[id] || []),
            { ...event, id: crypto.randomUUID(), timestamp: new Date().toISOString() },
        ];
        return { eventsBySession: { ...state.eventsBySession, [id]: events } };
    }),

    queuePending: (message, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            pendingBySession: {
                ...state.pendingBySession,
                [id]: [...(state.pendingBySession[id] || []), message],
            },
        };
    }),

    popPending: (sessionId) => {
        const id = sessionId || get().activeSessionId;
        const pending = get().pendingBySession[id] || [];
        const [message, ...rest] = pending;
        set((state) => ({
            pendingBySession: { ...state.pendingBySession, [id]: rest },
        }));
        return message;
    },

    setFile: (path, content, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const currentFiles = state.filesBySession[id] || {};
        const newFiles = { ...currentFiles, [path]: content };
        const currentActiveFile = state.activeFileBySession[id];
        
        return {
            filesBySession: { ...state.filesBySession, [id]: newFiles },
            activeFileBySession: {
                ...state.activeFileBySession,
                [id]: currentActiveFile === null ? path : currentActiveFile,
            },
        };
    }),

    replaceFiles: (files, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const currentActiveFile = state.activeFileBySession[id];
        
        return {
            filesBySession: { ...state.filesBySession, [id]: files },
            activeFileBySession: {
                ...state.activeFileBySession,
                [id]: currentActiveFile && files[currentActiveFile] !== undefined
                    ? currentActiveFile
                    : Object.keys(files)[0] || null,
            },
        };
    }),

    setActiveFile: (activeFile, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            activeFileBySession: { ...state.activeFileBySession, [id]: activeFile },
        };
    }),

    addLog: (log, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const currentLogs = state.logsBySession[id] || '';
        return {
            logsBySession: { ...state.logsBySession, [id]: currentLogs + log + '\n' },
        };
    }),

    setSandbox: (sandbox, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            sandboxBySession: { ...state.sandboxBySession, [id]: sandbox },
        };
    }),

    setPreviewUrl: (previewUrl, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            previewUrlBySession: { ...state.previewUrlBySession, [id]: previewUrl },
        };
    }),

    setTokenUsage: (usage, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            tokenUsageBySession: { ...state.tokenUsageBySession, [id]: usage },
        };
    }),

    addErrorAnalysis: (error, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        const existing = state.errorAnalysisBySession[id] || [];
        return {
            errorAnalysisBySession: {
                ...state.errorAnalysisBySession,
                [id]: [...existing.slice(-19), error],  // Keep last 20
            },
        };
    }),

    setUploadedDoc: (doc, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            uploadedDocBySession: { ...state.uploadedDocBySession, [id]: doc },
        };
    }),

    setSrsText: (text, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            srsTextBySession: { ...state.srsTextBySession, [id]: text },
        };
    }),

    consumeSrsText: (sessionId) => {
        const state = get();
        const id = sessionId || state.activeSessionId;
        const text = state.srsTextBySession[id] || null;
        if (text) {
            set({
                srsTextBySession: { ...state.srsTextBySession, [id]: null },
            });
        }
        return text;
    },

    setPlan: (plan, sessionId) => set((state) => {
        const id = sessionId || state.activeSessionId;
        return {
            planBySession: { ...state.planBySession, [id]: plan },
        };
    }),
}));
