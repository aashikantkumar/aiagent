import React, { useEffect, useState } from 'react';
import { api } from '../api/backend';
import type { LLMProfile, LLMProfileCreate } from '../api/backend';
import { Settings, Sliders, Cpu, Trash2, CheckCircle2, Circle, Plus, X, Loader2 } from 'lucide-react';

interface SettingsModalProps {
    onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ onClose }) => {
    const [activeTab, setActiveTab] = useState<'profiles' | 'general'>('profiles');
    const [profiles, setProfiles] = useState<LLMProfile[]>([]);
    const [generalSettings, setGeneralSettings] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    // Form state for creating a new profile
    const [showAddForm, setShowAddForm] = useState(false);
    const [newProvider, setNewProvider] = useState('gemini');
    const [newModel, setNewModel] = useState('gemini/gemini-2.5-flash');
    const [newTemp, setNewTemp] = useState(0.2);
    const [newMaxTokens, setNewMaxTokens] = useState<number | ''>('');
    const [newIsDefault, setNewIsDefault] = useState(false);

    const loadData = async () => {
        setLoading(true);
        try {
            const [profilesRes, settingsRes] = await Promise.all([
                api.settings.profiles.list(),
                api.settings.getAll(),
            ]);
            setProfiles(profilesRes.profiles);
            setGeneralSettings(settingsRes.settings);
        } catch (error) {
            console.error('Failed to load settings data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleCreateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        setActionLoading('create');
        try {
            const payload: LLMProfileCreate = {
                provider: newProvider,
                model: newModel,
                temperature: newTemp,
                max_tokens: newMaxTokens === '' ? null : newMaxTokens,
                is_default: newIsDefault,
            };
            await api.settings.profiles.create(payload);
            setShowAddForm(false);
            // Reset form
            setNewTemp(0.2);
            setNewMaxTokens('');
            setNewIsDefault(false);
            await loadData();
        } catch (error) {
            console.error('Failed to create profile:', error);
            alert('Failed to create LLM profile. Please check the inputs.');
        } finally {
            setActionLoading(null);
        }
    };

    const handleDeleteProfile = async (id: string) => {
        if (!confirm('Are you sure you want to delete this profile?')) return;
        setActionLoading(`delete-${id}`);
        try {
            await api.settings.profiles.delete(id);
            await loadData();
        } catch (error) {
            console.error('Failed to delete profile:', error);
        } finally {
            setActionLoading(null);
        }
    };

    const handleSetDefaultProfile = async (id: string) => {
        setActionLoading(`default-${id}`);
        try {
            await api.settings.profiles.setDefault(id);
            await loadData();
        } catch (error) {
            console.error('Failed to set default profile:', error);
        } finally {
            setActionLoading(null);
        }
    };

    const handleUpdateSetting = async (key: string, value: any) => {
        setActionLoading(key);
        try {
            await api.settings.update(key, value);
            setGeneralSettings(prev => ({ ...prev, [key]: value }));
        } catch (error) {
            console.error(`Failed to update setting ${key}:`, error);
        } finally {
            setActionLoading(null);
        }
    };

    // Auto-select models based on provider selection to assist the user
    useEffect(() => {
        if (newProvider === 'gemini') {
            setNewModel('gemini/gemini-2.5-flash');
        } else if (newProvider === 'groq') {
            setNewModel('groq/llama-3.3-70b-versatile');
        } else if (newProvider === 'ollama') {
            setNewModel('ollama/qwen2.5-coder:7b');
        } else if (newProvider === 'openai') {
            setNewModel('openai/gpt-4o-mini');
        }
    }, [newProvider]);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-2xl rounded-xl border border-border shadow-2xl flex flex-col max-h-[85vh]">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border bg-surface-hover rounded-t-xl">
                    <div className="flex items-center gap-2 text-text font-medium">
                        <Settings size={18} className="text-brand" />
                        <h2>Application Settings</h2>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-1.5 hover:bg-red-900/50 text-text-muted hover:text-red-400 rounded transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-border bg-surface shrink-0">
                    <button
                        onClick={() => setActiveTab('profiles')}
                        className={`flex-1 py-3 px-4 flex items-center justify-center gap-2 border-b-2 text-sm font-medium transition-all ${
                            activeTab === 'profiles'
                                ? 'border-brand text-brand bg-brand-muted/10'
                                : 'border-transparent text-text-muted hover:text-text hover:bg-surface-hover'
                        }`}
                    >
                        <Cpu size={16} />
                        <span>LLM Profiles</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('general')}
                        className={`flex-1 py-3 px-4 flex items-center justify-center gap-2 border-b-2 text-sm font-medium transition-all ${
                            activeTab === 'general'
                                ? 'border-brand text-brand bg-brand-muted/10'
                                : 'border-transparent text-text-muted hover:text-text hover:bg-surface-hover'
                        }`}
                    >
                        <Sliders size={16} />
                        <span>General Config</span>
                    </button>
                </div>

                {/* Content */}
                <div className="p-4 overflow-y-auto flex-1 min-h-[300px]">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-48 text-text-muted">
                            <Loader2 size={24} className="animate-spin mb-2 text-brand" />
                            <p className="text-sm">Loading settings...</p>
                        </div>
                    ) : activeTab === 'profiles' ? (
                        <div className="space-y-4">
                            {/* Actions Header */}
                            <div className="flex justify-between items-center">
                                <h3 className="text-sm font-semibold text-text">Configured LLM Profiles</h3>
                                {!showAddForm && (
                                    <button
                                        onClick={() => setShowAddForm(true)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-brand hover:bg-brand-hover text-white text-xs font-semibold rounded-md shadow-md transition-all"
                                    >
                                        <Plus size={14} />
                                        Add Profile
                                    </button>
                                )}
                            </div>

                            {/* Add Form */}
                            {showAddForm && (
                                <form onSubmit={handleCreateProfile} className="p-4 border border-brand bg-brand-muted/5 rounded-lg space-y-3">
                                    <div className="flex justify-between items-center border-b border-border pb-1.5">
                                        <span className="text-xs font-semibold text-brand">Create New LLM Profile</span>
                                        <button 
                                            type="button" 
                                            onClick={() => setShowAddForm(false)}
                                            className="text-text-muted hover:text-text"
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 text-xs">
                                        <div className="space-y-1">
                                            <label className="text-text-muted block">Provider</label>
                                            <select
                                                value={newProvider}
                                                onChange={e => setNewProvider(e.target.value)}
                                                className="w-full bg-surface-hover border border-border rounded px-2.5 py-1.5 text-text focus:border-brand outline-none"
                                            >
                                                <option value="gemini">Gemini</option>
                                                <option value="groq">Groq</option>
                                                <option value="ollama">Ollama (Local)</option>
                                                <option value="openai">OpenAI</option>
                                            </select>
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-text-muted block">Model Identifier</label>
                                            <input
                                                type="text"
                                                required
                                                value={newModel}
                                                onChange={e => setNewModel(e.target.value)}
                                                placeholder="e.g. gemini/gemini-2.5-flash"
                                                className="w-full bg-surface-hover border border-border rounded px-2.5 py-1.5 text-text focus:border-brand outline-none"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-text-muted block">Temperature ({newTemp})</label>
                                            <input
                                                type="range"
                                                min="0"
                                                max="1"
                                                step="0.1"
                                                value={newTemp}
                                                onChange={e => setNewTemp(parseFloat(e.target.value))}
                                                className="w-full h-1.5 bg-surface-hover rounded-lg appearance-none cursor-pointer accent-brand"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-text-muted block">Max Tokens (Optional)</label>
                                            <input
                                                type="number"
                                                value={newMaxTokens}
                                                onChange={e => setNewMaxTokens(e.target.value === '' ? '' : parseInt(e.target.value))}
                                                placeholder="Unlimited"
                                                className="w-full bg-surface-hover border border-border rounded px-2.5 py-1.5 text-text focus:border-brand outline-none"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between pt-2">
                                        <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={newIsDefault}
                                                onChange={e => setNewIsDefault(e.target.checked)}
                                                className="rounded border-border text-brand focus:ring-brand bg-surface-hover"
                                            />
                                            Set as default profile
                                        </label>
                                        <div className="flex gap-2">
                                            <button
                                                type="button"
                                                onClick={() => setShowAddForm(false)}
                                                className="px-3 py-1.5 border border-border hover:bg-surface-hover rounded text-xs font-semibold"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="submit"
                                                disabled={actionLoading === 'create'}
                                                className="px-4 py-1.5 bg-brand hover:bg-brand-hover disabled:bg-brand/50 text-white rounded text-xs font-semibold flex items-center gap-1"
                                            >
                                                {actionLoading === 'create' && <Loader2 size={12} className="animate-spin" />}
                                                Save Profile
                                            </button>
                                        </div>
                                    </div>
                                </form>
                            )}

                            {/* Profiles List */}
                            <div className="space-y-2">
                                {profiles.length === 0 ? (
                                    <p className="text-xs text-text-muted text-center py-8">No custom LLM profiles found. Falling back to backend defaults (.env).</p>
                                ) : (
                                    profiles.map(p => (
                                        <div 
                                            key={p.id} 
                                            className={`p-3 rounded-lg border flex items-center justify-between transition-all ${
                                                p.is_default 
                                                    ? 'border-brand/60 bg-brand-muted/5' 
                                                    : 'border-border bg-surface-hover/30 hover:bg-surface-hover/60'
                                            }`}
                                        >
                                            <div className="space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold text-xs text-text uppercase tracking-wider bg-zinc-800 px-2 py-0.5 rounded border border-zinc-700">
                                                        {p.provider}
                                                    </span>
                                                    <span className="font-mono text-xs text-text font-bold">
                                                        {p.model}
                                                    </span>
                                                    {p.is_default && (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand/20 text-brand border border-brand/30 font-semibold uppercase">
                                                            Default
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-[11px] text-text-muted flex gap-4">
                                                    <span>Temp: <strong className="text-gray-300">{p.temperature}</strong></span>
                                                    {p.max_tokens && <span>Max Tokens: <strong className="text-gray-300">{p.max_tokens}</strong></span>}
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                {p.is_default ? (
                                                    <span className="text-brand p-1.5" title="Active default model">
                                                        <CheckCircle2 size={16} />
                                                    </span>
                                                ) : (
                                                    <button
                                                        onClick={() => handleSetDefaultProfile(p.id)}
                                                        disabled={actionLoading !== null}
                                                        className="p-1.5 hover:bg-surface text-text-muted hover:text-text rounded transition-colors"
                                                        title="Set as default model"
                                                    >
                                                        {actionLoading === `default-${p.id}` ? (
                                                            <Loader2 size={16} className="animate-spin text-brand" />
                                                        ) : (
                                                            <Circle size={16} />
                                                        )}
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDeleteProfile(p.id)}
                                                    disabled={actionLoading !== null}
                                                    className="p-1.5 hover:bg-red-950/40 text-text-muted hover:text-red-400 rounded transition-colors"
                                                    title="Delete profile"
                                                >
                                                    {actionLoading === `delete-${p.id}` ? (
                                                        <Loader2 size={16} className="animate-spin text-red-400" />
                                                    ) : (
                                                        <Trash2 size={16} />
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <h3 className="text-sm font-semibold text-text">General Sandbox & Agent Configurations</h3>
                            
                            <div className="space-y-4">
                                {/* Sandbox Timeout */}
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 border border-border bg-surface-hover/20 rounded-lg gap-2">
                                    <div className="space-y-0.5">
                                        <h4 className="text-xs font-semibold text-text">Sandbox Timeout</h4>
                                        <p className="text-[11px] text-text-muted">Maximum execution time for running commands inside the sandbox (seconds).</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="number"
                                            value={generalSettings.sandbox_timeout || 30}
                                            onChange={e => handleUpdateSetting('sandbox_timeout', parseInt(e.target.value))}
                                            className="w-20 bg-surface border border-border rounded px-2 py-1 text-xs text-text text-center focus:border-brand outline-none font-semibold"
                                        />
                                        {actionLoading === 'sandbox_timeout' && <Loader2 size={14} className="animate-spin text-brand animate-duration-1000" />}
                                    </div>
                                </div>

                                {/* Max Retries */}
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 border border-border bg-surface-hover/20 rounded-lg gap-2">
                                    <div className="space-y-0.5">
                                        <h4 className="text-xs font-semibold text-text">Max LLM Iterations</h4>
                                        <p className="text-[11px] text-text-muted">Maximum repair iterations before the agent considers a file build cycle failed.</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="number"
                                            value={generalSettings.max_retries || 5}
                                            onChange={e => handleUpdateSetting('max_retries', parseInt(e.target.value))}
                                            className="w-20 bg-surface border border-border rounded px-2 py-1 text-xs text-text text-center focus:border-brand outline-none font-semibold"
                                        />
                                        {actionLoading === 'max_retries' && <Loader2 size={14} className="animate-spin text-brand" />}
                                    </div>
                                </div>

                                {/* Debug Mode */}
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 border border-border bg-surface-hover/20 rounded-lg gap-2">
                                    <div className="space-y-0.5">
                                        <h4 className="text-xs font-semibold text-text">Debug Log Mode</h4>
                                        <p className="text-[11px] text-text-muted">Enables verbose tracing of system internals in logs and files.</p>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <button
                                            onClick={() => handleUpdateSetting('debug_mode', !generalSettings.debug_mode)}
                                            disabled={actionLoading === 'debug_mode'}
                                            className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                                                generalSettings.debug_mode ? 'bg-brand' : 'bg-zinc-700'
                                            }`}
                                        >
                                            <span
                                                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                                    generalSettings.debug_mode ? 'translate-x-5' : 'translate-x-0'
                                                }`}
                                            />
                                        </button>
                                        {actionLoading === 'debug_mode' && <Loader2 size={14} className="animate-spin text-brand" />}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-3 border-t border-border bg-surface-hover text-xs text-text-muted flex items-center justify-between">
                    <span>LLM profiles manage keys and models used for planner, coder, and validation roles.</span>
                    <button
                        onClick={async () => {
                            if (confirm('Are you sure you want to reset all settings to defaults?')) {
                                setActionLoading('reset');
                                try {
                                    await api.settings.reset();
                                    await loadData();
                                } catch (error) {
                                    console.error(error);
                                } finally {
                                    setActionLoading(null);
                                }
                            }
                        }}
                        className="text-red-400 hover:text-red-300 font-semibold transition-colors flex items-center gap-1"
                    >
                        {actionLoading === 'reset' && <Loader2 size={12} className="animate-spin" />}
                        Reset Settings
                    </button>
                </div>
            </div>
        </div>
    );
};
