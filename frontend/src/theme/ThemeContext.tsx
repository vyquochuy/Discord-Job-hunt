import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  DEFAULT_THEME,
  THEME_STORAGE_KEY,
  applyTheme,
  getThemeMeta,
  isThemeId,
  normalizeThemeId,
  readSystemTheme,
  type ThemeId,
  type ThemeMeta,
} from './tokens';

interface ThemeContextValue {
  /** Active appearance mode. */
  theme: ThemeId;
  isDark: boolean;
  meta: ThemeMeta;
  setTheme: (theme: ThemeId) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/** Stored preference wins; otherwise follow the OS (light when undecided). */
const resolveInitialTheme = (): ThemeId => {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored) return normalizeThemeId(stored);
  } catch {
    /* storage blocked (private mode) — fall through to the OS preference */
  }
  return readSystemTheme();
};

const hasStoredPreference = (): boolean => {
  try {
    return Boolean(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return false;
  }
};

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeId>(resolveInitialTheme);

  // Keep <html data-theme> and the persisted preference in sync.
  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      /* storage can be blocked (private mode) — theme still applies for the session */
    }
  }, [theme]);

  // PERF: enable colour transitions only after the first paint. Otherwise the
  // initial `background-color` transition animates a full-page repaint on every
  // load (a brief fade from the browser default to the theme canvas).
  useEffect(() => {
    const root = document.documentElement;
    const id = window.requestAnimationFrame(() => root.classList.add('theme-transitions'));
    return () => {
      window.cancelAnimationFrame(id);
      root.classList.remove('theme-transitions');
    };
  }, []);

  // Follow the OS preference only while the user has not picked a mode yet.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (event: MediaQueryListEvent) => {
      if (hasStoredPreference()) return;
      setThemeState(event.matches ? 'dark' : 'light');
    };
    query.addEventListener('change', handler);
    return () => query.removeEventListener('change', handler);
  }, []);

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(isThemeId(next) ? next : DEFAULT_THEME);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => (current === 'dark' ? 'light' : 'dark'));
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, isDark: theme === 'dark', meta: getThemeMeta(theme), setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
};
