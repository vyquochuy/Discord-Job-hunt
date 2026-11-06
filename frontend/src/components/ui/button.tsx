import React, { forwardRef } from 'react';
import { cn } from '../../utils/cn';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'critical';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading = false, disabled, icon, children, ...props }, ref) => {
    const variantStyles: Record<ButtonVariant, string> = {
      primary: 'app-btn-primary focus-visible:ring-primary/40',
      secondary: 'bg-surface-muted text-text-primary hover:bg-surface-2 border border-border focus-visible:ring-primary/30',
      outline: 'bg-surface border border-border hover:bg-surface-2 text-text-secondary shadow-subtle focus-visible:ring-primary/30',
      ghost: 'bg-transparent text-text-secondary hover:bg-surface-muted hover:text-text-primary focus-visible:ring-primary/30',
      danger: 'bg-danger text-white hover:bg-danger-700 shadow-subtle focus-visible:ring-danger/40',
      critical: 'bg-critical text-white hover:bg-critical-800 shadow-subtle focus-visible:ring-critical/40',
    };

    const sizeStyles: Record<ButtonSize, string> = {
      xs: 'h-7 px-2 text-xs gap-1.5 rounded-sm',
      sm: 'h-8 px-3 text-xs sm:text-sm gap-1.5 rounded-md',
      md: 'h-9 px-3.5 text-sm gap-2 rounded-md',
      lg: 'h-10 px-4 text-base gap-2 rounded-lg',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors select-none whitespace-nowrap',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1',
          'disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          icon && <span className="flex-shrink-0">{icon}</span>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
