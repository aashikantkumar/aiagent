import { useEffect, useState } from 'react';
import { useAgentStore } from './store/agentStore';
import { useAgentStream } from './hooks/useAgentStream';
import { Chat } from './components/Chat';
import { CodeEditor } from './components/MonacoEditor';
import { TerminalLog } from './components/Terminal';
import { FileBrowser } from './components/FileBrowser';
import { SessionSidebar } from './components/SessionSidebar';
import { SandboxPanel } from './components/SandboxPanel';
import { BrowserPreview } from './components/BrowserPreview';
import { EventLog } from './components/EventLog';
import { TokenUsage } from './components/TokenUsage';
import { SettingsModal } from './components/SettingsModal';
import { ObservabilityDashboard } from './components/ObservabilityDashboard';
import { ArchitectureView } from './components/ArchitectureView';
import { Code2, Settings, Terminal, BarChart2, LayoutGrid } from 'lucide-react';

function App() {
  const { activeSessionId, fetchSessions, fetchArchitecturalPlan } = useAgentStore();
  const { refreshSandbox } = useAgentStream();
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState<'editor' | 'architecture' | 'observability'>('editor');

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    if (activeSessionId) {
      refreshSandbox(activeSessionId);
      fetchArchitecturalPlan(activeSessionId);
    }
  }, [activeSessionId, refreshSandbox, fetchArchitecturalPlan]);

  return (
    <div className="h-screen w-screen bg-background flex flex-col overflow-hidden font-sans">
      <header className="h-12 border-b border-border bg-surface flex items-center px-4 shrink-0 justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-brand font-semibold tracking-wide">
            <Code2 size={20} />
            <span>Antigravity Agent Builder</span>
          </div>
          
          {/* Tab Switcher */}
          <div className="flex items-center bg-[#181920] border border-slate-800 rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setActiveTab('editor')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'editor'
                  ? 'bg-brand text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal size={13} />
              IDE Workspace
            </button>
            <button
              onClick={() => setActiveTab('architecture')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'architecture'
                  ? 'bg-brand text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <LayoutGrid size={13} />
              System Architecture
            </button>
            <button
              onClick={() => setActiveTab('observability')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'observability'
                  ? 'bg-brand text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart2 size={13} />
              AI Observability
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <TokenUsage />
          <button
            onClick={() => setShowSettings(true)}
            className="p-1.5 rounded-md border border-border bg-surface text-text-muted hover:border-brand hover:text-brand transition-all hover:shadow-[0_0_8px_var(--color-brand-muted)]"
            title="Open Settings"
          >
            <Settings size={16} />
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden p-2 gap-2">
        <div className="flex flex-col rounded-xl overflow-hidden border border-border bg-surface shadow-lg">
          <SessionSidebar />
        </div>

        {/* Left pane: Chat */}
        <div className="w-[380px] flex-shrink-0 flex flex-col rounded-xl overflow-hidden border border-border bg-surface shadow-lg relative">
          <Chat />
        </div>
        
        {/* Middle pane: IDE Workspace or Observability Dashboard */}
        <div className="flex-1 flex flex-col rounded-xl overflow-hidden border border-border bg-[#1e1e1e] shadow-lg relative">
          {activeTab === 'editor' ? (
            <>
              <SandboxPanel />
              <div className="flex-1 flex overflow-hidden relative">
                <div className="w-[200px] flex-shrink-0 border-r border-border bg-surface">
                   <FileBrowser />
                </div>
                <div className="flex-1 h-full bg-[#1e1e1e]">
                  <CodeEditor />
                </div>
                <div className="w-[360px] flex-shrink-0 border-l border-border bg-surface">
                  <BrowserPreview />
                </div>
                <div className="w-[260px] flex-shrink-0 border-l border-border bg-surface">
                  <EventLog />
                </div>
              </div>
              
              {/* Bottom pane: Terminal logs */}
              <div className="h-[250px] flex-shrink-0 border-t border-border bg-surface">
                <TerminalLog />
              </div>
            </>
          ) : activeTab === 'architecture' ? (
            <ArchitectureView />
          ) : (
            <ObservabilityDashboard />
          )}
        </div>
      </div>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}

export default App;
