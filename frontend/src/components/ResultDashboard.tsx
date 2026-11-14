import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Image as ImageIcon,
  Globe,
  CheckCircle2,
  HelpCircle,
  ExternalLink,
  Info
} from 'lucide-react';
import type { AnalysisResultUnion, RiskCategory } from '../types';
import { RiskBadge } from './RiskBadge';

interface ResultDashboardProps {
  result: AnalysisResultUnion;
  onReset: () => void;
}

export const ResultDashboard: React.FC<ResultDashboardProps> = ({ result, onReset }) => {
  const { type } = result;

  const assessment =
    type === 'text'
      ? result.data.risk_assessment
      : type === 'image'
      ? result.data.risk_assessment
      : result.data.risk_assessment;

  const score = assessment.risk_score;
  const category = assessment.risk_category;

  const isFallback = Boolean(result.data.fallback_used);
  const rawModel = result.data.model_used;

  const formatModelDisplayName = (model?: string | null) => {
    if (!model) return 'Gemini';
    const clean = model.replace(/^models\//, '');
    if (clean.includes('3.5-flash-lite')) return 'Gemini 3.5 Flash-Lite';
    if (clean.includes('3.1-flash-lite')) return 'Gemini 3.1 Flash-Lite';
    if (clean.includes('2.5-flash-lite')) return 'Gemini 2.5 Flash-Lite';
    if (clean.includes('3.5-flash')) return 'Gemini 3.5 Flash';
    if (clean.includes('3.8-flash')) return 'Gemini 3.8 Flash';
    return clean;
  };

  const activeModelDisplay = formatModelDisplayName(rawModel);

  // Determine score color styles
  const getScoreColor = (cat: RiskCategory) => {
    switch (cat) {
      case 'Low':
        return {
          text: 'text-emerald-400',
          stroke: '#10B981',
          bg: 'bg-emerald-500',
          lightBg: 'bg-emerald-950/40',
          border: 'border-emerald-500/40',
          glow: 'drop-shadow(0 0 8px rgba(16, 185, 129, 0.6))',
        };
      case 'Medium':
        return {
          text: 'text-amber-400',
          stroke: '#F59E0B',
          bg: 'bg-amber-500',
          lightBg: 'bg-amber-950/40',
          border: 'border-amber-500/40',
          glow: 'drop-shadow(0 0 8px rgba(245, 158, 11, 0.6))',
        };
      case 'High':
        return {
          text: 'text-rose-400',
          stroke: '#EF4444',
          bg: 'bg-rose-500',
          lightBg: 'bg-rose-950/40',
          border: 'border-rose-500/40',
          glow: 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.6))',
        };
      case 'Insufficient Data':
      default:
        return {
          text: 'text-slate-400',
          stroke: '#64748B',
          bg: 'bg-slate-500',
          lightBg: 'bg-slate-900/40',
          border: 'border-slate-700',
          glow: 'none',
        };
    }
  };

  const style = getScoreColor(category);

  return (
    <div className="space-y-6">
      {/* Top Banner & Risk Score Card */}
      <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] shadow-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-[#1E3A5F]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase font-bold tracking-wider text-[#22D3EE]">
                Analysis Report
              </span>
              <span className="text-xs text-slate-600">•</span>
              <span className="text-xs font-mono text-slate-400">
                {type === 'text'
                  ? result.data.id
                  : type === 'image'
                  ? result.data.id
                  : result.data.id}
              </span>
            </div>
            <h2 className="text-2xl font-bold text-[#F8FAFC] tracking-tight flex flex-wrap items-center gap-2.5">
              {type === 'text' && <FileText className="w-6 h-6 text-[#22D3EE]" />}
              {type === 'image' && <ImageIcon className="w-6 h-6 text-[#22D3EE]" />}
              {type === 'url' && <Globe className="w-6 h-6 text-[#22D3EE]" />}
              <span>
                {type === 'text'
                  ? 'Text Advertisement Evaluation'
                  : type === 'image'
                  ? 'Image & Visual Deception Audit'
                  : 'URL & Destination Security Audit'}
              </span>
              {result.data.gemini_used && result.data.model_used && (
                <span
                  className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border inline-flex items-center gap-1.5 ${
                    isFallback
                      ? 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                      : 'bg-blue-950/70 text-blue-300 border-blue-500/40'
                  }`}
                >
                  {isFallback && <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0" />}
                  <span>
                    {activeModelDisplay} – {isFallback ? 'Automatic Fallback' : 'Primary'}
                  </span>
                </span>
              )}
              {!result.data.gemini_used && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-950/70 text-amber-300 border border-amber-500/40">
                  {type === 'url' ? 'Safe Browsing & Heuristics' : 'Heuristic Rules Only'}
                </span>
              )}
              {assessment.assessment_status && (
                <span
                  className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                    assessment.assessment_status === 'COMPLETE'
                      ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                      : assessment.assessment_status === 'PARTIAL'
                      ? 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                      : 'bg-slate-900 text-slate-300 border-slate-700'
                  }`}
                >
                  {assessment.assessment_status === 'COMPLETE'
                    ? '✓ Complete Audit'
                    : assessment.assessment_status === 'PARTIAL'
                    ? '⚠ Partial Audit'
                    : '❓ Inconclusive'}
                </span>
              )}
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Evaluated with AdShield Multi-Vector AI Engine •{' '}
              {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onReset}
              className="px-4 py-2 text-sm font-semibold text-[#F8FAFC] hover:text-[#22D3EE] bg-[#11243A] hover:bg-[#1E3A5F] border border-[#1E3A5F] hover:border-[#22D3EE]/50 rounded-xl transition-all cursor-pointer shadow-xs"
            >
              Analyze Another Ad
            </button>
          </div>
        </div>

        {/* Automatic Fallback Notification Banner */}
        {result.data.gemini_used && isFallback && (
          <div className="mt-4 p-4 bg-amber-950/40 border border-amber-500/40 rounded-xl flex items-start gap-3 shadow-md">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <div className="font-bold text-amber-200">
                Primary AI model quota reached. Switched automatically to {activeModelDisplay}.
              </div>
              <p className="text-amber-300/90 leading-relaxed">
                {result.data.fallback_reason || 'Primary model quota was reached. AdShield seamlessly activated fallback model to ensure uninterrupted evaluation.'}
              </p>
              {result.data.models_attempted && result.data.models_attempted.length > 1 && (
                <div className="text-[11px] text-amber-400 font-mono pt-0.5">
                  Priority chain attempted: {result.data.models_attempted.map(m => formatModelDisplayName(m)).join(' → ')}
                </div>
              )}
            </div>
          </div>
        )}

        {/* All Models Unavailable Banner */}
        {!result.data.gemini_used && (
          <div className="mt-4 p-4 bg-[#11243A] border border-[#1E3A5F] rounded-xl flex items-start gap-3 shadow-md">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <div className="font-bold text-[#F8FAFC]">
                AI contextual analysis service temporarily unavailable
              </div>
              <p className="text-slate-400 leading-relaxed">
                {result.data.ai_error_message || 'All configured Gemini models are currently in cooldown or quota exhausted. Completed checks continue using automated heuristics, Tesseract OCR, and Google Safe Browsing threat intelligence.'}
              </p>
            </div>
          </div>
        )}

        {/* Score & Category Overview Block */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
          {/* Gauge Widget */}
          <div className="flex flex-col items-center justify-center p-6 rounded-xl bg-[#081426] border border-[#1E3A5F] text-center shadow-inner">
            <span className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-2">
              Overall Threat Score
            </span>
            <div className="relative w-36 h-36 flex items-center justify-center">
              {/* Circular Gauge SVG */}
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  stroke="#1E3A5F"
                  strokeWidth="8"
                  fill="transparent"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  stroke={style.stroke}
                  strokeWidth="8"
                  strokeDasharray={264}
                  strokeDashoffset={score !== null && score !== undefined ? 264 - (264 * score) / 100 : 264}
                  strokeLinecap="round"
                  fill="transparent"
                  style={{ filter: style.glow }}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                {score !== null && score !== undefined ? (
                  <>
                    <span className={`text-4xl font-extrabold ${style.text}`}>{score}</span>
                    <span className="text-[10px] text-slate-400 font-semibold uppercase -mt-1">
                      out of 100
                    </span>
                  </>
                ) : (
                  <>
                    <span className="text-2xl font-extrabold text-slate-400">N/A</span>
                    <span className="text-[9px] text-slate-400 font-semibold uppercase">
                      Inconclusive
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="mt-3">
              <RiskBadge category={category} size="lg" />
            </div>
            <p className="text-[11px] text-slate-400 mt-2">
              {category === 'Low' && 'Safe threshold (0–30)'}
              {category === 'Medium' && 'Suspicious threshold (31–60)'}
              {category === 'High' && 'Dangerous threshold (61–100)'}
              {category === 'Insufficient Data' && 'Unable to verify – insufficient security data'}
            </p>
          </div>

          {/* AI Explanation */}
          <div className="md:col-span-2 flex flex-col justify-between p-6 rounded-xl bg-[#081426] border border-[#1E3A5F] shadow-inner">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${type === 'url' && !result.data.gemini_used ? 'bg-amber-400' : 'bg-[#22D3EE] shadow-[0_0_6px_#22D3EE]'}`} />
                <h3 className="text-sm font-bold text-[#F8FAFC] uppercase tracking-wide">
                  {type === 'url' && !result.data.gemini_used
                    ? 'Security Threat Assessment Verdict (Safe Browsing & Heuristics)'
                    : 'AI Threat Assessment Verdict'}
                </h3>
              </div>

              {type === 'url' && !result.data.gemini_used && (
                <div className="mb-3 p-3 bg-amber-950/40 border border-amber-500/40 rounded-xl flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <span className="font-semibold text-amber-200 block">AI contextual analysis temporarily unavailable</span>
                    <span className="text-amber-300/80 block mt-0.5 leading-relaxed">
                      {result.data.ai_error_message || 'Gemini AI service was temporarily unavailable. Risk score evaluated using verified Google Safe Browsing and structural URL heuristics.'}
                    </span>
                  </div>
                </div>
              )}

              {assessment.summary && (
                <p className="text-sm font-semibold text-[#22D3EE] mb-2 pb-2 border-b border-[#1E3A5F]">
                  {assessment.summary}
                </p>
              )}
              <p className="text-sm text-slate-300 leading-relaxed font-normal">
                {assessment.explanation}
              </p>
            </div>

            {/* Recommendations preview */}
            <div className="mt-4 pt-4 border-t border-[#1E3A5F]">
              <span className="text-xs font-bold text-slate-300 block mb-2">
                Actionable Recommendations:
              </span>
              <ul className="space-y-1.5">
                {assessment.recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#22D3EE] flex-shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Verification Status & Security Coverage Strip */}
      <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] shadow-xl p-5 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#1E3A5F]">
          <div className="flex items-center gap-2.5">
            <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
              Audit Status:
            </span>
            <span
              className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                assessment.assessment_status === 'COMPLETE'
                  ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                  : assessment.assessment_status === 'PARTIAL'
                  ? 'bg-amber-950/70 text-amber-300 border-amber-500/40'
                  : 'bg-slate-900 text-slate-300 border-slate-700'
              }`}
            >
              {assessment.assessment_status === 'COMPLETE'
                ? '✓ COMPLETE AUDIT'
                : assessment.assessment_status === 'PARTIAL'
                ? '⚠ PARTIAL AUDIT'
                : '❓ INCONCLUSIVE / INSUFFICIENT DATA'}
            </span>
          </div>

          {assessment.assessment_status === 'INSUFFICIENT_DATA' && (
            <span className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
              Unable to verify – insufficient security data
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Completed Security Checks */}
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              Completed Security Checks ({assessment.checks_completed?.length || 0})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {(assessment.checks_completed && assessment.checks_completed.length > 0) ? (
                assessment.checks_completed.map((check, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-950/50 text-emerald-300 border border-emerald-500/30 font-medium text-[11px]"
                  >
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    <span>{check}</span>
                  </span>
                ))
              ) : (
                <span className="text-slate-500 italic">No automated checks completed.</span>
              )}
            </div>
          </div>

          {/* Unavailable / Skipped Checks */}
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              Unavailable Services ({assessment.checks_unavailable?.length || 0})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {(assessment.checks_unavailable && assessment.checks_unavailable.length > 0) ? (
                assessment.checks_unavailable.map((svc, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-950/50 text-amber-300 border border-amber-500/30 font-medium text-[11px]"
                  >
                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                    <span>{svc}</span>
                  </span>
                ))
              ) : (
                <span className="text-emerald-400 font-medium flex items-center gap-1 text-[11px]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  All security services active & responding.
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Submitted Details & Deep Findings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Submitted Content & Extracted Data */}
        <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] shadow-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-[#F8FAFC] uppercase tracking-wider flex items-center gap-2">
            <Info className="w-4 h-4 text-[#22D3EE]" />
            <span>Submitted Content & Extractions</span>
          </h3>

          {/* Text Tab Findings */}
          {type === 'text' && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-400">Submitted Copy:</label>
                <div className="mt-1 p-3.5 bg-[#081426] rounded-xl text-xs font-mono text-slate-300 max-h-48 overflow-y-auto border border-[#1E3A5F] whitespace-pre-wrap">
                  {result.data.submitted_text_preview}
                </div>
              </div>

              {result.data.findings.detected_claims.length > 0 && (
                <div>
                  <label className="text-xs font-semibold text-slate-400">
                    Detected Marketing Claims:
                  </label>
                  <ul className="mt-1 space-y-1">
                    {result.data.findings.detected_claims.map((c, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Image Tab Findings */}
          {type === 'image' && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 pb-2 border-b border-[#1E3A5F]">
                <span>File: <strong className="text-[#F8FAFC]">{result.data.filename}</strong></span>
                <span>Size: <strong className="text-[#F8FAFC]">{result.data.file_size_kb} KB</strong></span>
                <span className="flex items-center gap-1">
                  <span>OCR:</span>
                  {result.data.ocr_status === 'SUCCESS' ? (
                    <span className="font-semibold text-emerald-300 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                      SUCCESS {result.data.ocr_confidence ? `(${result.data.ocr_confidence}%)` : ''}
                    </span>
                  ) : result.data.ocr_status === 'NO_TEXT_DETECTED' ? (
                    <span className="font-semibold text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
                      NO TEXT
                    </span>
                  ) : result.data.ocr_status === 'UNAVAILABLE' ? (
                    <span className="font-semibold text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30">
                      UNAVAILABLE
                    </span>
                  ) : (
                    <span className="font-semibold text-slate-300">
                      {result.data.ocr_used ? 'Processed' : 'N/A'}
                    </span>
                  )}
                </span>
              </div>

              {result.imagePreviewUrl && (
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1 block">
                    Analyzed Graphic:
                  </label>
                  <div className="rounded-xl overflow-hidden border border-[#1E3A5F] max-h-56 bg-[#050B18] flex items-center justify-center shadow-md">
                    <img
                      src={result.imagePreviewUrl}
                      alt="Analyzed ad"
                      className="max-h-56 w-auto object-contain"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs font-semibold text-slate-400 flex items-center justify-between">
                  <span>Extracted OCR Text (Tesseract):</span>
                  <span className="text-[11px] text-[#22D3EE] font-mono">
                    {result.data.findings.ocr_word_count} words
                  </span>
                </label>
                <div className="mt-1 p-3 bg-[#081426] rounded-xl text-xs font-mono text-slate-300 max-h-36 overflow-y-auto border border-[#1E3A5F] whitespace-pre-wrap">
                  {result.data.findings.extracted_text || 'No legible text extracted via OCR.'}
                </div>
              </div>

              {/* Visual Observations */}
              {((result.data.image_analysis?.visual_observations && result.data.image_analysis.visual_observations.length > 0) ||
                (result.data.findings.visual_observations && result.data.findings.visual_observations.length > 0)) && (
                <div>
                  <label className="text-xs font-semibold text-slate-400 block mb-1">
                    Gemini Vision Visual Observations:
                  </label>
                  <ul className="space-y-1 bg-[#081426] p-3 rounded-xl border border-[#1E3A5F]">
                    {(result.data.image_analysis?.visual_observations || result.data.findings.visual_observations || []).map((obs, idx) => (
                      <li key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] mt-1.5 flex-shrink-0" />
                        <span>{obs}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.data.findings.ocr_vision_alignment && (
                <div className="p-2.5 bg-blue-950/40 rounded-lg border border-blue-500/30 text-[11px] text-blue-300">
                  <span className="font-semibold text-[#22D3EE]">OCR-Vision Cross-Verification: </span>
                  {result.data.findings.ocr_vision_alignment}
                </div>
              )}
            </div>
          )}

          {/* URL Tab Findings */}
          {type === 'url' && (
            <div className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-slate-400">Analyzed Destination URL:</label>
                <div className="mt-1 p-3 bg-[#081426] rounded-xl text-xs font-mono text-[#22D3EE] border border-[#1E3A5F] break-all flex items-center justify-between">
                  <span>{result.data.findings.normalized_url}</span>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-500 flex-shrink-0 ml-2" />
                </div>
              </div>

              {/* Domain & Network Breakdown */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-[#081426] rounded-xl border border-[#1E3A5F] space-y-1">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">
                    Target Domain / Host
                  </span>
                  <span className="font-semibold text-[#F8FAFC] break-all block">
                    {result.data.findings.domain}
                  </span>
                  {result.data.findings.is_punycode && result.data.findings.decoded_punycode && (
                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-amber-950/60 text-amber-300 border border-amber-500/30 font-mono">
                      Punycode: {result.data.findings.decoded_punycode}
                    </span>
                  )}
                  {result.data.findings.is_ip_address && (
                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-rose-950/60 text-rose-300 border border-rose-500/30 font-semibold">
                      Direct IP Host
                    </span>
                  )}
                </div>

                <div className="p-3 bg-[#081426] rounded-xl border border-[#1E3A5F] space-y-1">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">
                    Protocol & Port Security
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`font-semibold ${
                        result.data.findings.scheme === 'https'
                          ? 'text-emerald-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {result.data.findings.scheme.toUpperCase()}
                    </span>
                    {result.data.findings.port && (
                      <span className="text-slate-400 font-mono text-[10px]">
                        :{result.data.findings.port}
                      </span>
                    )}
                  </div>
                  {result.data.findings.is_url_shortener && (
                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-blue-950/60 text-blue-300 border border-blue-500/30 font-medium">
                      Link Shortener
                    </span>
                  )}
                  {result.data.findings.has_suspicious_tld && (
                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-amber-950/60 text-amber-300 border border-amber-500/30 font-medium">
                      High-Abuse TLD
                    </span>
                  )}
                </div>
              </div>

              {/* Safe Browsing v5 Status Card */}
              <div className="p-3.5 bg-[#081426] rounded-xl border border-[#1E3A5F] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#22D3EE]" />
                    <span>Google Safe Browsing v5:</span>
                  </span>
                  <div className="flex items-center gap-1.5">
                    {result.data.findings.cache_hit && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#11243A] text-slate-300 border border-[#1E3A5F] font-mono">
                        Cached TTL
                      </span>
                    )}
                    {result.data.findings.safe_browsing_status === 'MATCH_FOUND' ? (
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-500/40">
                        THREAT DETECTED
                      </span>
                    ) : result.data.findings.safe_browsing_status === 'NO_THREAT_FOUND' ? (
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
                        NO KNOWN THREATS
                      </span>
                    ) : result.data.findings.safe_browsing_status === 'UNAVAILABLE' ? (
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-500/40">
                        DATABASE UNAVAILABLE
                      </span>
                    ) : (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        UNCONFIGURED
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-300">
                  {result.data.findings.safe_browsing_verdict ||
                    (result.data.findings.safe_browsing_checked
                      ? 'No threat match found in Google Safe Browsing v5 registry.'
                      : 'Database check unconfigured (SAFE_BROWSING_API_KEY required in backend/.env).')}
                </p>

                {result.data.findings.threat_types && result.data.findings.threat_types.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {result.data.findings.threat_types.map((tt, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/40"
                      >
                        {tt}
                      </span>
                    ))}
                  </div>
                )}

                <p className="text-[10px] text-slate-500 italic">
                  Note: Evaluated against threat registries. A clean lookup does not guarantee complete absence of new zero-day threats.
                </p>
              </div>

              {/* AI Domain & Phishing Intelligence Card */}
              {result.data.url_analysis && (
                <div className="p-3 bg-[#081426] rounded-xl border border-[#1E3A5F] space-y-1.5 text-xs">
                  <span className="font-semibold text-slate-300 block">
                    AI Phishing & Domain Evaluation:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {result.data.url_analysis.is_brand_impersonation && (
                      <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-500/40 font-semibold text-[10px]">
                        Brand Impersonation {result.data.url_analysis.detected_brand ? `(${result.data.url_analysis.detected_brand})` : ''}
                      </span>
                    )}
                    {result.data.url_analysis.is_lookalike_domain && (
                      <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-500/40 font-semibold text-[10px]">
                        Lookalike / Typosquatted Domain
                      </span>
                    )}
                    {result.data.url_analysis.is_phishing_login && (
                      <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-500/40 font-semibold text-[10px]">
                        Fake Login / Credential Bait
                      </span>
                    )}
                    {result.data.url_analysis.is_suspicious_shortener && (
                      <span className="px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-500/40 font-semibold text-[10px]">
                        Obscured Redirection Shortener
                      </span>
                    )}
                  </div>
                  {result.data.url_analysis.ad_url_consistency && (
                    <p className="text-slate-400 text-[11px] pt-1">
                      <strong className="text-slate-300">Ad & Destination Alignment:</strong> {result.data.url_analysis.ad_url_consistency}
                    </p>
                  )}
                </div>
              )}

              {/* AI Unavailable Graceful Degradation Card */}
              {type === 'url' && !result.data.gemini_used && (
                <div className="p-3.5 bg-amber-950/30 rounded-xl border border-amber-500/40 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-amber-200 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                      <span>AI Contextual Analysis:</span>
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-900/80 text-amber-200 border border-amber-500/40">
                      {result.data.ai_status || 'TEMPORARILY UNAVAILABLE'}
                    </span>
                  </div>
                  <p className="text-amber-300/80 text-[11px] leading-relaxed">
                    {result.data.ai_error_message || 'AI contextual analysis was skipped or unavailable. Completed checks include URL normalization, security heuristics, and Google Safe Browsing threat lookup.'}
                  </p>
                  <div className="pt-1.5 border-t border-amber-500/20">
                    <span className="text-[10px] font-bold text-amber-200 uppercase tracking-wider block mb-1">
                      Completed Security Audits:
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-1 text-[11px] text-amber-300 font-medium">
                      <div className="flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        <span>URL Validation</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        <span>Security Heuristics</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        <span>Safe Browsing v5</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Suspicious Indicators & Red Flags */}
        <div className="bg-[#0D1B2E] rounded-2xl border border-[#1E3A5F] shadow-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#F8FAFC] uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <span>Flagged Suspicious Indicators</span>
            </h3>
            <span className="px-2.5 py-0.5 rounded-full bg-[#11243A] border border-[#1E3A5F] text-xs font-mono font-bold text-[#22D3EE]">
              {assessment.indicators.length} detected
            </span>
          </div>

          {assessment.indicators.length === 0 ? (
            <div
              className={`p-8 text-center rounded-xl border ${
                assessment.assessment_status === 'INSUFFICIENT_DATA'
                  ? 'bg-[#081426] border-[#1E3A5F]'
                  : 'bg-emerald-950/30 border-emerald-500/30'
              }`}
            >
              {assessment.assessment_status === 'INSUFFICIENT_DATA' ? (
                <>
                  <HelpCircle className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-300">Verification Inconclusive</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Insufficient security intelligence was available to verify this advertisement or destination.
                  </p>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-emerald-300">No High-Risk Patterns Flagged</p>
                  <p className="text-xs text-emerald-400/80 mt-1">
                    The advertisement content adheres to standard advertising norms without prominent fraud indicators.
                  </p>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {assessment.indicators.map((ind, i) => (
                <div
                  key={i}
                  className={`p-3.5 rounded-xl border text-xs space-y-1.5 transition-all ${
                    ind.severity === 'HIGH'
                      ? 'bg-rose-950/40 border-rose-500/40 text-rose-200'
                      : 'bg-amber-950/40 border-amber-500/40 text-amber-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold flex items-center gap-1.5 text-[#F8FAFC]">
                      <AlertTriangle
                        className={`w-3.5 h-3.5 ${
                          ind.severity === 'HIGH' ? 'text-rose-400' : 'text-amber-400'
                        }`}
                      />
                      {ind.title}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                        ind.severity === 'HIGH'
                          ? 'bg-rose-900/60 text-rose-300 border-rose-500/40'
                          : 'bg-amber-900/60 text-amber-300 border-amber-500/40'
                      }`}
                    >
                      {ind.severity}
                    </span>
                  </div>
                  <p className="text-slate-300 leading-relaxed font-normal">{ind.description}</p>
                  <div className="flex flex-wrap items-center justify-between gap-1 text-[10px] text-slate-400 pt-1.5 border-t border-white/5">
                    <span className="flex items-center gap-1.5">
                      <span>Category: <strong className="text-slate-300">{ind.category}</strong></span>
                      {ind.source && (
                        <>
                          <span>•</span>
                          <span className="px-1.5 py-0.2 rounded bg-[#11243A] text-[#22D3EE] font-mono text-[9px] border border-[#1E3A5F]">
                            {ind.source}
                          </span>
                        </>
                      )}
                    </span>
                    {ind.confidence !== null && ind.confidence !== undefined && (
                      <span className="font-mono">Confidence: {Math.round(ind.confidence * 100)}%</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Legal / AI disclaimer notice */}
          <div className="pt-3 border-t border-[#1E3A5F] flex items-start gap-2 text-[11px] text-slate-500">
            <HelpCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-500" />
            <p>{assessment.disclaimer}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
