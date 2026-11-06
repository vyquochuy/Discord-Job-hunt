export type ThemeId = 'enterprise' | 'glass' | 'ai';

export interface ThemeMeta {
  id: ThemeId;
  short: string;
  label: string;
  description: string;
  /** Representative colours used for the preview swatches in the System page. */
  swatches: string[];
}

export const THEME_STORAGE_KEY = 'jh_theme';
export const DEFAULT_THEME: ThemeId = 'enterprise';

export const THEMES: ThemeMeta[] = [
  {
    id: 'enterprise',
    short: 'A',
    label: 'Modern Enterprise',
    description:
      'Nền tảng doanh nghiệp hiện đại: bề mặt phẳng, viền mảnh, đổ bóng nhẹ và nhịp điệu rõ ràng.',
    swatches: ['#f4f6f9', '#ffffff', '#3668f5', '#8b5cf6'],
  },
  {
    id: 'glass',
    short: 'B',
    label: 'Liquid Glass',
    description:
      'Bề mặt kính mờ, quầng sáng gradient và sidebar nổi bo tròn — mềm mại nhưng vẫn dễ đọc.',
    swatches: ['#dff0f5', 'rgba(255,255,255,.64)', '#087fba', '#8a6ee8'],
  },
  {
    id: 'ai',
    short: 'C',
    label: 'AI Intelligence',
    description:
      'Không gian tối chuyên sâu cho AI: lưới nền, đường viền cyan và hiệu ứng phát sáng có kiểm soát.',
    swatches: ['#080d1c', '#10172a', '#4e8cff', '#06d8e4'],
  },
];

export const THEME_IDS: ThemeId[] = THEMES.map((theme) => theme.id);

export const isThemeId = (value: unknown): value is ThemeId =>
  typeof value === 'string' && (THEME_IDS as string[]).includes(value);

export const getThemeMeta = (id: ThemeId): ThemeMeta =>
  THEMES.find((theme) => theme.id === id) ?? THEMES[0];

/** Reads the persisted theme without touching React state. Safe during SSR. */
export const readStoredTheme = (): ThemeId => {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemeId(stored) ? stored : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
};

/** Applies a theme to <html> so every CSS token resolves immediately. */
export const applyTheme = (theme: ThemeId): void => {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);
  root.style.colorScheme = theme === 'ai' ? 'dark' : 'light';
};
