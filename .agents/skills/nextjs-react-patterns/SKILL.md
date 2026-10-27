---
name: nextjs-react-patterns
description: Best practices for Next.js 14+ App Router, React 19, performance, state management, and avoiding common anti-patterns like setState in useEffect. Use when developing frontend pages, chess components, or refactoring React code.
license: MIT
---

# Next.js & React 19 Best Practices for Chessian.AI

Guidelines for writing clean, high-performance Next.js and React code across Chessian.AI's frontend (`frontend/src/**`).

## 1. React 19 & Hooks Rules: Avoid setState in Effects

The project uses React 19 and ESLint 9 (`react-hooks/set-state-in-effect`). Never call `setState` synchronously inside a `useEffect` body to synchronize state.

### Anti-Pattern: Synchronizing props or URL query to state via useEffect
```tsx
// ❌ WRONG: Causes cascading renders and ESLint errors
useEffect(() => {
  setOpeningEco(openingParam);
}, [openingParam]);
```

### Pattern A: Derive State During Render
If a value can be computed or derived from props or search parameters, calculate it directly during rendering:
```tsx
// ✅ CORRECT: No redundant state, no effect needed
const openingEco = searchParams.get("opening") || "";
```

### Pattern B: Event Handlers Over Effects
Put interaction, navigation, and reset logic in the callback that initiated it:
```tsx
// ❌ WRONG: Effect watches filter change and resets page
useEffect(() => {
  setPage(1);
}, [searchQuery, filter]);

// ✅ CORRECT: Reset page inside the change event handler
const handleSearchChange = (newQuery: string) => {
  setSearchQuery(newQuery);
  setPage(1);
};
```

### Pattern C: Asynchronous Data Fetching in Effects
When fetching data on mount or when dependencies change, ensure the fetch function handles its own loading lifecycle cleanly or uses an abort controller:
```tsx
useEffect(() => {
  let isSubscribed = true;

  async function loadData() {
    setLoading(true);
    try {
      const data = await api.getGames();
      if (isSubscribed) setGames(data);
    } catch (err) {
      if (isSubscribed) setError(err);
    } finally {
      if (isSubscribed) setLoading(false);
    }
  }

  loadData();
  return () => {
    isSubscribed = false;
  };
}, [filter]);
```

---

## 2. Eliminating Waterfalls & Fast Loading

- **Start promises early**: If fetching multiple resources (e.g. game details + engine analysis + opening stats), initiate them with `Promise.all()` instead of sequential awaits.
- **Client vs Server Components**:
  - Keep interactive chess board components (`Chessground`, user controls, move sliders) as `'use client'`.
  - Keep data wrappers and layouts as Server Components where appropriate to reduce client bundle size.

---

## 3. Styling & Architecture Conventions

- **CSS Modules only**: Use `[name].module.css`. Do not add inline `style={{ ... }}` except for dynamic values (such as eval bar height or piece coordinate transforms).
- **No `any`**: Strict TypeScript everywhere. Use proper types for FENs, move objects (`MoveAnalysis`, `GameAnalysis`), and API responses.
- **Chessground & Board Lifecycle**:
  - Avoid re-creating the Chessground DOM instance on every state change.
  - Use `chessground.set({ fen, turnColor, movable: { ... } })` for updating state smoothly.
