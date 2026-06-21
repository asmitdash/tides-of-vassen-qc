import { TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export default function Textarea({ label, className = '', ...props }: TextareaProps) {
  const baseStyles =
    'bg-slate-900 border border-slate-700 focus:border-amber-400 focus:ring-1 focus:ring-amber-400/30 rounded-md px-3 py-2 text-slate-100 w-full resize-none';

  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-medium text-slate-300">{label}</label>}
      <textarea className={`${baseStyles} ${className}`} {...props} />
    </div>
  );
}
