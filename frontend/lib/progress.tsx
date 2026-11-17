"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { chapters } from "./curriculum";

const STORAGE_KEY = "pyjourney.progress.v1";

type ProgressContextValue = {
  completed: Set<string>;
  ready: boolean;
  count: number;
  total: number;
  isComplete: (slug: string) => boolean;
  toggle: (slug: string) => void;
};

const ProgressContext = createContext<ProgressContextValue | null>(null);

export function ProgressProvider({ children }: { children: ReactNode }) {
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          setCompleted(
            new Set(parsed.filter((value): value is string => typeof value === "string")),
          );
        }
      }
    } catch {
      // localStorage can be unavailable in private mode; keep an empty set.
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...completed]));
    } catch {
      // Ignore quota/permission errors.
    }
  }, [completed, ready]);

  const toggle = useCallback((slug: string) => {
    setCompleted((previous) => {
      const next = new Set(previous);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        next.add(slug);
      }
      return next;
    });
  }, []);

  const value = useMemo<ProgressContextValue>(
    () => ({
      completed,
      ready,
      count: completed.size,
      total: chapters.length,
      isComplete: (slug: string) => completed.has(slug),
      toggle,
    }),
    [completed, ready, toggle],
  );

  return <ProgressContext.Provider value={value}>{children}</ProgressContext.Provider>;
}

export function useProgress(): ProgressContextValue {
  const value = useContext(ProgressContext);
  if (!value) {
    throw new Error("useProgress harus dipakai di dalam ProgressProvider.");
  }
  return value;
}
