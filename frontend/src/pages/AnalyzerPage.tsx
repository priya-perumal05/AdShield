import { useState, useRef } from 'react';
import {
  FileText,
  Image as ImageIcon,
  Globe,
  Upload,
  AlertCircle,
  Loader2,
  Sparkles,
  X,
  History,
  Trash2,
  CheckCircle,
  Cpu,
  ArrowRight
} from 'lucide-react';
import type {
  AnalysisResultUnion,
  SessionHistoryEntry,
  BackendHealth
} from '../types';
import { apiService, ApiError } from '../services/api';
import { ResultDashboard } from '../components/ResultDashboard';
import { RiskBadge } from '../components/RiskBadge';

interface AnalyzerPageProps {
  sessionHistory: SessionHistoryEntry[];
  onAddSessionItem: (item: SessionHistoryEntry) => void;
  onClearSession: () => void;
  health: BackendHealth | null;
}

const DEMO_HIGH_RISK: AnalysisResultUnion = {
  type: 'text',
  data: {
    id: 'adshield-scan-hr-88219',
    timestamp: new Date().toISOString(),
    submitted_text_preview: "CONGRATULATIONS! You have been selected as today's grand prize winner of an Apple iPhone 15 Pro Max! Click here immediately to claim your prize: http://free-iphone-claim.xyz/verify?id=992837. Only 2 items left! Confirm your shipping address and pay $1 fee now!",
    gemini_used: true,
    model_used: 'gemini-3.5-flash-lite',
    fallback_used: false,
    primary_model: 'gemini-3.5-flash-lite',
    risk_assessment: {
      risk_score: 88,
      risk_category: 'High',
      risk_level: 'HIGH_RISK',
      assessment_status: 'COMPLETE',
      checks_completed: [
        'Gemini AI NLP Analysis',
        'Linguistic Urgency Audit',
        'Suspicious URL Extraction',
        'Phishing Syntax Validation'
      ],
      checks_unavailable: [],
      summary: 'Critical Deception Indicators Detected in Promotional Advertisement Copy',
      explanation: 'The analyzed content demonstrates high-risk deceptive techniques including fabricated lottery winnings, artificial scarcity, high-risk unverified destination URL, and psychological urgency coercing sensitive identity and payment submission.',
      recommendations: [
        'Do not click the destination link or provide any personal shipping or financial credentials.',
        'Legitimate device manufacturers do not distribute hardware via unsolicited promotional messages.',
        'Block and report the advertising sender to digital safety registries.'
      ],
      disclaimer: 'AdShield threat scores are generated through multimodal AI intelligence and heuristic pattern engines.',
      indicators: [
        {
          category: 'Prize Scam',
          title: 'Fabricated Prize Winner Notification',
          description: 'The advertisement claims the recipient won an expensive flagship smartphone without entering an authentic verified sweepstakes.',
          severity: 'HIGH',
          source: 'Gemini NLP Reasoning',
          confidence: 0.96
        },
        {
          category: 'Urgency Exploitation',
          title: 'High-Pressure Scarcity Tactics',
          description: 'Uses panic cues ("immediately", "Only 2 items left!") to suppress critical evaluation and provoke hasty compliance.',
          severity: 'HIGH',
          source: 'Linguistic Engine',
          confidence: 0.92
        },
        {
          category: 'Suspicious Domain',
          title: 'High-Risk Destination URL Pattern',
          description: 'References an unverified .xyz domain with redirect and tracking query parameters typical of phishing collection pages.',
          severity: 'HIGH',
          source: 'URL Heuristics',
          confidence: 0.89
        }
      ]
    },
    findings: {
      detected_claims: [
        'Winner of Apple iPhone 15 Pro Max',
        'Only 2 items remaining in inventory',
        '$1 fee required to claim shipment'
      ],
      unrealistic_discounts: [],
      fake_prize_indicators: ['Grand prize winner', 'Free iPhone claim', '$1 processing fee'],
      misleading_statements: ['Selected as today’s grand prize winner'],
      urgency_cues: ['immediately', 'Only 2 items left', 'now!'],
      suspicious_patterns: ['Unsolicited prize bait', 'Low-friction payment lure ($1 fee)']
    }
  }
};

