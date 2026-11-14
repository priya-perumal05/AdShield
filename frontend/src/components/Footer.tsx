import { Shield, Lock, Cpu, Eye } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[#050B18] text-slate-400 mt-20 border-t border-[#1E3A5F]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand Col */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
                <Shield className="w-4 h-4 stroke-[2.2]" />
              </div>
              <span className="font-extrabold text-lg text-[#F8FAFC] tracking-tight">
                Ad<span className="text-[#22D3EE]">Shield</span>
              </span>
            </div>
            <p className="text-sm text-slate-400 max-w-md leading-relaxed">
              AdShield is an AI-powered detection system built to identify fraudulent, deceptive,
              and manipulative digital advertisements before they harm consumers.
            </p>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0D1B2E] border border-[#1E3A5F]">
                <Lock className="w-3.5 h-3.5 text-[#22D3EE]" />
                Zero-Persistence Privacy
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0D1B2E] border border-[#1E3A5F]">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                Gemini Multi-Modal
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0D1B2E] border border-[#1E3A5F]">
                <Eye className="w-3.5 h-3.5 text-[#22D3EE]" />
                OCR Text Analysis
              </span>
            </div>
          </div>

          {/* Threat Vector Scopes */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#F8FAFC] mb-3">
              Protected Vectors
            </h4>
            <ul className="space-y-2 text-xs text-slate-400">
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                <span>Unrealistic Discounts & Flash Sales</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                <span>Fake Celebrity Endorsements</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                <span>Phishing URLs & Obfuscated Domains</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                <span>Fabricated Tech Support Alerts</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                <span>Urgent Cryptocurrency Giveaways</span>
              </li>
            </ul>
          </div>

          {/* AI Disclaimer */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#F8FAFC] mb-3">
              Detection Disclaimer
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed bg-[#0D1B2E]/50 p-3 rounded-xl border border-[#1E3A5F]">
              Risk scores are AI-assisted estimates calculated from NLP patterns, OCR, and domain
              reputation signals. They provide actionable intelligence and should be supplemented by
              independent verification.
            </p>
          </div>
        </div>

        <div className="pt-8 border-t border-[#1E3A5F] flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <p>© {new Date().getFullYear()} AdShield. Built for consumer digital safety.</p>
          <div className="flex items-center gap-6">
            <span className="text-slate-400 font-mono">FastAPI • React • TypeScript • Gemini AI</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
