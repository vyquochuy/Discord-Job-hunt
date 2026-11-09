import React, { useEffect, useState } from 'react';
import { useToast } from '../context/ToastContext';
import * as jobsApi from '../api/jobs.api';
import { Job, JobFilterParams, JobFiltersResponse } from '../types/job';
import { PageHeader } from '../components/layout/PageHeader';
import { JobCard } from '../components/jobs/JobCard';
import { JobCardSkeleton } from '../components/ui/skeleton';
import { EmptyState } from '../components/ui/empty-state';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Sheet, SheetContent } from '../components/ui/sheet';
import {
  Search,
  Filter,
  Plus,
  RotateCcw,
  SlidersHorizontal,
  Briefcase,
} from 'lucide-react';

export interface JobsPageProps {
  onOpenJobDetail: (jobId: string) => void;
  onOpenManualIngest: () => void;
  onOpenScanner: () => void;
}

const PAGE_SIZE = 12;

export const JobsPage: React.FC<JobsPageProps> = ({
  onOpenJobDetail,
  onOpenManualIngest,
  onOpenScanner,
}) => {
  const { showToast } = useToast();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [catalog, setCatalog] = useState<JobFiltersResponse>({ sources: [], levels: [], work_modes: [], locations: [] });
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filterOptions = (key: keyof JobFiltersResponse, label: string) => [
    { value: '', label },
    ...catalog[key].map(option => ({ value: option.value, label: `${option.label} (${option.count})` })),
  ];
  const workModeOptions = filterOptions('work_modes', 'Tất cả hình thức');
  const levelOptions = filterOptions('levels', 'Tất cả cấp bậc');
  const sourceOptions = filterOptions('sources', 'Tất cả nguồn tin');
  const locationOptions = filterOptions('locations', 'Tất cả địa điểm');

  useEffect(() => {
    let active = true;
    jobsApi.getJobFilters().then(data => {
      if (active) setCatalog(data);
    }).catch((err: Error) => {
      if (active) showToast(`Không thể tải bộ lọc: ${err.message}`, 'error');
    });
    return () => { active = false; };
  }, [showToast]);

  // Filters state
  const [keyword, setKeyword] = useState('');
  const [debouncedKeyword, setDebouncedKeyword] = useState('');
  const [workMode, setWorkMode] = useState('');
  const [level, setLevel] = useState('');
  const [source, setSource] = useState('');
  const [location, setLocation] = useState('');

  // Mobile filters drawer
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  // Debounce search input (350ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedKeyword(keyword);
      setPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [keyword]);

  const activeFiltersCount = [workMode, level, source, location].filter(Boolean).length;

  useEffect(() => {
    let active = true;
    setLoading(true);
    const params: JobFilterParams = {
      keyword: debouncedKeyword.trim() || undefined,
      work_mode: workMode || undefined,
      level: level || undefined,
      source: source || undefined,
      location: location || undefined,
      page,
      page_size: PAGE_SIZE,
    };
    jobsApi.getJobs(params).then(res => {
      if (!active) return;
      setJobs(res.items);
      setTotal(res.total);
      const lastPage = Math.max(1, Math.ceil(res.total / PAGE_SIZE));
      if (page > lastPage) setPage(lastPage);
    }).catch((err: Error) => {
      if (active) {
        setJobs([]);
        setTotal(0);
        showToast(`Không thể tải danh sách việc làm: ${err.message}`, 'error');
      }
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [debouncedKeyword, workMode, level, source, location, page, showToast]);

  const handleResetFilters = () => {
    setKeyword('');
    setDebouncedKeyword('');
    setWorkMode('');
    setLevel('');
    setSource('');
    setLocation('');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Khám phá & Tìm kiếm việc làm"
        description={`Tổng cộng ${total.toLocaleString('vi-VN')} tin tuyển dụng IT đang được theo dõi và chuẩn hóa.`}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenManualIngest}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              <span>Thêm JD</span>
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onOpenScanner}
              icon={<Search className="w-3.5 h-3.5" />}
            >
              <span>Quét tin mới</span>
            </Button>
          </>
        }
      />

      {/* Filter Bar */}
      <div className="p-3.5 bg-surface border border-border rounded-lg shadow-card space-y-3">
        <div className="flex items-center gap-2.5">
          {/* Main search input */}
          <div className="flex-1">
            <Input
              type="text"
              placeholder="Tìm theo chức danh, công ty hoặc kỹ năng (Golang, Python, React, AWS)..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              icon={<Search className="w-4 h-4 text-text-muted" />}
            />
          </div>

          {/* Mobile Filter Sheet Trigger */}
          <div className="sm:hidden flex-shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMobileFilterOpen(true)}
              className="gap-1.5"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Lọc</span>
              {activeFiltersCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center">
                  {activeFiltersCount}
                </span>
              )}
            </Button>
          </div>
        </div>

        {/* Desktop Filter Row (Hidden on mobile) */}
        <div className="hidden sm:grid sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2.5 pt-1">
          <Select
            aria-label="Hình thức làm việc"
            value={workMode}
            onChange={(e) => { setWorkMode(e.target.value); setPage(1); }}
            options={workModeOptions}
          />
          <Select
            aria-label="Cấp bậc"
            value={level}
            onChange={(e) => { setLevel(e.target.value); setPage(1); }}
            options={levelOptions}
          />
          <Select
            aria-label="Nguồn tin"
            value={source}
            onChange={(e) => { setSource(e.target.value); setPage(1); }}
            options={sourceOptions}
          />
          <Select
            aria-label="Địa điểm làm việc"
            value={location}
            onChange={(e) => { setLocation(e.target.value); setPage(1); }}
            options={locationOptions}
          />

          <div className="flex items-center gap-2">
            {(activeFiltersCount > 0 || keyword) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetFilters}
                className="w-full text-xs text-text-muted hover:text-text-primary gap-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Đặt lại</span>
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Filters Sheet */}
      <Sheet open={mobileFilterOpen} onOpenChange={setMobileFilterOpen}>
        <SheetContent side="right" className="p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2 font-semibold text-text-primary">
              <Filter className="w-4 h-4 text-primary" />
              <span>Bộ lọc nâng cao</span>
            </div>
            {activeFiltersCount > 0 && (
              <button
                onClick={handleResetFilters}
                className="text-xs text-primary font-medium hover:underline"
              >
                Đặt lại
              </button>
            )}
          </div>

          <div className="space-y-3.5">
            <Select
              label="Hình thức làm việc"
              value={workMode}
              onChange={(e) => { setWorkMode(e.target.value); setPage(1); }}
              options={workModeOptions}
            />
            <Select
              label="Cấp bậc"
              value={level}
              onChange={(e) => { setLevel(e.target.value); setPage(1); }}
              options={levelOptions}
            />
            <Select
              label="Nguồn cào dữ liệu"
              value={source}
              onChange={(e) => { setSource(e.target.value); setPage(1); }}
              options={sourceOptions}
            />
            <Select
              label="Địa điểm làm việc"
              value={location}
              onChange={(e) => { setLocation(e.target.value); setPage(1); }}
              options={locationOptions}
            />
          </div>

          <div className="pt-4 mt-auto border-t border-border">
            <Button
              variant="primary"
              size="md"
              className="w-full justify-center"
              onClick={() => setMobileFilterOpen(false)}
            >
              Áp dụng bộ lọc
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Jobs Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array(6)
            .fill(0)
            .map((_, i) => (
              <JobCardSkeleton key={i} />
            ))}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="w-6 h-6 text-text-muted" />}
          title="Không tìm thấy tin tuyển dụng phù hợp"
          description="Hãy thử thay đổi từ khóa, xóa bớt điều kiện lọc hoặc quét thêm tin mới từ các sàn đối tác."
          action={
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleResetFilters}>
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Đặt lại bộ lọc</span>
              </Button>
              <Button variant="primary" size="sm" onClick={onOpenScanner}>
                <Search className="w-3.5 h-3.5" />
                <span>Quét thêm tin</span>
              </Button>
            </div>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} onOpenDetail={onOpenJobDetail} />
          ))}
        </div>
      )}
      <nav aria-label="Phân trang việc làm" className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" className="text-sm text-text-muted">
          {total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} / {total.toLocaleString('vi-VN')} tin
        </p>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" disabled={loading || page <= 1} onClick={() => setPage(page - 1)} aria-label="Trang trước">Trước</Button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, index) =>
            Math.max(1, Math.min(page - 2, totalPages - 4)) + index
          ).map(number => (
            <Button key={number} variant={number === page ? 'primary' : 'outline'} size="sm"
              aria-label={`Trang ${number}`} aria-current={number === page ? 'page' : undefined}
              disabled={loading} onClick={() => setPage(number)}>{number}</Button>
          ))}
          <Button variant="outline" size="sm" disabled={loading || page >= totalPages} onClick={() => setPage(page + 1)} aria-label="Trang sau">Sau</Button>
        </div>
      </nav>
    </div>
  );
};
