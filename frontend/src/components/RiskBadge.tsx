import { ShieldAlert, ShieldCheck, AlertTriangle, HelpCircle } from 'lucide-react';
import type { RiskCategory } from '../types';

interface RiskBadgeProps {
  category: RiskCategory;
  score?: number | null;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ category, score, size = 'md' }) => {
  const configMap = {
    Low: {
      bg: 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40 shadow-xs shadow-emerald-500/10',
      dot: 'bg-emerald-400 shadow-[0_0_8px_#10B981]',
      pill: 'bg-emerald-900/60 text-emerald-200 border-emerald-500/30',
      icon: ShieldCheck,
      label: 'Low Risk',
      accent: '#10B981',
    },
    Medium: {
      bg: 'bg-amber-950/60 text-amber-300 border-amber-500/40 shadow-xs shadow-amber-500/10',
      dot: 'bg-amber-400 shadow-[0_0_8px_#F59E0B]',
      pill: 'bg-amber-900/60 text-amber-200 border-amber-500/30',
      icon: AlertTriangle,
      label: 'Medium Risk',
      accent: '#F59E0B',
    },
    High: {
      bg: 'bg-rose-950/60 text-rose-300 border-rose-500/40 shadow-xs shadow-rose-500/10',
      dot: 'bg-rose-400 shadow-[0_0_8px_#EF4444]',
      pill: 'bg-rose-900/60 text-rose-200 border-rose-500/30',
      icon: ShieldAlert,
      label: 'High Risk',
      accent: '#EF4444',
    },
    'Insufficient Data': {
      bg: 'bg-slate-900/80 text-slate-300 border-slate-700 shadow-xs',
      dot: 'bg-slate-400',
      pill: 'bg-slate-800 text-slate-300 border-slate-700',
      icon: HelpCircle,
      label: 'Inconclusive',
      accent: '#64748B',
    },
  };

  const config = configMap[category] || configMap['Insufficient Data'];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm font-medium',
    lg: 'px-4 py-1.5 text-base font-semibold',
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border backdrop-blur-md ${config.bg} ${sizeClasses}`}
    >
      <Icon className={size === 'sm' ? 'w-3.5 h-3.5' : size === 'md' ? 'w-4 h-4' : 'w-5 h-5'} />
      <span>{config.label}</span>
      {score !== undefined && score !== null && (
        <span className={`ml-1 px-1.5 py-0.2 rounded-full border text-xs font-mono font-bold ${config.pill}`}>
          {score}/100
        </span>
      )}
    </span>
  );
};