const DEMO_LOW_RISK: AnalysisResultUnion = {
  type: 'text',
  data: {
    id: 'adshield-scan-lr-12044',
    timestamp: new Date().toISOString(),
    submitted_text_preview: "Summer clearance sale at Nordstrom. Enjoy 20% off selected styles across womenswear and accessories. Free standard shipping on all qualifying orders over $89. Visit nordstrom.com or your nearest retail store.",
    gemini_used: true,
    model_used: 'gemini-3.5-flash-lite',
    fallback_used: false,
    primary_model: 'gemini-3.5-flash-lite',
    risk_assessment: {
      risk_score: 12,
      risk_category: 'Low',
      risk_level: 'LOW_RISK',
      assessment_status: 'COMPLETE',
      checks_completed: [
        'Gemini AI NLP Analysis',
        'Price Reasonability Check',
        'Domain Reputation Verification',
        'Brand Consistency Audit'
      ],
      checks_unavailable: [],
      summary: 'Legitimate Commercial Promotion with Standard Retail Terms',
      explanation: 'The promotional copy reflects standard commercial discount conventions (20% seasonal clearance) with transparent conditions, authentic merchant domain reference, and zero manipulative panic pressure.',
      recommendations: [
        'Ad copy appears consistent with legitimate commercial retail standards.',
        'Always ensure navigation directly through official verified merchant web domains.'
      ],
      disclaimer: 'AdShield threat scores are generated through multimodal AI intelligence and heuristic pattern engines.',
      indicators: []
    },
    findings: {
      detected_claims: [
        '20% off selected styles across womenswear and accessories',
        'Free standard shipping on qualifying orders over $89'
      ],
      unrealistic_discounts: [],
      fake_prize_indicators: [],
      misleading_statements: [],
      urgency_cues: [],
      suspicious_patterns: []
    }
  }
};

