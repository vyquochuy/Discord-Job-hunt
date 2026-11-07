/**
 * Appearance model — two modes of a single visual identity (Liquid Glass).
 *
 * There is no longer a "pick a design" concept: the product ships one visual
 * language with a light and a dark rendering. Both resolve through the same
 * semantic CSS token names, so no component ever branches on the mode.
 *
 *   mode 'light' → <html data-theme="glass">       (default)
 *   mode 'dark'  → <html data-theme="glass-dark">
 */
export type ThemeId = 'light' | 'dark';

export interface ThemeMeta {
  id: ThemeId;
  /** Human label used by the System page status line (never in the header toggle). */
  label: string;
  dataTheme: 'glass' | 'glass-dark';
  colorScheme: 'light' | 'dark';
}

export const THEME_STORAGE_KEY = 'jh_theme';
export const DEFAULT_THEME: ThemeId = 'light';

export const THEMES: ThemeMeta[] = [
  { id: 'light', label: 'Sáng', dataTheme: 'glass', colorScheme: 'light' },
  { id: 'dark', label: 'Tối', dataTheme: 'glass-dark', colorScheme: 'dark' },
];

export const THEME_IDS: ThemeId[] = THEMES.map((theme) => theme.id);

export const isThemeId = (value: unknown): value is ThemeId =>
  typeof value === 'string' && (THEME_IDS as string[]).includes(value);

export const getThemeMeta = (id: ThemeId): ThemeMeta =>
  THEMES.find((theme) => theme.id === id) ?? THEMES[0];

/**
 * Maps any value that may already be persisted on a user's device to a mode.
 * The previous release stored `enterprise` / `glass` / `ai`; those migrate
 * silently so nobody loses their preference on deploy.
 */
export const normalizeThemeId = (value: unknown): ThemeId => {
  if (isThemeId(value)) return value;
  if (value === 'ai') return 'dark';
  // 'glass' and 'enterprise' were both light themes.
  if (value === 'glass' || value === 'enterprise') return 'light';
  return DEFAULT_THEME;
};

/** Reads the persisted mode without touching React state. Safe during SSR. */
export const readStoredTheme = (): ThemeId => {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  try {
    return normalizeThemeId(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return DEFAULT_THEME;
  }
};

/** Applies a mode to <html> so every CSS token resolves immediately. */
export const applyTheme = (theme: ThemeId): void => {
  if (typeof document === 'undefined') return;
  const meta = getThemeMeta(theme);
  const root = document.documentElement;
  root.setAttribute('data-theme', meta.dataTheme);
  root.style.colorScheme = meta.colorScheme;
};

/** The OS preference, used only while the user has not chosen explicitly. */
export const readSystemTheme = (): ThemeId => {
  if (typeof window === 'undefined' || !window.matchMedia) return DEFAULT_THEME;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};
