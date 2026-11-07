import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  DEFAULT_THEME,
  THEME_STORAGE_KEY,
  applyTheme,
  getThemeMeta,
  isThemeId,
  readStoredTheme,
  type ThemeId,
  type ThemeMeta,
} from './tokens';

interface ThemeContextValue {
  theme: ThemeId;
  meta: ThemeMeta;
  setTheme: (theme: ThemeId) => void;
  cycleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeId>(() => readStoredTheme());

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

  // Follow the OS preference only while the user has not picked a theme yet.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (event: MediaQueryListEvent) => {
      try {
        if (window.localStorage.getItem(THEME_STORAGE_KEY)) return;
      } catch {
        return;
      }
      setThemeState(event.matches ? 'ai' : DEFAULT_THEME);
    };
    query.addEventListener('change', handler);
    return () => query.removeEventListener('change', handler);
  }, []);

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(isThemeId(next) ? next : DEFAULT_THEME);
  }, []);

  const cycleTheme = useCallback(() => {
    setThemeState((current) => (current === 'enterprise' ? 'glass' : current === 'glass' ? 'ai' : 'enterprise'));
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, meta: getThemeMeta(theme), setTheme, cycleTheme }),
    [theme, setTheme, cycleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
};
