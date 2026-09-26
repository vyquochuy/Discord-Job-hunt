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
        bg: 'bg-emerald-50',
        text: 'text-emerald-700',
        border: 'border-emerald-200',
        bar: 'bg-emerald-600',
      };
    }
    if (s >= 60) {
      return {
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        border: 'border-amber-200',
        bar: 'bg-amber-600',
      };
    }
    return {
      bg: 'bg-slate-50',
      text: 'text-slate-700',
      border: 'border-slate-200',
      bar: 'bg-slate-500',
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
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
            <Check className="w-3 h-3" /> Đạt điều kiện
          </span>
        );
      case 'BORDERLINE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
            <HelpCircle className="w-3 h-3" /> Cần đối soát
          </span>
        );
      case 'INELIGIBLE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded">
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
