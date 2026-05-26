# Hotfix: Computed Getters Issue

## Problem

After implementing per-session state, the workspace showed "No files generated yet..." even though the agent was generating files. The issue was that Zustand doesn't support computed getters using the `get` syntax inside the store definition.

## Root Cause

I initially tried to use computed getters like this:

```typescript
export const useAgentStore = create<AgentStore>((set, get) => ({
    filesBySession: {},
    
    // ❌ This doesn't work in Zustand!
    get files() {
        return get().filesBySession[get().activeSessionId] || {};
    },
}));
```

**Why it failed:**
- Zustand doesn't support ES6 getter syntax in the store definition
- The `get()` function inside a getter creates circular dependencies
- Components couldn't access the computed values

## Solution

Instead of computed getters in the store, components now directly access per-session data:

```typescript
// In components:
const { filesBySession, activeSessionId } = useAgentStore();
const files = filesBySession[activeSessionId] || {};
```

## Files Modified

1. **`frontend/src/store/agentStore.ts`**
   - Removed computed getters from interface
   - Removed getter implementations from store

2. **`frontend/src/components/FileBrowser.tsx`**
   - Access `filesBySession[activeSessionId]` directly
   - Access `activeFileBySession[activeSessionId]` directly

3. **`frontend/src/components/MonacoEditor.tsx`**
   - Access `filesBySession[activeSessionId]` directly
   - Access `activeFileBySession[activeSessionId]` directly

4. **`frontend/src/components/Terminal.tsx`**
   - Access `logsBySession[activeSessionId]` directly

5. **`frontend/src/components/BrowserPreview.tsx`**
   - Access `previewUrlBySession[activeSessionId]` directly

6. **`frontend/src/components/SandboxPanel.tsx`**
   - Access `sandboxBySession[activeSessionId]` directly
   - Access `previewUrlBySession[activeSessionId]` directly

## Pattern Used

### Before (Broken)
```typescript
// Store
interface AgentStore {
    files: Record<string, string>;  // Computed getter
}

// Component
const { files } = useAgentStore();
```

### After (Working)
```typescript
// Store
interface AgentStore {
    filesBySession: Record<string, Record<string, string>>;
    activeSessionId: string;
}

// Component
const { filesBySession, activeSessionId } = useAgentStore();
const files = filesBySession[activeSessionId] || {};
```

## Benefits of This Approach

1. **Explicit**: Clear that we're accessing per-session data
2. **Type-safe**: TypeScript can properly infer types
3. **Performant**: No getter overhead
4. **Zustand-compatible**: Works with Zustand's reactivity model
5. **Debuggable**: Easy to inspect in React DevTools

## Testing

After this fix:
1. ✅ Files should appear in the File Browser when agent generates them
2. ✅ Code should appear in the Monaco Editor
3. ✅ Terminal logs should appear in the Terminal panel
4. ✅ Browser preview should work
5. ✅ Switching sessions should show different files

## Alternative Approaches Considered

### 1. Zustand Middleware
Could use `subscribeWithSelector` middleware, but adds complexity.

### 2. Derived State Hook
Could create a custom hook:
```typescript
function useCurrentSessionData() {
    const { filesBySession, activeSessionId } = useAgentStore();
    return {
        files: filesBySession[activeSessionId] || {},
        // ...
    };
}
```
This would work but adds an extra layer of abstraction.

### 3. Selector Functions
Could use Zustand selectors:
```typescript
const files = useAgentStore(state => 
    state.filesBySession[state.activeSessionId] || {}
);
```
This is more performant but less readable.

## Recommendation

The current approach (direct access in components) is the best balance of:
- Simplicity
- Readability
- Performance
- Type safety
- Zustand compatibility

## Future Improvements

If we find ourselves repeating the pattern too much, we could create a helper hook:

```typescript
// hooks/useSessionData.ts
export function useSessionData() {
    const { 
        filesBySession, 
        activeFileBySession,
        logsBySession,
        sandboxBySession,
        previewUrlBySession,
        activeSessionId 
    } = useAgentStore();
    
    return {
        files: filesBySession[activeSessionId] || {},
        activeFile: activeFileBySession[activeSessionId] || null,
        logs: logsBySession[activeSessionId] || '',
        sandbox: sandboxBySession[activeSessionId] || null,
        previewUrl: previewUrlBySession[activeSessionId] || null,
    };
}

// Usage in components:
const { files, logs, sandbox } = useSessionData();
```

This would provide the convenience of computed getters while working with Zustand's architecture.
