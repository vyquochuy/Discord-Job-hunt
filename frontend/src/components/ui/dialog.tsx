import React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export interface DialogContentProps extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, children, size = 'md', ...props }, ref) => {
  const sizeStyles: Record<string, string> = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-5xl',
  };

  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[2px] transition-opacity animate-in fade-in" />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          'fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%]',
          'w-[calc(100%-2rem)] max-h-[90vh] bg-surface rounded-xl border border-border shadow-dialog overflow-hidden flex flex-col',
          'animate-in fade-in zoom-in-95 duration-150',
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1.5 text-text-muted hover:text-text-primary hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40">
          <X className="w-4 h-4" />
          <span className="sr-only">Đóng</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
});
DialogContent.displayName = DialogPrimitive.Content.displayName;

export const DialogHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('px-5 sm:px-6 py-4 border-b border-border bg-white flex-shrink-0', className)} {...props} />
);
DialogHeader.displayName = 'DialogHeader';

export const DialogTitle: React.FC<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>> = ({
  className,
  ...props
}) => (
  <DialogPrimitive.Title
    className={cn('text-base sm:text-lg font-semibold text-text-primary leading-tight', className)}
    {...props}
  />
);
DialogTitle.displayName = DialogPrimitive.Title.displayName;

export const DialogDescription: React.FC<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>> = ({
  className,
  ...props
}) => (
  <DialogPrimitive.Description className={cn('text-xs sm:text-sm text-text-secondary mt-1', className)} {...props} />
);
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export const DialogBody: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('p-5 sm:p-6 overflow-y-auto flex-1', className)} {...props} />
);
DialogBody.displayName = 'DialogBody';

export const DialogFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div
    className={cn(
      'px-5 sm:px-6 py-3.5 bg-slate-50 border-t border-border flex items-center justify-end gap-2.5 flex-shrink-0',
      className
    )}
    {...props}
  />
);
DialogFooter.displayName = 'DialogFooter';
