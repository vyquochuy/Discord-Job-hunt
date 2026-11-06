import React from 'react';
import { cn } from '../../utils/cn';
import { Eligibility } from '../../types/match';
import { Check, AlertCircle, HelpCircle } from 'lucide-react';

export interface MatchScoreBadgeProps {
  score: number;
  eligibility?: Eligibility;
  size?: 'sm' | 'md' | 'lg';
  showEligibility?: boolean;
  className?: string;
}

export const MatchScoreBadge: React.FC<MatchScoreBadgeProps> = ({
  score,
  eligibility,
  size = 'md',
  showEligibility = false,
  className,
}) => {
  const roundedScore = Math.round(score);

  const getScoreColors = (s: number) => {
    if (s >= 80) {
      return {
        bg: 'bg-success-50',
        text: 'text-success-700',
        border: 'border-success-200',
        bar: 'bg-success-600',
      };
    }
    if (s >= 60) {
      return {
        bg: 'bg-warning-50',
        text: 'text-warning-700',
        border: 'border-warning-200',
        bar: 'bg-warning-600',
      };
    }
    return {
      bg: 'bg-surface-2',
      text: 'text-text-secondary',
      border: 'border-border',
      bar: 'bg-text-muted',
    };
  };

  const colors = getScoreColors(roundedScore);

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3.5 py-1.5 font-bold',
  };

  const getEligibilityBadge = (elig: Eligibility) => {
    switch (elig) {
      case 'ELIGIBLE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-success-700 bg-success-50 border border-success-200 px-2 py-0.5 rounded">
            <Check className="w-3 h-3" /> Đạt điều kiện
          </span>
        );
      case 'BORDERLINE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-warning-700 bg-warning-50 border border-warning-200 px-2 py-0.5 rounded">
            <HelpCircle className="w-3 h-3" /> Cần đối soát
          </span>
        );
      case 'INELIGIBLE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-danger-700 bg-danger-50 border border-danger-200 px-2 py-0.5 rounded">
            <AlertCircle className="w-3 h-3" /> Không đủ ĐK
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-md font-semibold border transition-colors',
          colors.bg,
          colors.text,
          colors.border,
          sizeClasses[size]
        )}
      >
        <span>{roundedScore}%</span>
        <span className="text-[10px] font-normal opacity-80 uppercase tracking-wider">Match</span>
      </div>
      {showEligibility && eligibility && getEligibilityBadge(eligibility)}
    </div>
  );
};
