import React from 'react';
import { AlertTriangle, Bug, FileWarning, Package, ShieldAlert, Clock, Wifi, FolderSearch, Wrench } from 'lucide-react';
import { useAgentStore } from '../store/agentStore';

export interface ErrorAnalysisData {
    category: string;
    severity: string;
    errorType: string;
    message: string;
    file?: string;
    line?: number;
    suggestion?: string;
}

const CATEGORY_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
    syntax: { icon: Bug, color: 'text-red-400', label: 'Syntax' },
    type: { icon: Bug, color: 'text-orange-400', label: 'Type' },
    import: { icon: Package, color: 'text-yellow-400', label: 'Import' },
    dependency: { icon: Package, color: 'text-amber-400', label: 'Dependency' },
    runtime: { icon: AlertTriangle, color: 'text-red-400', label: 'Runtime' },
    file_not_found: { icon: FolderSearch, color: 'text-yellow-400', label: 'File Not Found' },
    permission: { icon: ShieldAlert, color: 'text-red-500', label: 'Permission' },
    timeout: { icon: Clock, color: 'text-gray-400', label: 'Timeout' },
    network: { icon: Wifi, color: 'text-gray-400', label: 'Network' },
    port_in_use: { icon: Wifi, color: 'text-yellow-400', label: 'Port In Use' },
    build: { icon: Wrench, color: 'text-orange-400', label: 'Build' },
    test: { icon: FileWarning, color: 'text-yellow-400', label: 'Test' },
    unknown: { icon: AlertTriangle, color: 'text-gray-400', label: 'Unknown' },
};

const SEVERITY_STYLES: Record<string, string> = {
    low: 'border-gray-700 bg-gray-900/30 text-gray-400',
    medium: 'border-yellow-800 bg-yellow-950/30 text-yellow-300',
    high: 'border-orange-800 bg-orange-950/30 text-orange-300',
    fatal: 'border-red-800 bg-red-950/30 text-red-300',
};

export const ErrorAnalysisPanel: React.FC = () => {
    const { errorAnalysisBySession, activeSessionId } = useAgentStore();
    const errors = errorAnalysisBySession[activeSessionId] || [];

    if (errors.length === 0) return null;

    const latestError = errors[errors.length - 1];
    const config = CATEGORY_CONFIG[latestError.category] || CATEGORY_CONFIG.unknown;
    const Icon = config.icon;
    const severityStyle = SEVERITY_STYLES[latestError.severity] || SEVERITY_STYLES.medium;

    return (
        <div className={`border rounded-lg p-3 text-xs ${severityStyle} transition-all animate-in fade-in`}>
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className={config.color} />
                <span className={`font-semibold ${config.color}`}>
                    {config.label} Error
                </span>
                <span className={`ml-auto px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider ${
                    latestError.severity === 'fatal' ? 'bg-red-900/50 text-red-300' :
                    latestError.severity === 'high' ? 'bg-orange-900/50 text-orange-300' :
                    latestError.severity === 'medium' ? 'bg-yellow-900/50 text-yellow-300' :
                    'bg-gray-800 text-gray-400'
                }`}>
                    {latestError.severity}
                </span>
            </div>

            {/* Error details */}
            <div className="space-y-1.5">
                <div className="font-mono text-[11px] opacity-90">
                    {latestError.errorType}: {latestError.message}
                </div>

                {latestError.file && (
                    <div className="flex items-center gap-1 text-text-muted">
                        <FileWarning size={10} />
                        <span className="font-mono">
                            {latestError.file}
                            {latestError.line ? `:${latestError.line}` : ''}
                        </span>
                    </div>
                )}

                {latestError.suggestion && (
                    <div className="mt-2 p-2 rounded bg-black/20 border border-white/5">
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">
                            💡 Suggested Fix
                        </div>
                        <div className="text-[11px] text-text whitespace-pre-wrap leading-relaxed">
                            {latestError.suggestion}
                        </div>
                    </div>
                )}
            </div>

            {/* Error count */}
            {errors.length > 1 && (
                <div className="mt-2 text-[10px] text-text-muted border-t border-white/5 pt-2">
                    {errors.length} errors analyzed this session
                </div>
            )}
        </div>
    );
};
