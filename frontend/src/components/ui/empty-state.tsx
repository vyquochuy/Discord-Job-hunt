import React from 'react';
import { cn } from '../../utils/cn';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-lg p-8 sm:p-12 text-center flex flex-col items-center justify-center',
        className
      )}
    >
      {icon && (
        <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center mb-3.5 flex-shrink-0">
          {icon}
        </div>
      )}
      <h3 className="text-base sm:text-lg font-semibold text-text-primary mb-1.5">{title}</h3>
      {description && (
        <p className="text-xs sm:text-sm text-text-secondary max-w-md mx-auto leading-relaxed mb-5">
          {description}
        </p>
      )}
      {action && <div className="flex items-center justify-center gap-2.5 flex-wrap">{action}</div>}
    </div>
  );
};
