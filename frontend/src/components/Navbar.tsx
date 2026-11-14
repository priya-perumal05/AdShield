import { Shield, ShieldAlert, Cpu, RefreshCw } from 'lucide-react';
import type { BackendHealth } from '../types';

interface NavbarProps {
  health: BackendHealth | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
  activeTab: 'home' | 'scanner' | 'history';
  onNavigate: (tab: 'home' | 'scanner' | 'history') => void;
  sessionCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  healthLoading,
  onRefreshHealth,
  activeTab,
  onNavigate,
  sessionCount,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-[#050B18]/90 backdrop-blur-md border-b border-[#1E3A5F]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => onNavigate('home')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-blue-500 to-cyan-400 flex items-center justify-center text-white shadow-md shadow-cyan-500/20 group-hover:shadow-cyan-400/40 group-hover:scale-105 transition-all">
              <Shield className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-xl tracking-tight text-[#F8FAFC]">
                  Ad<span className="text-[#22D3EE]">Shield</span>
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-[#0D1B2E] border border-[#1E3A5F] text-[#22D3EE]">
                  AI
                </span>
              </div>
              <p className="text-[11px] font-medium text-slate-400 -mt-1 hidden sm:block">
                Fake Advertisement Detection System
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5">
            <button
              onClick={() => onNavigate('home')}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === 'home'
                  ? 'bg-[#11243A] text-[#22D3EE] border border-[#1E3A5F] shadow-xs'
                  : 'text-slate-400 hover:text-[#F8FAFC] hover:bg-[#0D1B2E]'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => onNavigate('scanner')}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === 'scanner'
                  ? 'bg-[#11243A] text-[#22D3EE] border border-[#1E3A5F] shadow-xs'
                  : 'text-slate-400 hover:text-[#F8FAFC] hover:bg-[#0D1B2E]'
              }`}
            >
              Ad Scanner
            </button>
            <button
              onClick={() => onNavigate('history')}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'history'
                  ? 'bg-[#11243A] text-[#22D3EE] border border-[#1E3A5F] shadow-xs'
                  : 'text-slate-400 hover:text-[#F8FAFC] hover:bg-[#0D1B2E]'
              }`}
            >
              <span>Session Scans</span>
              {sessionCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-blue-600 text-white text-xs font-mono font-bold">
                  {sessionCount}
                </span>
              )}
            </button>
          </nav>

          {/* Backend Status & CTA */}
          <div className="flex items-center gap-3">
            {/* Health Status Pill */}
            <div className="relative group">
              <div
                className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium cursor-pointer transition-all ${
                  healthLoading
                    ? 'bg-slate-900/80 text-slate-400 border-slate-700'
                    : health?.status === 'healthy'
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900/60'
                    : 'bg-rose-950/60 text-rose-300 border-rose-500/40 hover:bg-rose-900/60'
                }`}
                onClick={onRefreshHealth}
                title="Click to refresh backend status"
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    healthLoading
                      ? 'bg-slate-400 animate-ping'
                      : health?.status === 'healthy'
                      ? 'bg-emerald-400 shadow-[0_0_8px_#10B981] animate-pulse'
                      : 'bg-rose-400 shadow-[0_0_8px_#EF4444]'
                  }`}
                />
                <span className="hidden sm:inline">
                  {healthLoading
                    ? 'Checking API...'
                    : health?.status === 'healthy'
                    ? 'Backend Online'
                    : 'Backend Disconnected'}
                </span>
                <RefreshCw
                  className={`w-3 h-3 text-slate-400 group-hover:text-slate-200 transition-colors ${
                    healthLoading ? 'animate-spin' : ''
                  }`}
                />
              </div>

              {/* Subsystems Dropdown on Hover */}
              {health && (
                <div className="absolute right-0 mt-2 w-72 p-3.5 bg-[#0D1B2E] rounded-xl shadow-2xl border border-[#1E3A5F] text-xs hidden group-hover:block transition-all z-50">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#1E3A5F]">
                    <span className="font-bold text-[#F8FAFC]">System Subsystems</span>
                    <span className="text-[10px] text-[#22D3EE] font-mono">v{health.version}</span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 flex items-center gap-1.5">
                        <Cpu className="w-3.5 h-3.5 text-[#22D3EE]" />
                        Gemini AI:
                      </span>
                      <span
                        className={`font-semibold ${
                          health.gemini_configured ? 'text-emerald-400' : 'text-amber-400'
                        }`}
                      >
                        {health.gemini_configured ? health.gemini_model : 'Not configured'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-blue-400" />
                        Safe Browsing:
                      </span>
                      <span
                        className={`font-semibold ${
                          health.safe_browsing_configured ? 'text-emerald-400' : 'text-slate-500'
                        }`}
                      >
                        {health.safe_browsing_configured ? 'Active (v5 API)' : 'Unconfigured'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-blue-400" />
                        Tesseract OCR:
                      </span>
                      <span
                        className={`font-semibold ${
                          health.tesseract_available ? 'text-emerald-400' : 'text-slate-500'
                        }`}
                      >
                        {health.tesseract_available ? 'Available' : 'Disabled / Missing'}
                      </span>
                    </div>
                  </div>
                  <p className="mt-2.5 pt-2 border-t border-[#1E3A5F]/70 text-[10px] text-slate-500">
                    Local active session • Zero database persistence
                  </p>
                </div>
              )}
            </div>

            {/* Launch Scanner CTA */}
            <button
              onClick={() => onNavigate('scanner')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-cyan-500 text-white text-xs sm:text-sm font-semibold shadow-md shadow-blue-600/30 hover:shadow-cyan-500/30 transition-all cursor-pointer"
            >
              Scan Advertisement
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
