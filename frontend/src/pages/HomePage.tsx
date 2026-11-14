import {
  FileText,
  Image as ImageIcon,
  Globe,
  Lock,
  CheckCircle,
  ArrowRight,
  TrendingDown,
  Gift,
  Clock,
  Sparkles,
  Shield,
  Activity,
  Zap,
} from 'lucide-react';
import type { BackendHealth } from '../types';

interface HomePageProps {
  onStartScanning: () => void;
  health: BackendHealth | null;
}

export const HomePage: React.FC<HomePageProps> = ({ onStartScanning, health }) => {
  return (
    <div className="space-y-20 pb-16">
      {/* Hero Section */}
      <section className="relative pt-12 sm:pt-20 pb-16 overflow-hidden">
        {/* Futuristic glowing ambient orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-blue-600/15 via-cyan-500/10 to-transparent pointer-events-none -z-10 rounded-full blur-3xl" />
        <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-blue-600/10 pointer-events-none -z-10 rounded-full blur-2xl" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-cyan-400/10 pointer-events-none -z-10 rounded-full blur-2xl" />

        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6">
          {/* Cyber Status Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#0D1B2E] border border-[#1E3A5F] text-[#22D3EE] text-xs font-semibold mb-8 shadow-md shadow-cyan-500/10">
            <Sparkles className="w-3.5 h-3.5 text-[#22D3EE]" />
            <span>Next-Gen Fake Advertisement Defense Engine</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] shadow-[0_0_6px_#22D3EE]" />
            <span className="text-slate-400 font-mono">v1.0</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-6xl font-extrabold text-[#F8FAFC] tracking-tight leading-tight sm:leading-none">
            Detect Fake Advertisements <br className="hidden sm:inline" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 via-cyan-400 to-blue-400">
              Before You Trust
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Protect yourself from misleading promotions, phishing advertisements and online scams with AI-powered multimodal intelligence.
          </p>

          {/* CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onStartScanning}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-bold text-base shadow-lg shadow-cyan-500/25 hover:shadow-cyan-400/35 transition-all cursor-pointer group"
            >
              <span>Get Started – Scan Ad</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="#threat-vectors"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-[#0D1B2E] hover:bg-[#11243A] text-[#F8FAFC] font-semibold text-base border border-[#1E3A5F] hover:border-[#22D3EE]/50 shadow-md transition-all"
            >
              Explore Threat Vectors
            </a>
          </div>

          {/* Interactive Cyber Radar Shield Visual */}
          <div className="mt-14 relative max-w-lg mx-auto">
            <div className="relative mx-auto w-48 h-48 rounded-full border border-[#1E3A5F] bg-[#081426]/80 flex items-center justify-center radar-sweep shadow-2xl shadow-blue-500/10">
              <div className="w-36 h-36 rounded-full border border-dashed border-[#22D3EE]/30 flex items-center justify-center">
                <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-blue-600 to-cyan-400/80 flex items-center justify-center text-white shadow-[0_0_30px_rgba(34,211,238,0.4)]">
                  <Shield className="w-12 h-12 stroke-[2.2]" />
                </div>
              </div>
              {/* Orbital Nodes */}
              <div className="absolute top-2 left-10 flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#0D1B2E] border border-[#1E3A5F] text-[10px] text-[#22D3EE] font-mono">
                <Zap className="w-2.5 h-2.5" /> NLP AI
              </div>
              <div className="absolute bottom-2 right-8 flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#0D1B2E] border border-[#1E3A5F] text-[10px] text-emerald-400 font-mono">
                <Activity className="w-2.5 h-2.5" /> OCR Vision
              </div>
              <div className="absolute top-1/2 -left-6 -translate-y-1/2 flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#0D1B2E] border border-[#1E3A5F] text-[10px] text-blue-400 font-mono">
                <Globe className="w-2.5 h-2.5" /> GSB v5
              </div>
            </div>
          </div>

          {/* Security Guarantees Bar */}
          <div className="mt-12 pt-8 border-t border-[#1E3A5F] grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
            <div className="p-3.5 bg-[#0D1B2E] rounded-xl border border-[#1E3A5F] shadow-xs">
              <span className="text-xs text-slate-400 font-medium block">Core Engine</span>
              <span className="text-sm font-bold text-[#F8FAFC]">
                {health?.gemini_configured ? health.gemini_model : 'Gemini Multi-Modal'}
              </span>
            </div>
            <div className="p-3.5 bg-[#0D1B2E] rounded-xl border border-[#1E3A5F] shadow-xs">
              <span className="text-xs text-slate-400 font-medium block">OCR Extraction</span>
              <span className="text-sm font-bold text-[#F8FAFC]">Tesseract Computer Vision</span>
            </div>
            <div className="p-3.5 bg-[#0D1B2E] rounded-xl border border-[#1E3A5F] shadow-xs">
              <span className="text-xs text-slate-400 font-medium block">Threat Feed</span>
              <span className="text-sm font-bold text-[#F8FAFC]">Google Safe Browsing v5</span>
            </div>
            <div className="p-3.5 bg-[#0D1B2E] rounded-xl border border-[#1E3A5F] shadow-xs">
              <span className="text-xs text-slate-400 font-medium block">Privacy Standard</span>
              <span className="text-sm font-bold text-emerald-400 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-emerald-400" /> Zero Storage
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 3 Core Analysis Vectors */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#22D3EE] mb-2">
            Multi-Vector Defense Architecture
          </h2>
          <h3 className="text-3xl font-extrabold text-[#F8FAFC] tracking-tight">
            How AdShield Evaluates Suspicious Ads
          </h3>
          <p className="mt-3 text-slate-400 text-sm leading-relaxed">
            Deceptive ads use layered tricks to bypass basic filters. AdShield cross-references
            visual cues, linguistic markers, and domain registries.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1: Text Analysis */}
          <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] p-8 shadow-lg hover:border-[#22D3EE]/50 hover:shadow-cyan-500/10 transition-all group flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#11243A] border border-[#1E3A5F] text-[#22D3EE] flex items-center justify-center mb-6 group-hover:scale-110 group-hover:border-[#22D3EE]/50 transition-all">
                <FileText className="w-6 h-6" />
              </div>
              <h4 className="text-xl font-bold text-[#F8FAFC] mb-2 group-hover:text-[#22D3EE] transition-colors">
                Text & NLP Analysis
              </h4>
              <p className="text-sm text-slate-400 leading-relaxed">
                Evaluates ad copy, social posts, and SMS promotions using Gemini AI. Detects
                unrealistic discounts, artificial urgency, fake lottery notifications, and deceptive
                guarantees.
              </p>
            </div>
            <ul className="mt-6 pt-4 border-t border-[#1E3A5F] space-y-2.5 text-xs text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Unrealistic price & discount checks
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Psychological urgency detection
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Language manipulation syntax scoring
              </li>
            </ul>
          </div>

          {/* Card 2: Image & Vision Analysis */}
          <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] p-8 shadow-lg hover:border-[#22D3EE]/50 hover:shadow-cyan-500/10 transition-all group flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#11243A] border border-[#1E3A5F] text-blue-400 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:border-blue-400/50 transition-all">
                <ImageIcon className="w-6 h-6" />
              </div>
              <h4 className="text-xl font-bold text-[#F8FAFC] mb-2 group-hover:text-[#22D3EE] transition-colors">
                Vision & OCR Engine
              </h4>
              <p className="text-sm text-slate-400 leading-relaxed">
                Extracts embedded typography via Tesseract OCR and performs deep visual audit with
                Gemini Vision to detect counterfeit logos, fake trust badges, and deceptive click
                traps.
              </p>
            </div>
            <ul className="mt-6 pt-4 border-t border-[#1E3A5F] space-y-2.5 text-xs text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Tesseract embedded text extraction
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Deceptive fake UI element detection
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Visual vs. textual intent alignment
              </li>
            </ul>
          </div>

          {/* Card 3: URL Analysis */}
          <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] p-8 shadow-lg hover:border-[#22D3EE]/50 hover:shadow-cyan-500/10 transition-all group flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#11243A] border border-[#1E3A5F] text-cyan-400 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:border-cyan-400/50 transition-all">
                <Globe className="w-6 h-6" />
              </div>
              <h4 className="text-xl font-bold text-[#F8FAFC] mb-2 group-hover:text-[#22D3EE] transition-colors">
                URL & Domain Integrity
              </h4>
              <p className="text-sm text-slate-400 leading-relaxed">
                Validates advertisement destination URLs against Google Safe Browsing threat lists
                and identifies typosquatting, deceptive subdomains, and suspicious top-level domains.
              </p>
            </div>
            <ul className="mt-6 pt-4 border-t border-[#1E3A5F] space-y-2.5 text-xs text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Google Safe Browsing v5 API check
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Typosquatting & brand spoofing alerts
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                Low-reputation TLD flagger
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Threat Vectors Spotlight */}
      <section id="threat-vectors" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-[#081426] rounded-3xl border border-[#1E3A5F] p-8 sm:p-12 text-[#F8FAFC] relative overflow-hidden shadow-2xl">
          <div className="relative z-10 max-w-3xl">
            <span className="text-xs uppercase font-bold tracking-widest text-[#22D3EE]">
              Threat Intelligence
            </span>
            <h3 className="text-2xl sm:text-4xl font-extrabold tracking-tight mt-2 mb-4">
              Common Scam Patterns Unmasked
            </h3>
            <p className="text-sm sm:text-base text-slate-300 mb-8 leading-relaxed">
              Cybercriminals invest millions into deceptive sponsored banners, search ads, and
              social feed promos. Here is what AdShield scans for every time:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-[#0D1B2E] border border-[#1E3A5F] flex items-start gap-3">
                <TrendingDown className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h5 className="font-bold text-sm text-[#F8FAFC]">Impossible Discounts</h5>
                  <p className="text-xs text-slate-400 mt-1">
                    "95% off designer watches for the next 15 minutes only!"
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0D1B2E] border border-[#1E3A5F] flex items-start gap-3">
                <Gift className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h5 className="font-bold text-sm text-[#F8FAFC]">Fake Prize & Lottery Bait</h5>
                  <p className="text-xs text-slate-400 mt-1">
                    "You won an iPhone 16! Pay $1 shipping to claim before time expires."
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0D1B2E] border border-[#1E3A5F] flex items-start gap-3">
                <Clock className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h5 className="font-bold text-sm text-[#F8FAFC]">Fabricated Panic Urgency</h5>
                  <p className="text-xs text-slate-400 mt-1">
                    "Your cloud account will be deleted in 2 hours unless you confirm billing."
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0D1B2E] border border-[#1E3A5F] flex items-start gap-3">
                <Globe className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h5 className="font-bold text-sm text-[#F8FAFC]">Lookalike Domains</h5>
                  <p className="text-xs text-slate-400 mt-1">
                    "paypal-security-auth-check.xyz instead of paypal.com"
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-8">
              <button
                onClick={onStartScanning}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold text-sm transition-all shadow-md shadow-cyan-500/20 cursor-pointer"
              >
                <span>Scan an Advertisement Now</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
