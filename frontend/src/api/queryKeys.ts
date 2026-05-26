export const queryKeys = {
    sandbox: {
        status: (sessionId: string) => ['sandbox', sessionId, 'status'] as const,
        files: (sessionId: string) => ['sandbox', sessionId, 'files'] as const,
        usage: (sessionId: string) => ['sandbox', sessionId, 'usage'] as const,
    },
    settings: {
        all: ['settings'] as const,
        profiles: ['settings', 'profiles'] as const,
        profile: (profileId: string) => ['settings', 'profiles', profileId] as const,
    },
    secrets: {
        all: ['secrets'] as const,
        provider: (provider: string) => ['secrets', provider] as const,
    },
    conversations: {
        all: ['conversations'] as const,
        byId: (conversationId: string) => ['conversations', conversationId] as const,
    },
};
