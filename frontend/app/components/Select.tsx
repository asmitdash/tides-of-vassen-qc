import { SelectHTMLAttributes } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export default function Select({ label, className = '', children, ...props }: SelectProps) {
  const baseStyles =
    'bg-slate-900 border border-slate-700 focus:border-amber-400 focus:ring-1 focus:ring-amber-400/30 rounded-md px-3 py-2 text-slate-100 w-full';

  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-medium text-slate-300">{label}</label>}
      <select className={`${baseStyles} ${className}`} {...props}>
        {children}
      </select>
    </div>
  );
}
