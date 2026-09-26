import React from 'react';
import { MapPin, Laptop, Layers, DollarSign, Clock, ChevronRight } from 'lucide-react';
import { Job } from '../../types/job';
import { formatCurrency, formatDate, getCompanyMonogram, getSourceBadgeInfo } from '../../utils/formatters';
import { Card } from '../ui/card';
import { Button } from '../ui/button';

export interface JobCardProps {
  job: Job;
  matchScore?: number;
  onOpenDetail: (jobId: string) => void;
  className?: string;
}

export const JobCard: React.FC<JobCardProps> = ({ job, matchScore, onOpenDetail, className }) => {
  const monogram = getCompanyMonogram(job.company_name);
  const sourceInfo = getSourceBadgeInfo(job.source);

  const salaryText =
    job.min_salary || job.max_salary
      ? `${formatCurrency(job.min_salary, job.salary_currency)} - ${formatCurrency(job.max_salary, job.salary_currency)}`
      : 'Thỏa thuận';

  return (
    <Card
      hoverable
      onClick={() => onOpenDetail(job.id)}
      className={`p-4 sm:p-5 flex flex-col justify-between cursor-pointer transition-all ${className || ''}`}
    >
      <div>
        {/* Header: Company Avatar & Title & Source */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center flex-shrink-0 border border-slate-200">
              {monogram}
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm sm:text-base font-semibold text-text-primary group-hover:text-primary transition-colors truncate">
                {job.title}
              </h3>
              <p className="text-xs text-text-secondary font-medium truncate mt-0.5">
                {job.company_name || 'N/A'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded border ${sourceInfo.colorClass}`}
              title={`Nguồn tin: ${sourceInfo.label}`}
            >
              {sourceInfo.label}
            </span>
          </div>
        </div>

        {/* Metadata badges */}
        <div className="flex items-center gap-1.5 flex-wrap text-xs text-text-secondary mb-3">
          <span className="inline-flex items-center gap-1 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-[11px]">
            <MapPin className="w-3 h-3 text-slate-400" />
            <span className="truncate max-w-[120px]">{job.location || 'Việt Nam'}</span>
          </span>

          <span className="inline-flex items-center gap-1 bg-blue-50/70 border border-blue-200 text-blue-700 px-2 py-0.5 rounded text-[11px]">
            <Laptop className="w-3 h-3 text-blue-500" />
            <span>{job.work_mode || 'ONSITE'}</span>
          </span>

          <span className="inline-flex items-center gap-1 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-[11px]">
            <Layers className="w-3 h-3 text-slate-400" />
            <span>{job.level || 'All Levels'}</span>
          </span>

          {(job.min_salary || job.max_salary) && (
            <span className="inline-flex items-center gap-1 bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-0.5 rounded text-[11px] font-medium">
              <DollarSign className="w-3 h-3 text-emerald-500" />
              <span>{salaryText}</span>
            </span>
          )}

          {matchScore !== undefined && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold border ${
                matchScore >= 80
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : matchScore >= 60
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : 'bg-slate-50 text-slate-700 border-slate-200'
              }`}
            >
              {Math.round(matchScore)}% Match
            </span>
          )}
        </div>

        {/* Snippet */}
        <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed mb-4">
          {job.description || job.description_raw
            ? (job.description || job.description_raw || '').replace(/<[^>]*>?/gm, '').trim()
            : 'Chưa có thông tin mô tả chi tiết công việc.'}
        </p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border mt-auto text-xs text-text-muted">
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>{formatDate(job.posted_at || job.created_at)}</span>
        </div>

        <Button
          variant="outline"
          size="xs"
          onClick={(e) => {
            e.stopPropagation();
            onOpenDetail(job.id);
          }}
          className="text-xs gap-1"
        >
          <span>Chi tiết</span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        </Button>
      </div>
    </Card>
  );
};
