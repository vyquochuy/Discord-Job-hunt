import React from 'react';
import { cn } from '../utils/cn';
import { useTheme } from './ThemeContext';
import { THEMES } from './tokens';

export interface ThemeSwitcherProps {
  className?: string;
  /** Hide the text label and render only the A/B/C chip (used on narrow screens). */
  compact?: boolean;
}

/**
 * A/B/C segmented control that mirrors the Figma Make concept switcher.
 * Reads and writes the shared ThemeContext — layout and content never change.
 */
export const ThemeSwitcher: React.FC<ThemeSwitcherProps> = ({ className, compact = false }) => {
  const { theme, setTheme } = useTheme();

  return (
    <div
      className={cn('app-theme-switcher', className)}
      role="radiogroup"
      aria-label="Chọn giao diện"
    >
      {THEMES.map((option) => {
        const selected = theme === option.id;
        return (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={selected}
            title={option.label}
            onClick={() => setTheme(option.id)}
          >
            <b aria-hidden="true">{option.short}</b>
            {!compact && <span>{option.label}</span>}
          </button>
        );
      })}
    </div>
  );
};