export const AnalyzerPage: React.FC<AnalyzerPageProps> = ({
  sessionHistory,
  onAddSessionItem,
  onClearSession,
  health,
}) => {
  const getInitialResult = (): AnalysisResultUnion | null => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const demo = params.get('demo');
      if (demo === 'high' || demo === 'high-risk') return DEMO_HIGH_RISK;
      if (demo === 'low' || demo === 'low-risk') return DEMO_LOW_RISK;
    }
    return null;
  };

  const [activeTab, setActiveTab] = useState<'text' | 'image' | 'url'>('text');

  // Text Tab State
  const [adText, setAdText] = useState('');
  const [sourceContext, setSourceContext] = useState('Social Media');

  // Image Tab State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // URL Tab State
  const [adUrl, setAdUrl] = useState('');
  const [urlAdText, setUrlAdText] = useState('');
  const [urlContext, setUrlContext] = useState('Social Media');

  // Execution & UI State
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [currentResult, setCurrentResult] = useState<AnalysisResultUnion | null>(getInitialResult);

  // Sample Loaders for Quick Evaluation
  const loadTextSample = (type: 'scam' | 'safe') => {
    setError(null);
    if (type === 'scam') {
      setAdText(
        "CONGRATULATIONS! You have been selected as today's grand prize winner of an Apple iPhone 15 Pro Max! Click here immediately to claim your prize: http://free-iphone-claim.xyz/verify?id=992837. Only 2 items left! Confirm your shipping address and pay $1 fee now!"
      );
      setSourceContext("SMS / WhatsApp");
    } else {
      setAdText(
        "Summer clearance sale at Nordstrom. Enjoy 20% off selected styles across womenswear and accessories. Free standard shipping on all qualifying orders over $89. Visit nordstrom.com or your nearest retail store."
      );
      setSourceContext("Social Media");
    }
  };

  const loadUrlSample = (type: 'scam' | 'safe') => {
    setError(null);
    if (type === 'scam') {
      setAdUrl('http://paypal-account-verification-alert.xyz/security-login');
      setUrlAdText('URGENT NOTICE: Your PayPal account has been temporarily restricted! Confirm identity immediately to prevent suspension.');
      setUrlContext('Email / SMS');
    } else {
      setAdUrl('https://www.apple.com/shop/buy-iphone');
      setUrlAdText('Buy iPhone 15 Pro Max directly from Apple with free delivery and special trade-in financing options.');
      setUrlContext('Official Website / Social Media');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setError('Please upload a valid image file (JPG, JPEG, PNG, or WEBP).');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('Image file size must be under 10 MB.');
        return;
      }
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setError(null);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setError('Please upload a valid image file (JPG, JPEG, PNG, or WEBP).');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('Image file size must be under 10 MB.');
        return;
      }
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
    }
  };

  const handleAnalyze = async () => {
    setError(null);

    // Frontend validations
    if (activeTab === 'text') {
      if (!adText.trim() || adText.trim().length < 5) {
        setError('Please enter advertisement text (at least 5 characters).');
        return;
      }
    } else if (activeTab === 'image') {
      if (!selectedFile) {
        setError('Please upload or drag an advertisement graphic to inspect.');
        return;
      }
    } else if (activeTab === 'url') {
      if (!adUrl.trim() || adUrl.trim().length < 4) {
        setError('Please enter a target advertisement URL.');
        return;
      }
    }

    setLoading(true);

    try {
      if (activeTab === 'text') {
        setLoadingStep('Evaluating text with Gemini NLP engine...');
        const res = await apiService.analyzeText({
          text: adText.trim(),
          source_context: sourceContext,
        });

        const resultObj: AnalysisResultUnion = { type: 'text', data: res };
        setCurrentResult(resultObj);

        // Store in session
        onAddSessionItem({
          id: res.id,
          type: 'text',
          title: adText.slice(0, 35) + '...',
          timestamp: new Date().toLocaleTimeString(),
          riskScore: res.risk_assessment.risk_score,
          riskCategory: res.risk_assessment.risk_category,
          result: resultObj,
        });
      } else if (activeTab === 'image') {
        setLoadingStep('Extracting OCR text and evaluating image visuals...');
        const res = await apiService.analyzeImage(selectedFile!, sourceContext);

        const resultObj: AnalysisResultUnion = {
          type: 'image',
          data: res,
          imagePreviewUrl: imagePreview || undefined,
        };
        setCurrentResult(resultObj);

        onAddSessionItem({
          id: res.id,
          type: 'image',
          title: res.filename,
          timestamp: new Date().toLocaleTimeString(),
          riskScore: res.risk_assessment.risk_score,
          riskCategory: res.risk_assessment.risk_category,
          result: resultObj,
        });
      } else if (activeTab === 'url') {
        setLoadingStep('Auditing URL structure, Safe Browsing v5, and phishing indicators...');
        const res = await apiService.analyzeUrl({
          url: adUrl.trim(),
          ad_text: urlAdText.trim() || undefined,
          source_context: urlContext,
        });

        const resultObj: AnalysisResultUnion = { type: 'url', data: res };
        setCurrentResult(resultObj);

        onAddSessionItem({
          id: res.id,
          type: 'url',
          title: res.findings.domain || adUrl.slice(0, 30),
          timestamp: new Date().toLocaleTimeString(),
          riskScore: res.risk_assessment.risk_score,
          riskCategory: res.risk_assessment.risk_category,
          result: resultObj,
        });
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred during analysis.');
      }
    } finally {
      setLoading(false);
      setLoadingStep('');
    }
  };

  const handleResetCurrent = () => {
    setCurrentResult(null);
    setError(null);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3A5F]">
        <div>
          <h1 className="text-3xl font-extrabold text-[#F8FAFC] tracking-tight">
            Advertisement Threat Scanner
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Choose an inspection vector below to analyze suspicious promotional content.
          </p>
        </div>

        {/* Ephemeral Session Notice */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0D1B2E] border border-[#1E3A5F] text-xs text-[#22D3EE]">
          <History className="w-3.5 h-3.5 text-[#22D3EE]" />
          <span>Session State Only • No Database Storage</span>
        </div>
      </div>

      {/* Backend API status alert if not configured */}
      {health && !health.gemini_configured && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs sm:text-sm flex items-start gap-3 shadow-md">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold text-amber-100">Gemini API Key Required For Live AI Analysis</p>
            <p className="text-xs text-amber-300/90 leading-relaxed">
              The backend is running, but <code className="bg-amber-900/60 text-amber-200 px-1.5 py-0.5 rounded border border-amber-600/40">GEMINI_API_KEY</code> is not configured in <code className="bg-amber-900/60 text-amber-200 px-1.5 py-0.5 rounded border border-amber-600/40">backend/.env</code>. Set your key to unlock deep neural text & vision scanning. URL heuristic checks remain operational.
            </p>
          </div>
        </div>
      )}

      {/* Main Analysis Section or Results View */}
      {currentResult ? (
        <ResultDashboard result={currentResult} onReset={handleResetCurrent} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Input Form (2 Cols) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] shadow-xl overflow-hidden">
              {/* Tab Selector */}
              <div className="flex border-b border-[#1E3A5F] bg-[#081426] p-1.5 gap-1.5">
                <button
                  onClick={() => {
                    setActiveTab('text');
                    setError(null);
                  }}
                  className={`flex-1 py-2.5 px-4 rounded-xl text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    activeTab === 'text'
                      ? 'bg-[#11243A] text-[#22D3EE] border border-[#1E3A5F] shadow-xs'
                      : 'text-slate-400 hover:text-[#F8FAFC] hover:bg-[#0D1B2E]/60'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Text Analysis</span>
                </button>
                <button
                  onClick={() => {
                    setActiveTab('image');
                    setError(null);
                  }}
                  className={`flex-1 py-2.5 px-4 rounded-xl text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    activeTab === 'image'
                      ? 'bg-[#11243A] text-[#22D3EE] border border-[#1E3A5F] shadow-xs'
                      : 'text-slate-400 hover:text-[#F8FAFC] hover:bg-[#0D1B2E]/60'
                  }`}
                >
                  <ImageIcon className="w-4 h-4" />
                  <span>Image Analysis</span>
                </button>
                <button
                  onClick={() => {
                    setActiveTab('url');
                    setError(null);
                  }}
                  className={`flex-1 py-2.5 px-4 rounded-xl text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    activeTab === 'url'
                      ? 'bg-[#11243A] text-[#22D3EE] border border-[#1E3A5F] shadow-xs'
                      : 'text-slate-400 hover:text-[#F8FAFC] hover:bg-[#0D1B2E]/60'
                  }`}
                >
                  <Globe className="w-4 h-4" />
                  <span>URL Security</span>
                </button>
              </div>

              {/* Tab 1: Text Content */}
              {activeTab === 'text' && (
                <div className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Paste Advertisement Copy
                    </label>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Quick tests:</span>
                      <button
                        onClick={() => loadTextSample('scam')}
                        className="text-xs font-medium text-rose-400 hover:text-rose-300 hover:underline cursor-pointer"
                      >
                        Sample Scam
                      </button>
                      <span className="text-slate-600">•</span>
                      <button
                        onClick={() => loadTextSample('safe')}
                        className="text-xs font-medium text-emerald-400 hover:text-emerald-300 hover:underline cursor-pointer"
                      >
                        Sample Legitimate
                      </button>
                    </div>
                  </div>

                  <textarea
                    rows={6}
                    value={adText}
                    onChange={(e) => setAdText(e.target.value)}
                    placeholder="Paste the sponsored ad headline, body copy, marketing email, or promotional SMS message here..."
                    className="w-full p-4 rounded-xl bg-[#081426] border border-[#1E3A5F] text-sm text-[#F8FAFC] placeholder-slate-500 focus:outline-none focus:border-[#22D3EE] focus:ring-1 focus:ring-[#22D3EE]/30 resize-none font-sans"
                  />

                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2">
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-semibold text-slate-400">Source Platform:</label>
                      <select
                        value={sourceContext}
                        onChange={(e) => setSourceContext(e.target.value)}
                        className="text-xs bg-[#081426] border border-[#1E3A5F] rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-[#22D3EE] text-slate-300"
                      >
                        <option value="Social Media">Social Media (FB / IG / X / TikTok)</option>
                        <option value="SMS / WhatsApp">SMS / WhatsApp / Messenger</option>
                        <option value="Search Engine Ad">Google / Bing Search Ad</option>
                        <option value="Website Banner">Website Display Banner</option>
                        <option value="Promotional Email">Promotional Email</option>
                      </select>
                    </div>
                    <span className="text-xs text-slate-500 font-mono">
                      {adText.length} characters
                    </span>
                  </div>
                </div>
              )}

              {/* Tab 2: Image Upload */}
              {activeTab === 'image' && (
                <div className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Upload Advertisement Graphic
                    </label>
                    <span className="text-xs text-slate-400">JPG, JPEG, PNG, WEBP (Max 10MB)</span>
                  </div>

                  <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                      imagePreview
                        ? 'border-[#22D3EE] bg-[#081426]/70 shadow-lg shadow-cyan-500/10'
                        : 'border-[#1E3A5F] hover:border-[#22D3EE]/50 hover:bg-[#081426]/50'
                    }`}
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept="image/jpeg,image/jpg,image/png,image/webp"
                      className="hidden"
                    />

                    {imagePreview ? (
                      <div className="space-y-4">
                        <div className="relative inline-block max-h-56 rounded-xl overflow-hidden shadow-2xl border border-[#1E3A5F] bg-[#050B18]">
                          <img
                            src={imagePreview}
                            alt="Ad Preview"
                            className="max-h-56 w-auto object-contain"
                          />
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedFile(null);
                              setImagePreview(null);
                            }}
                            className="absolute top-2 right-2 p-1.5 rounded-full bg-[#050B18]/80 text-white hover:bg-rose-600 transition-colors border border-white/20"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-300">
                          <strong>{selectedFile?.name}</strong> (
                          {Math.round((selectedFile?.size || 0) / 1024)} KB)
                        </p>
                        <p className="text-[11px] text-[#22D3EE]">
                          Click to select a different image
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="w-12 h-12 rounded-xl bg-[#11243A] border border-[#1E3A5F] text-[#22D3EE] flex items-center justify-center mx-auto">
                          <Upload className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-[#F8FAFC]">
                            Drop ad banner here, or <span className="text-[#22D3EE]">browse</span>
                          </p>
                          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                            AdShield will extract embedded text via Tesseract OCR and audit visual deceit with Gemini Vision.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 3: URL Target */}
              {activeTab === 'url' && (
                <div className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Destination / Landing Page URL
                    </label>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Quick tests:</span>
                      <button
                        onClick={() => loadUrlSample('scam')}
                        className="text-xs font-medium text-rose-400 hover:text-rose-300 hover:underline cursor-pointer"
                      >
                        Sample Phishing URL
                      </button>
                      <span className="text-slate-600">•</span>
                      <button
                        onClick={() => loadUrlSample('safe')}
                        className="text-xs font-medium text-emerald-400 hover:text-emerald-300 hover:underline cursor-pointer"
                      >
                        Sample Safe URL
                      </button>
                    </div>
                  </div>

                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                      <Globe className="w-4 h-4" />
                    </div>
                    <input
                      type="url"
                      value={adUrl}
                      onChange={(e) => setAdUrl(e.target.value)}
                      placeholder="https://example-promo-site.com/offer"
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#081426] border border-[#1E3A5F] text-sm text-[#F8FAFC] focus:outline-none focus:border-[#22D3EE] focus:ring-1 focus:ring-[#22D3EE]/30 font-mono"
                    />
                  </div>

                  {/* Accompanying Ad Copy (Optional Context) */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                    <div className="md:col-span-2 space-y-1">
                      <label className="text-xs font-semibold text-slate-400 block">
                        Associated Advertisement Copy <span className="text-slate-500 font-normal">(Optional context)</span>
                      </label>
                      <textarea
                        rows={2}
                        value={urlAdText}
                        onChange={(e) => setUrlAdText(e.target.value)}
                        placeholder="e.g. '50% off holiday sale! Click link to claim your promo code now!'"
                        className="w-full p-2.5 rounded-xl bg-[#081426] border border-[#1E3A5F] text-xs text-[#F8FAFC] placeholder-slate-500 focus:outline-none focus:border-[#22D3EE] resize-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-400 block">
                        Platform / Channel
                      </label>
                      <select
                        value={urlContext}
                        onChange={(e) => setUrlContext(e.target.value)}
                        className="w-full p-2.5 rounded-xl bg-[#081426] border border-[#1E3A5F] text-xs text-slate-300 focus:outline-none focus:border-[#22D3EE]"
                      >
                        <option value="Social Media">Social Media Feed</option>
                        <option value="Email / Newsletter">Email / Newsletter</option>
                        <option value="SMS / Messaging">SMS / Mobile Message</option>
                        <option value="Search Engine Ad">Search Engine Ad</option>
                        <option value="Display Network">Banner / Display Network</option>
                      </select>
                    </div>
                  </div>

                  <div className="p-3.5 bg-[#081426] rounded-xl border border-[#1E3A5F] text-xs text-slate-400 space-y-1.5">
                    <p className="font-semibold text-slate-300">Security Checks Performed:</p>
                    <p>• Google Safe Browsing v5 (urls:search) threat registry query</p>
                    <p>• SSRF protection (private IP / localhost rejection)</p>
                    <p>• Punycode & IDNA homograph character detection</p>
                    <p>• High-abuse TLDs, URL shorteners, and brand impersonation inspection</p>
                  </div>
                </div>
              )}

              {/* Error Alert Box */}
              {error && (
                <div className="mx-6 mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-200 text-xs flex items-start gap-2.5 shadow-md">
                  <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-rose-100">Analysis Warning: </span>
                    <span>{error}</span>
                  </div>
                </div>
              )}

              {/* Action Bar */}
              <div className="p-6 bg-[#081426]/80 border-t border-[#1E3A5F] flex flex-col sm:flex-row items-center justify-between gap-4">
                <span className="text-xs text-slate-400 text-center sm:text-left">
                  Powered by multi-modal AI reasoning and threat feeds.
                </span>

                <button
                  onClick={handleAnalyze}
                  disabled={loading}
                  className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3 rounded-xl text-white font-bold text-sm transition-all cursor-pointer ${
                    loading
                      ? 'bg-blue-600/50 cursor-not-allowed text-slate-300'
                      : 'bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 shadow-lg shadow-cyan-500/20'
                  }`}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-[#22D3EE]" />
                      <span>{loadingStep || 'Analyzing Advertisement...'}</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-[#22D3EE]" />
                      <span>Analyse Advertisement</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right Sidebar: Session History & Info (1 Col) */}
          <div className="space-y-6">
            <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] shadow-xl p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-[#22D3EE]" />
                  <h3 className="text-sm font-bold text-[#F8FAFC]">Current Session History</h3>
                </div>
                {sessionHistory.length > 0 && (
                  <button
                    onClick={onClearSession}
                    className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1 cursor-pointer transition-colors"
                    title="Clear session history"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear</span>
                  </button>
                )}
              </div>

              {sessionHistory.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500 space-y-2">
                  <Cpu className="w-8 h-8 text-slate-600 mx-auto" />
                  <p>No analyses performed yet in this browser session.</p>
                  <p className="text-[11px] text-slate-500">
                    Results remain ephemeral in frontend state only.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                  {sessionHistory.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => setCurrentResult(item.result)}
                      className="p-3 rounded-xl bg-[#081426] hover:bg-[#11243A] border border-[#1E3A5F] hover:border-[#22D3EE]/50 transition-all cursor-pointer space-y-1.5 group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-[#11243A] border border-[#1E3A5F] text-[#22D3EE]">
                          {item.type}
                        </span>
                        <RiskBadge category={item.riskCategory} score={item.riskScore} size="sm" />
                      </div>
                      <p className="text-xs font-semibold text-[#F8FAFC] group-hover:text-[#22D3EE] transition-colors truncate">
                        {item.title}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>{item.timestamp}</span>
                        <span className="text-[#22D3EE] font-semibold flex items-center gap-0.5">
                          View Details <ArrowRight className="w-2.5 h-2.5" />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Privacy Architecture Card */}
            <div className="bg-gradient-to-br from-[#081426] to-[#11243A] rounded-2xl border border-[#1E3A5F] p-5 text-xs text-slate-400 space-y-2 shadow-lg">
              <span className="font-bold text-[#F8FAFC] block flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-[#22D3EE]" />
                Zero-Knowledge Privacy Standard
              </span>
              <p className="leading-relaxed text-[11px] text-slate-400">
                AdShield stores no user records, logs, or advertiser content in permanent databases.
                All scans execute in isolated memory and disappear upon closing your browser.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
