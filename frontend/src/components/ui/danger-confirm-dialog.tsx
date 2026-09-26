import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
} from './dialog';
import { Button } from './button';
import { Input } from './input';
import { AlertTriangle } from 'lucide-react';

export interface DangerConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmationKeyword?: string;
  confirmLabel?: string;
  onConfirm: () => Promise<void> | void;
  loading?: boolean;
}

export const DangerConfirmDialog: React.FC<DangerConfirmDialogProps> = ({
  open,
  onOpenChange,
  title,
  description,
  confirmationKeyword = 'DELETE',
  confirmLabel = 'Xóa vĩnh viễn',
  onConfirm,
  loading = false,
}) => {
  const [typedValue, setTypedValue] = useState('');
  const isMatch = typedValue.trim() === confirmationKeyword;

  const handleClose = () => {
    if (!loading) {
      setTypedValue('');
      onOpenChange(false);
    }
  };

  const handleConfirm = async () => {
    if (!isMatch) return;
    await onConfirm();
    setTypedValue('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent size="sm">
        <DialogHeader>
          <div className="flex items-center gap-2.5 text-danger">
            <div className="w-8 h-8 rounded-md bg-red-100 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-4 h-4 text-danger" />
            </div>
            <DialogTitle className="text-danger">{title}</DialogTitle>
          </div>
          <DialogDescription className="text-text-secondary mt-2 leading-relaxed">
            {description}
          </DialogDescription>
        </DialogHeader>

        <DialogBody>
          <div className="p-3.5 bg-red-50/60 border border-red-200 rounded-md text-xs text-red-800 mb-4 leading-relaxed">
            Hành động này mang tính phá hủy và <strong>không thể hoàn tác</strong>. Dữ liệu liên quan sẽ bị xóa vĩnh viễn khỏi máy chủ.
          </div>

          <div className="space-y-2">
            <p className="text-xs text-text-secondary">
              Vui lòng gõ chính xác từ khóa{' '}
              <strong className="font-mono bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 text-danger font-bold">
                {confirmationKeyword}
              </strong>{' '}
              để xác nhận thực thi:
            </p>
            <Input
              type="text"
              placeholder={`Gõ ${confirmationKeyword} vào đây...`}
              value={typedValue}
              onChange={(e) => setTypedValue(e.target.value)}
              className="font-mono text-sm tracking-wide"
              autoFocus
            />
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={handleClose} disabled={loading}>
            Hủy bỏ
          </Button>
          <Button
            variant="critical"
            size="sm"
            disabled={!isMatch || loading}
            loading={loading}
            onClick={handleConfirm}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
