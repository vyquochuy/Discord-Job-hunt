import React from 'react';
import { cn } from '../../utils/cn';

export type BadgeVariant = 'primary' | 'success' | 'warning' | 'danger' | 'purple' | 'slate' | 'outline';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'slate',
  icon,
  children,
  ...props
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    primary: 'bg-primary-50 text-primary-700 border-primary-200',
    success: 'bg-success-50 text-success-700 border-success-200',
    warning: 'bg-warning-50 text-warning-700 border-warning-200',
    danger: 'bg-danger-50 text-danger-700 border-danger-200',
    purple: 'bg-violet-50 text-violet-700 border-violet-200',
    slate: 'bg-surface-muted text-text-secondary border-border',
    outline: 'bg-surface text-text-secondary border-border-strong',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md border transition-colors',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </span>
  );
};
