import React from 'react';
import { cn } from '../../utils/cn';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export const Skeleton: React.FC<SkeletonProps> = ({ className, ...props }) => {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-slate-200/80', className)}
      {...props}
    />
  );
};

export const JobCardSkeleton: React.FC = () => {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 sm:p-5 flex flex-col justify-between h-[210px]">
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <Skeleton className="w-10 h-10 rounded-md" />
            <div className="space-y-1.5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
          <Skeleton className="h-5 w-16 rounded-md" />
        </div>

        <div className="flex items-center gap-2 mb-3">
          <Skeleton className="h-5 w-20 rounded-md" />
          <Skeleton className="h-5 w-24 rounded-md" />
          <Skeleton className="h-5 w-16 rounded-md" />
        </div>

        <div className="space-y-1.5">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-border">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-7 w-20 rounded-md" />
      </div>
    </div>
  );
};

export const MetricCardSkeleton: React.FC = () => {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 sm:p-5 flex items-center gap-4">
      <Skeleton className="w-12 h-12 rounded-lg" />
      <div className="space-y-2 flex-1">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-3 w-32" />
      </div>
    </div>
  );
};
