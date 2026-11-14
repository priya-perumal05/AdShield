import { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { HomePage } from './pages/HomePage';
import { AnalyzerPage } from './pages/AnalyzerPage';
import { ResultDashboard } from './components/ResultDashboard';
import { RiskBadge } from './components/RiskBadge';
import type { BackendHealth, SessionHistoryEntry, AnalysisResultUnion } from './types';
import { apiService } from './services/api';
import { Shield, History, Trash2, ArrowRight, ArrowLeft } from 'lucide-react';

export function App() {
  const getInitialTab = (): 'home' | 'scanner' | 'history' => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab');
      if (tabParam === 'scanner' || tabParam === 'history' || tabParam === 'home') {
        return tabParam;
      }
      if (window.location.hash === '#scanner') return 'scanner';
      if (window.location.hash === '#history') return 'history';
    }
    return 'home';
  };

  const [activeTab, setActiveTab] = useState<'home' | 'scanner' | 'history'>(getInitialTab);
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [sessionHistory, setSessionHistory] = useState<SessionHistoryEntry[]>([]);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<AnalysisResultUnion | null>(null);

  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const data = await apiService.checkHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const handleAddSessionItem = (item: SessionHistoryEntry) => {
    setSessionHistory((prev) => [item, ...prev]);
  };

  const handleClearSession = () => {
    setSessionHistory([]);
    setSelectedHistoryItem(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#050B18] text-[#F8FAFC] selection:bg-blue-600 selection:text-white cyber-grid">
      {/* Cybersecurity Top Navbar */}
      <Navbar
        health={health}
        healthLoading={healthLoading}
        onRefreshHealth={fetchHealth}
        activeTab={activeTab}
        onNavigate={(tab) => {
          setSelectedHistoryItem(null);
          setActiveTab(tab);
        }}
        sessionCount={sessionHistory.length}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeTab === 'home' && (
          <HomePage
            onStartScanning={() => setActiveTab('scanner')}
            health={health}
          />
        )}

        {activeTab === 'scanner' && (
          <AnalyzerPage
            sessionHistory={sessionHistory}
            onAddSessionItem={handleAddSessionItem}
            onClearSession={handleClearSession}
            health={health}
          />
        )}

        {activeTab === 'history' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3A5F]">
              <div>
                <h1 className="text-3xl font-extrabold text-[#F8FAFC] tracking-tight flex items-center gap-2.5">
                  <History className="w-7 h-7 text-[#22D3EE]" />
                  <span>Session Scan History</span>
                </h1>
                <p className="text-sm text-slate-400 mt-1">
                  Active browser session records. Cleared upon tab closure or manually below.
                </p>
              </div>

              {sessionHistory.length > 0 && (
                <button
                  onClick={handleClearSession}
                  className="px-4 py-2 rounded-xl bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-semibold flex items-center gap-2 border border-rose-500/40 transition-all cursor-pointer shadow-xs"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Clear All Session Scans</span>
                </button>
              )}
            </div>

            {selectedHistoryItem ? (
              <div className="space-y-4">
                <button
                  onClick={() => setSelectedHistoryItem(null)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-[#22D3EE] transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Session List</span>
                </button>
                <ResultDashboard
                  result={selectedHistoryItem}
                  onReset={() => setSelectedHistoryItem(null)}
                />
              </div>
            ) : sessionHistory.length === 0 ? (
              <div className="p-16 text-center bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] space-y-3">
                <Shield className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-base font-bold text-[#F8FAFC]">No Scans Recorded in Session</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                  Run an advertisement analysis using the Text, Image, or URL scanner to see threat breakdown cards here.
                </p>
                <button
                  onClick={() => setActiveTab('scanner')}
                  className="mt-2 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition-all cursor-pointer"
                >
                  Go to Ad Scanner
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sessionHistory.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setSelectedHistoryItem(item.result)}
                    className="p-5 rounded-2xl bg-[#0D1B2E] border border-[#1E3A5F] hover:border-[#22D3EE]/50 hover:shadow-lg hover:shadow-cyan-500/10 transition-all cursor-pointer flex flex-col justify-between space-y-4 group"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#11243A] border border-[#1E3A5F] text-[#22D3EE]">
                          {item.type}
                        </span>
                        <RiskBadge
                          category={item.riskCategory}
                          score={item.riskScore}
                          size="sm"
                        />
                      </div>
                      <h4 className="text-sm font-bold text-[#F8FAFC] group-hover:text-[#22D3EE] transition-colors truncate">
                        {item.title}
                      </h4>
                      <p className="text-xs text-slate-400 mt-1">
                        Scanned at {item.timestamp}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-[#1E3A5F] flex items-center justify-between text-xs text-[#22D3EE] font-semibold">
                      <span>View Full Breakdown</span>
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Cybersecurity Footer */}
      <Footer />
    </div>
  );
}

export default App;
