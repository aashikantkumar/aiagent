import React, { useState, useCallback } from 'react';
import { Upload, FileText, X, CheckCircle, Loader2 } from 'lucide-react';
import { api } from '../api/backend';
import { useAgentStore } from '../store/agentStore';

interface UploadResult {
    filename: string;
    document_id: string;
    text_length: number;
    text_preview: string;
    full_text: string;
    chunks_indexed: number;
    rag_enabled: boolean;
}

export const FileUpload: React.FC = () => {
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<UploadResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const { addMessage, setSrsText, activeSessionId } = useAgentStore();

    const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.md', '.txt'];

    const handleFile = useCallback(async (file: File) => {
        const ext = '.' + file.name.split('.').pop()?.toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            setError(`Unsupported file type: ${ext}. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
            return;
        }

        setUploading(true);
        setError(null);
        setResult(null);

        try {
            const uploadResult = await api.documents.upload(file);
            setResult(uploadResult);

            // Store the full extracted text so the agent can use it
            setSrsText(uploadResult.full_text, activeSessionId);

            // Inject the document text as a user message for the agent
            addMessage({
                role: 'system',
                content: `📄 Document uploaded: **${uploadResult.filename}**\n` +
                    `• ${uploadResult.text_length.toLocaleString()} characters extracted\n` +
                    (uploadResult.rag_enabled
                        ? `• ${uploadResult.chunks_indexed} chunks indexed for semantic search\n`
                        : '• RAG indexing not available\n') +
                    `\nPreview:\n${uploadResult.text_preview}`,
            }, activeSessionId);
        } catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg);
        } finally {
            setUploading(false);
        }
    }, [addMessage, setSrsText, activeSessionId]);

    const onDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }, [handleFile]);

    const onDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const onDragLeave = useCallback(() => setIsDragging(false), []);

    const onFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
        e.target.value = '';
    }, [handleFile]);

    return (
        <div className="relative">
            {/* Drag overlay */}
            {isDragging && (
                <div
                    className="absolute inset-0 z-50 bg-brand/10 border-2 border-dashed border-brand rounded-lg flex items-center justify-center backdrop-blur-sm"
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                >
                    <div className="text-center">
                        <Upload size={32} className="mx-auto text-brand mb-2" />
                        <p className="text-sm text-brand font-medium">Drop SRS document here</p>
                        <p className="text-xs text-text-muted mt-1">PDF, DOCX, MD, TXT</p>
                    </div>
                </div>
            )}

            {/* Upload area */}
            <div
                className={`border border-dashed rounded-lg p-3 transition-all cursor-pointer ${
                    isDragging
                        ? 'border-brand bg-brand/5'
                        : 'border-border hover:border-brand/50 bg-surface-hover/50'
                }`}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
            >
                <label className="flex items-center gap-3 cursor-pointer">
                    <div className="w-8 h-8 rounded-md bg-brand/10 flex items-center justify-center flex-shrink-0">
                        {uploading ? (
                            <Loader2 size={16} className="text-brand animate-spin" />
                        ) : result ? (
                            <CheckCircle size={16} className="text-green-400" />
                        ) : (
                            <Upload size={16} className="text-brand" />
                        )}
                    </div>
                    <div className="flex-1 min-w-0">
                        {uploading ? (
                            <p className="text-xs text-text-muted">Processing document...</p>
                        ) : result ? (
                            <div className="flex items-center gap-2">
                                <FileText size={12} className="text-green-400 flex-shrink-0" />
                                <span className="text-xs text-green-400 truncate">{result.filename}</span>
                                <span className="text-[10px] text-text-muted">
                                    {result.chunks_indexed} chunks
                                </span>
                                <button
                                    onClick={(e) => {
                                        e.preventDefault();
                                        setResult(null);
                                    }}
                                    className="ml-auto"
                                >
                                    <X size={12} className="text-text-muted hover:text-text" />
                                </button>
                            </div>
                        ) : (
                            <>
                                <p className="text-xs text-text">Upload SRS document</p>
                                <p className="text-[10px] text-text-muted">PDF, DOCX, MD, TXT — drag & drop or click</p>
                            </>
                        )}
                    </div>
                    <input
                        type="file"
                        className="hidden"
                        accept={ALLOWED_EXTENSIONS.join(',')}
                        onChange={onFileSelect}
                        disabled={uploading}
                    />
                </label>
            </div>

            {/* Error */}
            {error && (
                <div className="mt-2 text-xs text-red-400 bg-red-950/40 border border-red-800 rounded p-2 flex items-start gap-2">
                    <X size={12} className="flex-shrink-0 mt-0.5" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    );
};
