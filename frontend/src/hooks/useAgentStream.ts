import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, getWebSocketUrl } from '../api/backend';
import { queryKeys } from '../api/queryKeys';
import { useAgentStore } from '../store/agentStore';

interface LangGraphEvent {
    type: string;
    node?: string;
    data?: any;
    chunk?: string;
    seq?: number;
    replay?: boolean;
    ts?: number;
}

const extractWrite = (content: string) =>
    content.match(/<write\s+path=['"]([^'"]+)['"]>([\s\S]*?)<\/write>/);

export function useAgentStream() {
    const queryClient = useQueryClient();
    const ws = useRef<WebSocket | null>(null);
    const isReceivingStream = useRef(false);
    const retryCount = useRef(0);
    const reconnectTimer = useRef<number | null>(null);
    const lastSeq = useRef<Record<string, number>>({});

    const refreshSandbox = useCallback(async (sessionId: string) => {
        const store = useAgentStore.getState();
        try {
            const [sandbox, fileList] = await Promise.all([
                api.sandbox.status(sessionId),
                api.sandbox.files(sessionId),
            ]);

            const files: Record<string, string> = {};
            await Promise.all(fileList.files.map(async (path) => {
                if (
                    path.includes('node_modules/') ||
                    path.includes('.git/') ||
                    path.includes('venv/') ||
                    path.includes('.venv/') ||
                    path.includes('.agents/') ||
                    path.includes('.codex/')
                ) {
                    return;
                }
                try {
                    files[path] = (await api.sandbox.readFile(sessionId, path)).content;
                } catch (error) {
                    store.addLog(`> Could not read ${path}: ${error instanceof Error ? error.message : String(error)}`, sessionId);
                }
            }));

            store.setSandbox(sandbox, sessionId);
            store.replaceFiles(files, sessionId);

            for (const port of [3000, 5173, 8000]) {
                try {
                    const health = await api.sandbox.health(sessionId, port);
                    if (health.healthy && health.url) {
                        store.setPreviewUrl(health.url, sessionId);
                        return;
                    }
                } catch {
                    // App preview is optional; keep looking across common ports.
                }
            }

            queryClient.invalidateQueries({ queryKey: queryKeys.sandbox.status(sessionId) });
            queryClient.invalidateQueries({ queryKey: queryKeys.sandbox.files(sessionId) });
        } catch (error) {
            store.addLog(`> Sandbox refresh failed: ${error instanceof Error ? error.message : String(error)}`, sessionId);
        }
    }, [queryClient]);

    const handleAgentContent = useCallback((content: string, sessionId: string) => {
        const store = useAgentStore.getState();
        if (!content.trim()) return;

        store.addMessage({ role: 'agent', content }, sessionId);

        const writeMatch = extractWrite(content);
        if (writeMatch) {
            store.setFile(writeMatch[1], writeMatch[2].trim(), sessionId);
        }
    }, []);

    const handleEvent = useCallback((event: LangGraphEvent, sessionId: string) => {
        if (typeof event.seq === 'number') {
            const currentSeq = lastSeq.current[sessionId] || 0;
            if (event.seq <= currentSeq) return;
            lastSeq.current[sessionId] = event.seq;
        }

        const store = useAgentStore.getState();
        store.addEvent(event, sessionId);

        if (event.type === 'on_chat_model_stream') {
            if (!event.chunk) return;
            if (!isReceivingStream.current) {
                isReceivingStream.current = true;
                store.addMessage({ role: 'agent', content: event.chunk }, sessionId);
            } else {
                store.updateLastMessage(event.chunk, sessionId);
            }
            return;
        }

        if (event.type === 'error') {
            const errorMsg = event.data?.message || event.chunk || (event as any).message || (event as any).error || 'An unknown error occurred';
            store.addLog(`> ❌ Error: ${errorMsg}`, sessionId);
            store.addMessage({ role: 'agent', content: `❌ **Error**: ${errorMsg}` }, sessionId);
            store.setStatus('error');
            return;
        }

        if (event.type === 'on_chain_end') {
            isReceivingStream.current = false;

            const output = event.data?.output;
            const content = output?.content;
            if (typeof content === 'string' && ['plan', 'implement', 'RunnableSequence'].includes(event.node || '')) {
                handleAgentContent(content, sessionId);
            }

            // Extract plan from plan node output
            if (event.node === 'plan' && output?.plan) {
                try {
                    const parsedPlan = typeof output.plan === 'string' ? JSON.parse(output.plan) : output.plan;
                    store.setPlan(parsedPlan, sessionId);
                } catch (e) {
                    console.warn("Failed to parse plan JSON", e);
                }
            }

            const observation = output?.last_obs;
            if (observation) {
                store.addLog(`> ${observation.output || JSON.stringify(observation)}`, sessionId);
                void refreshSandbox(sessionId);
            }

            if (output?.status) {
                store.setStatus(output.status);
            }

            // Extract token usage from implement node output
            if (typeof output?.token_count === 'number') {
                const budgetTokens = output?.context_budget?.conversation || 4096;
                const activeModules: string[] = [];
                if (output?.token_count > 0) activeModules.push('ctx');
                if (output?.last_error_analysis) activeModules.push('err');
                if (output?.workspace_summary) activeModules.push('ws');
                store.setTokenUsage({
                    messageTokens: output.token_count,
                    budgetTokens,
                    usagePercent: Math.round((output.token_count / budgetTokens) * 100),
                    activeModules,
                }, sessionId);
            }

            // Extract error analysis
            if (output?.error_history && Array.isArray(output.error_history)) {
                const latest = output.error_history[output.error_history.length - 1];
                if (latest) {
                    store.addErrorAnalysis({
                        category: latest.category || 'unknown',
                        severity: latest.severity || 'medium',
                        errorType: latest.error_type || 'Error',
                        message: latest.message || '',
                        file: latest.file,
                        line: latest.line,
                        suggestion: latest.suggestion,
                    }, sessionId);
                }
            }
        }

        if (event.type === 'on_tool_end' && event.node === 'execute') {
            const obs = event.data?.output;
            if (obs) {
                store.addLog(`> [${new Date().toLocaleTimeString()}] ${JSON.stringify(obs)}`, sessionId);
                void refreshSandbox(sessionId);
            }
        }

        if (event.node) {
            store.setStatus(`running: ${event.node}`);
        }
    }, [handleAgentContent, refreshSandbox]);

    const openAndSend = useCallback((message: string, sessionId: string) => {
        const store = useAgentStore.getState();

        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.close(1000);
        }

        if (reconnectTimer.current) {
            window.clearTimeout(reconnectTimer.current);
            reconnectTimer.current = null;
        }

        store.setConnectionState('connecting');
        store.setStatus('connecting');
        store.setError(null);

        ws.current = new WebSocket(getWebSocketUrl());

        ws.current.onopen = () => {
            retryCount.current = 0;
            store.setConnectionState('open');
            store.setStatus('planning');
            const lastSeqForSession = lastSeq.current[sessionId] || 0;
            ws.current?.send(JSON.stringify({
                session_id: sessionId,
                message,
                last_seq: lastSeqForSession,
            }));
        };

        ws.current.onmessage = (e) => {
            try {
                const event = JSON.parse(e.data) as LangGraphEvent;
                if (event.type === 'ping') {
                    ws.current?.send(JSON.stringify({
                        type: 'pong',
                        ts: event.ts,
                        last_seq: lastSeq.current[sessionId] || 0,
                    }));
                    return;
                }
                handleEvent(event, sessionId);
            } catch (error) {
                store.setError('Failed to parse backend event');
                store.addLog(`> Event parse error: ${error instanceof Error ? error.message : String(error)}`);
            }
        };

        ws.current.onerror = () => {
            store.setConnectionState('error');
            store.setStatus('error');
            store.setError('WebSocket error. Backend may be offline.');
        };

        ws.current.onclose = (event) => {
            store.setConnectionState(event.code === 1000 ? 'closed' : 'error');

            if (event.code !== 1000) {
                retryCount.current += 1;
                const delay = Math.min(1000 * (2 ** (retryCount.current - 1)), 30000);
                store.addLog(`> WebSocket closed unexpectedly. Reconnecting in ${Math.round(delay / 1000)}s...`, sessionId);
                reconnectTimer.current = window.setTimeout(() => openAndSend(message, sessionId), delay);
                if (retryCount.current > 6) {
                    store.queuePending(message, sessionId);
                    store.setError('Message queued. Reconnect or send again when backend is ready.');
                }
                return;
            }

            if (store.status !== 'error') {
                store.setStatus('idle');
            }
        };
    }, [handleEvent]);

    const send = useCallback((message: string) => {
        const store = useAgentStore.getState();
        const sessionId = store.activeSessionId;
        store.addMessage({ role: 'user', content: message }, sessionId);
        openAndSend(message, sessionId);
    }, [openAndSend]);

    const retryPending = useCallback(() => {
        const store = useAgentStore.getState();
        const sessionId = store.activeSessionId;
        const message = store.popPending(sessionId);
        if (message) openAndSend(message, sessionId);
    }, [openAndSend]);

    const stop = useCallback(() => {
        const store = useAgentStore.getState();
        if (ws.current) {
            ws.current.close(1000);
        }
        if (reconnectTimer.current) {
            window.clearTimeout(reconnectTimer.current);
            reconnectTimer.current = null;
        }
        store.setStatus('idle');
        store.setConnectionState('closed');
        store.addLog(`> Generation stopped by user.`, store.activeSessionId);
    }, []);

    return { send, retryPending, refreshSandbox, stop };
}
