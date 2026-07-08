import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement ResizeObserver; Radix UI primitives (e.g. the
// password-strength meter's Select-adjacent sizing) require it at mount time.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
