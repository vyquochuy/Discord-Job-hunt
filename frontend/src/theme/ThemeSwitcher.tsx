import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { cn } from '../utils/cn';
import { useTheme } from './ThemeContext';

export interface ThemeSwitcherProps {
  className?: string;
}

/**
 * Compact appearance toggle: one button, two icon slots, a sliding thumb.
 * No theme names, no descriptions — the Sun/Moon pair is the whole control.
 * Reads and writes the shared ThemeContext, so every surface follows instantly.
 */
export const ThemeSwitcher: React.FC<ThemeSwitcherProps> = ({ className }) => {
  const { isDark, toggleTheme } = useTheme();
  const label = isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối';

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={label}
      title={label}
      onClick={toggleTheme}
      className={cn('app-theme-switcher', className)}
    >
      <span className="app-theme-switcher__thumb" aria-hidden="true" />
      <span className="app-theme-switcher__icon" data-active={!isDark} aria-hidden="true">
        <Sun className="h-3.5 w-3.5" />
      </span>
      <span className="app-theme-switcher__icon" data-active={isDark} aria-hidden="true">
        <Moon className="h-3.5 w-3.5" />
      </span>
    </button>
  );
};
