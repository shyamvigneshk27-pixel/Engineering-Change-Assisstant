/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Hexagon, 
  Activity, 
  Box, 
  Layers, 
  ChevronRight, 
  Download, 
  FileText, 
  Cpu, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight,
  Clock,
  DollarSign,
  ShieldCheck,
  Search,
  ExternalLink
} from 'lucide-react';

// --- Types ---
type Phase = 'analysis' | 'cad' | 'architecture';

// --- Components ---

const CountUp = ({ end, duration = 600, suffix = "" }: { end: number | string, duration?: number, suffix?: string }) => {
  const [count, setCount] = useState(0);
  const target = typeof end === 'string' ? parseFloat(end.replace(/[^0-9.]/g, '')) : end;

  useEffect(() => {
    let startTime: number | null = null;
    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [target, duration]);

  return <span>{typeof end === 'string' && isNaN(target) ? end : `${count}${suffix}`}</span>;
};

const SidebarItem = ({ icon: Icon, label, active, onClick, delay }: { icon: any, label: string, active: boolean, onClick: () => void, delay: number }) => (
  <motion.button
    initial={{ x: -20, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ delay }}
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-6 py-4 text-left transition-all duration-200 border-l-2 ${
      active 
        ? 'bg-accent/5 border-accent text-accent' 
        : 'border-transparent text-text-muted hover:text-text-primary hover:bg-surface-2'
    }`}
  >
    <Icon size={18} className={active ? 'text-accent' : 'text-text-muted'} />
    <span className="font-sans font-semibold tracking-wider text-xs uppercase">{label}</span>
  </motion.button>
);

const MetricCard = ({ label, value, unit, color, delay }: { label: string, value: string | number, unit: string, color: string, delay: number }) => (
  <motion.div
    initial={{ y: 20, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ delay }}
    className="card p-4 flex flex-col justify-between"
  >
    <span className="label-muted">{label}</span>
    <div className="flex items-baseline gap-2 mt-2">
      <span className="text-4xl font-bold tracking-tighter" style={{ color }}>
        <CountUp end={value} />
      </span>
      <span className="label-muted lowercase">{unit}</span>
    </div>
  </motion.div>
);

const TableRow = ({ data, colors }: { data: string[], colors?: string[] }) => (
  <tr className="border-b border-border/50 hover:bg-surface-2 group transition-colors">
    {data.map((cell, i) => (
      <td key={i} className={`py-3 px-4 text-xs font-mono ${i === 0 ? 'border-l-2 border-transparent group-hover:border-accent' : ''}`}>
        {cell?.includes && (cell.includes('Broken') || cell.includes('MAJOR')) ? (
          <span className="px-2 py-0.5 bg-danger/10 text-danger rounded-full text-[10px] font-bold uppercase">{cell}</span>
        ) : cell?.includes && (cell.includes('Review') || cell.includes('amber')) ? (
          <span className="px-2 py-0.5 bg-warn/10 text-warn rounded-full text-[10px] font-bold uppercase">{cell}</span>
        ) : cell?.includes && (cell.includes('PASS') || cell.includes('MINOR')) ? (
          <span className="px-2 py-0.5 bg-success/10 text-success rounded-full text-[10px] font-bold uppercase">{cell}</span>
        ) : (
          <span className={colors?.[i] || 'text-text-primary'}>{cell}</span>
        )}
      </td>
    ))}
  </tr>
);

// --- Main App ---

export default function App() {
  const [phase, setPhase] = useState<Phase>('analysis');
  const [analyzing, setAnalyzing] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [ewrText, setEwrText] = useState("Reduce the wall thickness of the Valve Body by 2mm for weight reduction");
  const [resultData, setResultData] = useState<any>(null);
  const [showExhaustedModal, setShowExhaustedModal] = useState(false);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setShowResults(false);
    setShowExhaustedModal(false);
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ewrText })
      });
      
      if (res.status === 429) {
        setShowExhaustedModal(true);
        return;
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (err.error === "GEMINI_API_EXHAUSTED") {
          setShowExhaustedModal(true);
          return;
        }
        throw new Error("API Error");
      }

      const data = await res.json();
      setResultData(data);
      setShowResults(true);
    } catch (error) {
      console.error(error);
      alert("Failed to analyze. Gemini API may be rate limited (5 RPM). Try again in 60 seconds.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleChipClick = (text: string) => {
    setEwrText(text);
  };

  const aiParseData = resultData?.aiParse || [
    { label: "Affected Part", value: "PART-001 — Valve Body", conf: 98 },
    { label: "Parameter", value: "Wall Thickness", conf: 99 },
    { label: "Original Value", value: "12.00 mm", conf: 100 },
    { label: "New Value", value: "10.00 mm", conf: 100 },
    { label: "Delta", value: "-2.00 mm", conf: 100 },
    { label: "Delta%", value: "-16.67%", conf: 97 },
    { label: "Pressure Boundary", value: "YES", conf: 99 },
    { label: "Material Change", value: "NO", conf: 99 },
  ];

  const metricsData = resultData?.metrics || {
    assembliesAffected: 3,
    inspectionSteps: 5,
    documents: 17,
    effort: 80,
    revisionType: "MAJOR",
    revisionLabel: "B→C",
    safetyFactor: 3.07,
    safetyStatus: "PASS"
  };

  const assemblyImpactData = resultData?.assemblyImpact || [
    { assembly: "GV-ASSY-01", level: "L1", constraint: "Flange Interface", status: "Broken" },
    { assembly: "STACK-X-04", level: "L2", constraint: "Envelope Dim", status: "Review" },
    { assembly: "WELLHEAD-09", level: "L3", constraint: "None", status: "PASS" },
    { assembly: "SUBSEA-MOD", level: "L4", constraint: "None", status: "PASS" }
  ];

  const inspectionImpactData = resultData?.inspectionImpact || [
    { stepId: "INSP-001", keywordMatch: "Wall Thickness", actionRequired: "Update Tolerance", colors: ['text-accent', 'text-text-primary', 'text-warn'] },
    { stepId: "INSP-042", keywordMatch: "Hydrostatic", actionRequired: "Recalculate Pressure", colors: ['text-accent', 'text-text-primary', 'text-danger'] },
    { stepId: "INSP-088", keywordMatch: "Weight", actionRequired: "Update Mass Prop", colors: ['text-accent', 'text-text-primary', 'text-accent'] },
    { stepId: "INSP-102", keywordMatch: "UT Scan", actionRequired: "Review Path", colors: ['text-accent', 'text-text-primary', 'text-warn'] }
  ];

  const revisionRulesData = resultData?.revisionRules || [
    { id: "RULE-6D-01", desc: "Change in pressure-containing wall thickness exceeds 5% of nominal.", triggered: true },
    { id: "RULE-6D-04", desc: "Modification affects primary pressure boundary integrity.", triggered: true },
    { id: "RULE-ASME-09", desc: "Change in material specification or grade.", triggered: false },
    { id: "RULE-ASME-12", desc: "Welding procedure specification (WPS) update required.", triggered: false },
  ];

  const effortEstimateData = resultData?.effortEstimate || [
    { label: "CAD Modification & Drafting", hours: 24, total: 80, color: "var(--color-accent)" },
    { label: "FEA Structural Validation", hours: 16, total: 80, color: "var(--color-accent)" },
    { label: "Assembly Propagation Review", hours: 20, total: 80, color: "var(--color-accent)" },
    { label: "Inspection Plan Updates", hours: 8, total: 80, color: "var(--color-accent)" },
    { label: "Safety Multiplier (Pressure Boundary)", hours: 12, total: 80, color: "var(--color-danger)" },
  ];

  const barlowValidationData = resultData?.barlowValidation || {
    s: "75,000 PSI",
    tOriginal: "12.00 mm",
    tProposed: "10.00 mm",
    d: "150.00 mm",
    originalSf: 3.68,
    proposedSf: 3.07,
    status: "VALIDATION PASS"
  };

  const narrativeData = resultData?.narrative || "The proposed reduction of wall thickness from 12mm to 10mm for PART-001 (Valve Body) results in a 16.67% decrease in material volume, effectively reducing the total assembly weight by approximately 4.2kg. Structural validation using the Barlow formula confirms that the new design maintains a safety factor of 3.07, which remains well above the API 6D minimum requirement of 2.00 for the specified 5,000 PSI service pressure.\n\nHowever, this change is classified as a MAJOR revision due to its impact on the primary pressure boundary. Propagation analysis identifies three critical assembly interfaces that require immediate review: the main flange bolt-up pattern, the stack-up envelope for the Stark-X module, and the internal seal carrier alignment. Inspection plan INSP-042 must be updated to reflect the new hydrostatic test parameters.\n\nRecommendation: Proceed with the change request. The weight reduction benefits outweigh the engineering effort required for documentation updates. Ensure that all downstream STEP files are regenerated using the updated parametric model to prevent manufacturing discrepancies.";

  const documentRegisterData = resultData?.documentRegister || [
    { docId: "DWG-VALVE-001", title: "Main Assembly Drawing", status: "Review" },
    { docId: "SPEC-MAT-316", title: "Material Specification", status: "PASS" },
    { docId: "CALC-STR-042", title: "Structural Calculation Report", status: "Review" },
    { docId: "PROC-INSP-01", title: "General Inspection Procedure", status: "PASS" },
    { docId: "BOM-GV-001", title: "Bill of Materials", status: "Review" },
    { docId: "CERT-API-6D", title: "API 6D Compliance Certificate", status: "PASS" },
  ];

  return (
    <div className="min-h-screen flex bg-bg text-text-primary selection:bg-accent/30 selection:text-accent">
      <div className="scan-line" />
      
      {/* API Exhausted Modal */}
      <AnimatePresence>
        {showExhaustedModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowExhaustedModal(false)}
              className="absolute inset-0 bg-bg/80 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative w-full max-w-md bg-surface border border-danger/30 p-8 shadow-[0_0_50px_rgba(255,82,82,0.1)] rounded-sm"
            >
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-danger/10 rounded-full flex items-center justify-center mb-6">
                  <AlertTriangle className="text-danger" size={32} />
                </div>
                <h3 className="text-xl font-bold tracking-tighter mb-2 uppercase">Gemini API Exhausted</h3>
                <p className="text-text-muted text-sm leading-relaxed mb-8">
                  The AI has reached its rate limit (5 requests per minute). 
                  Please wait 60 seconds for the service to reset before initiating another analysis.
                </p>
                <div className="flex items-center gap-2 mb-8 text-[10px] font-mono text-danger/60 uppercase tracking-widest">
                  <Clock size={12} /> Cooling down...
                </div>
                <button 
                  onClick={() => setShowExhaustedModal(false)}
                  className="w-full py-3 bg-danger text-bg font-bold tracking-widest uppercase text-xs hover:bg-danger/90 transition-colors"
                >
                  ACKNOWLEDGE
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      
      {/* Sidebar */}
      <aside className="w-[220px] fixed top-0 left-0 h-full border-r border-border bg-surface z-50 flex flex-col sidebar-grid">
        <div className="p-8">
          <div className="flex items-center gap-2 text-accent">
            <Hexagon size={28} fill="currentColor" fillOpacity={0.2} />
            <span className="text-2xl font-bold tracking-tighter font-sans">ECA</span>
          </div>
          <div className="mt-1 font-mono text-[10px] text-text-muted tracking-widest uppercase">
            ENGINEERING CHANGE ASSISTANT
          </div>
          <div className="mt-1 font-mono text-[8px] text-text-muted/60 tracking-wider">
            STARK-X · SREC · SLB 2026
          </div>
        </div>

        <nav className="flex-1 mt-4">
          <SidebarItem 
            icon={Activity} 
            label="Phase 1 — Analysis" 
            active={phase === 'analysis'} 
            onClick={() => setPhase('analysis')} 
            delay={0.1}
          />
          <SidebarItem 
            icon={Box} 
            label="Phase 2 — CAD" 
            active={phase === 'cad'} 
            onClick={() => setPhase('cad')} 
            delay={0.2}
          />
          <SidebarItem 
            icon={Layers} 
            label="Phase 3 — Architecture" 
            active={phase === 'architecture'} 
            onClick={() => setPhase('architecture')} 
            delay={0.3}
          />
        </nav>

        <div className="p-6 border-t border-border bg-bg/50">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse shadow-[0_0_8px_#00E676]" />
            <span className="label-muted text-[9px]">System Ready</span>
          </div>
          <div className="space-y-1 mb-4">
            <div className="label-muted text-[8px] opacity-50">Mentors</div>
            <div className="text-[9px] text-text-muted font-mono">Dr. S. Rajini</div>
            <div className="text-[9px] text-text-muted font-mono">Dr. T. Kumaran</div>
          </div>
          <div className="font-mono text-[9px] text-text-muted/60">v1.0-PoC · Hackathon 2026</div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-[220px] min-h-screen flex flex-col">
        {/* Top Bar */}
        <header className="h-14 border-b border-border bg-surface/80 backdrop-blur-md sticky top-0 z-40 flex items-center justify-between px-8">
          <div className="flex items-center gap-2 text-[11px] font-mono tracking-wider">
            <span className="text-text-muted">EWR ANALYSIS</span>
            <ChevronRight size={12} className="text-text-muted" />
            <span className="text-accent">GATE VALVE — PART-001</span>
          </div>
          <div className="px-3 py-1 bg-accent/10 border border-accent/20 rounded-full text-[10px] font-bold text-accent tracking-widest uppercase">
            HACKATHON 2026 · SLB INDUSTRY PROBLEM
          </div>
          <div className="absolute bottom-0 left-0 w-full h-[1px] bg-accent/30" />
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-6xl mx-auto w-full space-y-8">
          <AnimatePresence mode="wait">
            {phase === 'analysis' && (
              <motion.div
                key="analysis"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-10"
              >
                {/* SECTION A: EWR INPUT */}
                <section className="card p-6 border-l-[3px] border-l-accent shadow-[0_0_20px_rgba(0,212,255,0.05)]">
                  <label className="label-muted mb-4 block">Engineering Work Request</label>
                  <textarea 
                    className="w-full bg-bg border border-border p-4 font-mono text-sm text-accent focus:outline-none focus:border-accent/50 min-h-[120px] resize-none"
                    value={ewrText}
                    onChange={(e) => setEwrText(e.target.value)}
                  />
                  
                  <div className="flex gap-3 mt-4 overflow-x-auto pb-2 no-scrollbar">
                    {[
                      { label: "Wall −2mm", text: "Reduce the wall thickness of the Valve Body by 2mm for weight reduction" },
                      { label: "SS316L swap", text: "Change material from Carbon Steel to SS316L for corrosion resistance" },
                      { label: "Stem +28mm", text: "Increase stem length by 28mm to accommodate new actuator interface" },
                      { label: "Mark update", text: "Update nameplate marking requirements to include API 6D monogram" },
                      { label: "OD tol.", text: "Tighten outer diameter tolerance from +/- 0.5mm to +/- 0.1mm" }
                    ].map((chip) => (
                      <button 
                        key={chip.label} 
                        onClick={() => handleChipClick(chip.text)}
                        className="flex-shrink-0 px-4 py-1.5 border border-border rounded-full text-[11px] font-mono text-text-muted hover:border-accent hover:text-accent hover:shadow-[0_0_10px_rgba(0,212,255,0.2)] transition-all"
                      >
                        {chip.label}
                      </button>
                    ))}
                  </div>

                  <button 
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="btn-primary w-full mt-6 shimmer flex items-center justify-center gap-2 relative overflow-hidden"
                  >
                    {analyzing ? (
                      <>
                        <div className="w-4 h-4 border-2 border-bg border-t-transparent rounded-full animate-spin" />
                        ANALYZING...
                      </>
                    ) : (
                      <>ANALYZE ENGINEERING CHANGE REQUEST <ArrowRight size={20} /></>
                    )}
                  </button>
                </section>

                {showResults && (
                  <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="space-y-12"
                  >
                    {/* SECTION B: AI PARSE */}
                    <section>
                      <h3 className="label-muted mb-4 flex items-center gap-2">
                        <Cpu size={14} className="text-accent" />
                        Gemini 2.5 Flash — Structured Extraction
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {aiParseData.map((field: any, i: number) => (
                          <div key={i} className="card p-3 bg-surface-2/50">
                            <div className="label-muted text-[9px] mb-1">{field.label}</div>
                            <div className="text-accent font-mono text-xs font-bold truncate">{field.value}</div>
                            <div className="mt-2 h-1 bg-border rounded-full overflow-hidden">
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${field.conf}%` }}
                                transition={{ delay: 0.5 + i * 0.05, duration: 0.8 }}
                                className="h-full bg-accent" 
                              />
                            </div>
                            <div className="mt-1 text-[8px] font-mono text-text-muted text-right">{field.conf}% CONF</div>
                          </div>
                        ))}
                      </div>
                    </section>

                    {/* SECTION C: IMPACT DASHBOARD */}
                    <section>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <MetricCard label="Assemblies Affected" value={metricsData.assembliesAffected} unit="items" color="var(--color-danger)" delay={0.1} />
                        <MetricCard label="Inspection Steps" value={metricsData.inspectionSteps} unit="steps" color="var(--color-warn)" delay={0.2} />
                        <MetricCard label="Documents" value={metricsData.documents} unit="files" color="var(--color-accent)" delay={0.3} />
                        <MetricCard label="Effort" value={metricsData.effort} unit="hours" color="var(--color-warn)" delay={0.4} />
                        <MetricCard label="Revision Type" value={metricsData.revisionType} unit="class" color="var(--color-danger)" delay={0.5} />
                        <MetricCard label="Revision Label" value={metricsData.revisionLabel} unit="rev" color="var(--color-accent)" delay={0.6} />
                        <MetricCard label="Safety Factor" value={metricsData.safetyFactor} unit="sf" color="var(--color-warn)" delay={0.7} />
                        <MetricCard label="Safety Status" value={metricsData.safetyStatus} unit="valid" color="var(--color-success)" delay={0.8} />
                      </div>
                    </section>

                    {/* SECTION D & E: TABLES */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                      <section>
                        <h3 className="font-sans font-semibold text-sm tracking-widest uppercase mb-4 flex items-center gap-2">
                          <span className="text-accent">[</span> ASSEMBLY IMPACT — 5-LAYER PROPAGATION <span className="text-accent">]</span>
                        </h3>
                        <div className="card overflow-hidden">
                          <table className="w-full text-left border-collapse">
                            <thead className="bg-surface-2 text-text-muted text-[10px] uppercase tracking-wider font-sans">
                              <tr>
                                <th className="py-3 px-4 font-semibold">Assembly</th>
                                <th className="py-3 px-4 font-semibold">Level</th>
                                <th className="py-3 px-4 font-semibold">Constraint</th>
                                <th className="py-3 px-4 font-semibold">Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {assemblyImpactData.map((row: any, i: number) => (
                                <TableRow key={i} data={[row.assembly, row.level, row.constraint, row.status]} />
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </section>

                      <section>
                        <h3 className="font-sans font-semibold text-sm tracking-widest uppercase mb-4 flex items-center gap-2">
                          <span className="text-accent">[</span> INSPECTION PLAN IMPACT <span className="text-accent">]</span>
                        </h3>
                        <div className="card overflow-hidden">
                          <table className="w-full text-left border-collapse">
                            <thead className="bg-surface-2 text-text-muted text-[10px] uppercase tracking-wider font-sans">
                              <tr>
                                <th className="py-3 px-4 font-semibold">Step ID</th>
                                <th className="py-3 px-4 font-semibold">Keyword Match</th>
                                <th className="py-3 px-4 font-semibold">Action Required</th>
                              </tr>
                            </thead>
                            <tbody>
                              {inspectionImpactData.map((row: any, i: number) => (
                                <TableRow key={i} data={[row.stepId, row.keywordMatch, row.actionRequired]} colors={row.colors || ['text-accent', 'text-text-primary', 'text-warn']} />
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </section>
                    </div>

                    {/* SECTION F: REVISION CLASSIFIER */}
                    <section>
                      <h3 className="font-sans font-semibold text-sm tracking-widest uppercase mb-4">
                        <span className="text-accent">[</span> REVISION CLASSIFICATION — ASME VIII / API 6D <span className="text-accent">]</span>
                      </h3>
                      <div className="space-y-3">
                        {revisionRulesData.map((rule: any, i: number) => (
                          <div key={i} className={`card p-4 flex items-center justify-between border-l-4 ${rule.triggered ? 'border-l-danger bg-danger/5' : 'border-l-border opacity-50'}`}>
                            <div className="flex flex-col gap-1">
                              <span className="font-mono text-[10px] text-text-muted">{rule.id}</span>
                              <span className="text-xs font-medium">{rule.desc}</span>
                            </div>
                            {rule.triggered && (
                              <span className="px-2 py-1 bg-danger text-bg text-[10px] font-bold rounded-sm">TRIGGERED</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </section>

                    {/* SECTION G: EFFORT ESTIMATE */}
                    <section>
                      <div className="flex justify-between items-end mb-4">
                        <h3 className="label-muted">Effort Estimate</h3>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-accent tracking-tighter font-sans">TOTAL: {metricsData.effort}h</div>
                        </div>
                      </div>
                      <div className="card p-6 space-y-6">
                        {effortEstimateData.map((item: any, i: number) => {
                           const total = metricsData.effort > 0 ? metricsData.effort : 80;
                           return (
                          <div key={i} className="space-y-2">
                            <div className="flex justify-between text-[11px] font-mono">
                              <span className="text-text-primary">{item.label}</span>
                              <span className="text-text-muted">{item.hours}h</span>
                            </div>
                            <div className="h-2 bg-border rounded-full overflow-hidden">
                              <motion.div 
                                initial={{ width: 0 }}
                                whileInView={{ width: `${(item.hours / total) * 100}%` }}
                                transition={{ duration: 1, ease: "easeOut" }}
                                className="h-full"
                                style={{ backgroundColor: item.color || "var(--color-accent)" }}
                              />
                            </div>
                          </div>
                        )})}
                      </div>
                    </section>

                    {/* SECTION H: BARLOW VALIDATION */}
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                      <div className="card p-8 flex flex-col justify-center items-center bg-surface-2/30">
                        <div className="label-muted mb-8">Barlow Formula Validation</div>
                        <div className="font-mono text-3xl tracking-tighter flex items-center gap-4">
                          <span className="text-accent">P_max</span>
                          <span>=</span>
                          <div className="flex flex-col items-center">
                            <div className="flex gap-2">
                              <span className="text-success">(2</span>
                              <span className="text-text-muted">×</span>
                              <span className="text-warn">S</span>
                              <span className="text-text-muted">×</span>
                              <span className="text-danger">t)</span>
                            </div>
                            <div className="w-full h-[2px] bg-text-muted my-1" />
                            <span className="text-accent">D</span>
                          </div>
                        </div>
                        <div className="mt-8 grid grid-cols-2 gap-x-12 gap-y-2 text-[10px] font-mono">
                          <div className="text-text-muted">S (Yield Strength)</div><div className="text-warn">{barlowValidationData.s}</div>
                          <div className="text-text-muted">t (Wall Thickness)</div><div className="text-danger">{barlowValidationData.tProposed}</div>
                          <div className="text-text-muted">D (Outer Diameter)</div><div className="text-accent">{barlowValidationData.d}</div>
                        </div>
                      </div>
                      <div className="flex flex-col gap-4">
                        <div className="card p-6 flex-1">
                          <div className="label-muted mb-4">Safety Comparison</div>
                          <div className="space-y-4">
                            <div className="flex justify-between items-center">
                              <span className="text-xs font-mono">Original ({barlowValidationData.tOriginal})</span>
                              <span className="text-xl font-bold text-success">{barlowValidationData.originalSf} SF</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-xs font-mono">Proposed ({barlowValidationData.tProposed})</span>
                              <span className="text-xl font-bold text-warn">{barlowValidationData.proposedSf} SF</span>
                            </div>
                            <div className="pt-4 border-t border-border flex justify-between items-center">
                              <span className="text-xs font-mono text-text-muted">API 6D Limit</span>
                              <span className="text-sm font-bold">2.00 SF</span>
                            </div>
                          </div>
                        </div>
                        <div className="bg-success/10 border-2 border-success p-4 rounded-sm flex items-center justify-center gap-3 shadow-[0_0_20px_rgba(0,230,118,0.2)]">
                          <ShieldCheck className="text-success" size={32} />
                          <span className="text-2xl font-bold text-success tracking-widest font-sans">{barlowValidationData.status}</span>
                        </div>
                      </div>
                    </section>

                    {/* SECTION I: AI NARRATIVE */}
                    <section className="card p-8 border-l-[3px] border-l-accent bg-surface-2/20 relative overflow-hidden">
                      <div className="label-muted mb-6">AI-Generated Impact Narrative</div>
                      <div className="space-y-4 font-mono text-[13px] leading-relaxed text-text-primary/90 max-w-3xl relative z-10 whitespace-pre-wrap">
                        {narrativeData}
                      </div>
                      <div className="absolute bottom-4 right-8 font-sans font-bold text-6xl text-text-muted/5 pointer-events-none tracking-tighter select-none">GEMINI 2.5 FLASH</div>
                    </section>

                    {/* SECTION J: DOCUMENT REGISTER */}
                    <section>
                      <div className="flex justify-between items-center mb-4">
                        <h3 className="label-muted">Document Register</h3>
                        <button className="text-[10px] font-mono text-accent hover:underline flex items-center gap-1">
                          12 more documents <ExternalLink size={10} />
                        </button>
                      </div>
                      <div className="card overflow-hidden">
                        <table className="w-full text-left border-collapse">
                          <thead className="bg-surface-2 text-text-muted text-[10px] uppercase tracking-wider font-sans">
                            <tr>
                              <th className="py-3 px-4 font-semibold">Doc ID</th>
                              <th className="py-3 px-4 font-semibold">Title</th>
                              <th className="py-3 px-4 font-semibold">Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {documentRegisterData.map((doc: any, i: number) => (
                              <TableRow key={i} data={[doc.docId, doc.title, doc.status]} />
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>

                    {/* SECTION K: SIGN-OFF */}
                    <section className="space-y-8">
                      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-surface p-6 border border-border rounded-sm">
                        <div className="flex items-center gap-3">
                          <FileText className="text-accent" />
                          <span className="font-sans font-bold text-sm tracking-widest uppercase">9-Section Change Impact Summary Report</span>
                        </div>
                        <div className="flex gap-4">
                          <button className="btn-outline flex items-center gap-2 text-xs">
                            <Download size={14} /> PDF REPORT
                          </button>
                          <button className="btn-outline flex items-center gap-2 text-xs">
                            <Download size={14} /> STEP FILES
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 border border-border">
                        <div className="p-8 border-r border-border flex flex-col gap-8">
                          <div className="label-muted">Prepared By</div>
                          <div className="flex flex-col gap-2">
                            <div className="font-mono text-xs italic text-accent/80">ECA — AI Assistant</div>
                            <div className="h-[1px] bg-text-muted/30 w-full" />
                            <div className="text-[9px] text-text-muted uppercase font-sans">Engineering Change Assistant</div>
                          </div>
                        </div>
                        <div className="p-8 border-r border-border flex flex-col gap-8">
                          <div className="label-muted">Reviewed By</div>
                          <div className="flex flex-col gap-2">
                            <div className="h-6" />
                            <div className="h-[1px] bg-text-muted/30 w-full" />
                            <div className="text-[9px] text-text-muted uppercase font-sans">Lead Engineer · SLB SREC</div>
                          </div>
                        </div>
                        <div className="p-8 flex flex-col gap-8">
                          <div className="label-muted">Approved By</div>
                          <div className="flex flex-col gap-2">
                            <div className="h-6" />
                            <div className="h-[1px] bg-text-muted/30 w-full" />
                            <div className="text-[9px] text-text-muted uppercase font-sans">Engineering Manager</div>
                          </div>
                        </div>
                      </div>
                    </section>
                  </motion.div>
                )}
              </motion.div>
            )}

            {phase === 'cad' && (
              <motion.div
                key="cad"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                className="space-y-8"
              >
                <header className="flex justify-between items-center">
                  <h2 className="text-2xl font-bold tracking-tighter font-sans uppercase">Parametric CAD Modification — CadQuery 2.4</h2>
                  <div className="flex gap-2">
                    <button className="btn-outline text-[10px] py-1 px-3">REGENERATE</button>
                    <button className="btn-outline text-[10px] py-1 px-3">EXPORT STEP</button>
                  </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-border border border-border">
                  {/* BEFORE PANEL */}
                  <div className="bg-surface p-8 flex flex-col items-center relative">
                    <div className="absolute top-4 left-4 label-muted text-accent">BEFORE</div>
                    <div className="w-full aspect-square max-w-[400px] flex items-center justify-center">
                      <svg viewBox="0 0 200 200" className="w-full h-full drop-shadow-[0_0_15px_rgba(59,139,212,0.2)]">
                        {/* Outer Body */}
                        <rect x="25" y="25" width="150" height="150" fill="none" stroke="#3B8BD4" strokeWidth="2" />
                        {/* Inner Bore */}
                        <rect x="37" y="37" width="126" height="126" fill="none" stroke="#3B8BD4" strokeWidth="2" strokeDasharray="4 2" />
                        {/* Dimension Lines */}
                        <g className="text-[6px] font-mono fill-text-muted">
                          <path d="M25 20 H175" stroke="currentColor" strokeWidth="0.5" />
                          <text x="100" y="15" textAnchor="middle">OD 150mm</text>
                          <path d="M37 185 H163" stroke="currentColor" strokeWidth="0.5" />
                          <text x="100" y="195" textAnchor="middle">ID 126mm</text>
                          {/* Wall thickness arrows */}
                          <path d="M25 100 H37" stroke="#3B8BD4" strokeWidth="1" markerEnd="url(#arrow)" markerStart="url(#arrow)" />
                          <text x="31" y="95" textAnchor="middle" className="fill-accent">12mm</text>
                          <path d="M163 100 H175" stroke="#3B8BD4" strokeWidth="1" markerEnd="url(#arrow)" markerStart="url(#arrow)" />
                          <text x="169" y="95" textAnchor="middle" className="fill-accent">12mm</text>
                        </g>
                        <defs>
                          <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3" markerHeight="3" orient="auto-start-reverse">
                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#3B8BD4" />
                          </marker>
                        </defs>
                      </svg>
                    </div>
                    <div className="mt-4 font-mono text-xs text-text-muted">OD 150mm · ID 126mm · Wall 12mm</div>
                  </div>

                  {/* AFTER PANEL */}
                  <div className="bg-surface p-8 flex flex-col items-center relative">
                    <div className="absolute top-4 left-4 label-muted text-success">AFTER</div>
                    <div className="absolute top-1/2 -left-4 -translate-y-1/2 z-10 w-8 h-8 bg-border rounded-full flex items-center justify-center border border-accent/50 text-accent">
                      <ArrowRight size={16} />
                    </div>
                    <div className="w-full aspect-square max-w-[400px] flex items-center justify-center">
                      <svg viewBox="0 0 200 200" className="w-full h-full drop-shadow-[0_0_15px_rgba(0,230,118,0.2)]">
                        {/* Delta Highlight */}
                        <rect x="35" y="35" width="130" height="130" fill="rgba(255,184,0,0.1)" />
                        {/* Outer Body */}
                        <rect x="25" y="25" width="150" height="150" fill="none" stroke="#00E676" strokeWidth="2" />
                        {/* Inner Bore */}
                        <rect x="35" y="35" width="130" height="130" fill="none" stroke="#00E676" strokeWidth="2" strokeDasharray="4 2" />
                        {/* Dimension Lines */}
                        <g className="text-[6px] font-mono fill-text-muted">
                          <path d="M25 20 H175" stroke="currentColor" strokeWidth="0.5" />
                          <text x="100" y="15" textAnchor="middle">OD 150mm</text>
                          <path d="M35 185 H165" stroke="currentColor" strokeWidth="0.5" />
                          <text x="100" y="195" textAnchor="middle" className="fill-success">ID 130mm</text>
                          {/* Wall thickness arrows */}
                          <path d="M25 100 H35" stroke="#00E676" strokeWidth="1" markerEnd="url(#arrow-g)" markerStart="url(#arrow-g)" />
                          <text x="30" y="95" textAnchor="middle" className="fill-success">10mm</text>
                          <path d="M165 100 H175" stroke="#00E676" strokeWidth="1" markerEnd="url(#arrow-g)" markerStart="url(#arrow-g)" />
                          <text x="170" y="95" textAnchor="middle" className="fill-success">10mm</text>
                        </g>
                        <defs>
                          <marker id="arrow-g" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3" markerHeight="3" orient="auto-start-reverse">
                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#00E676" />
                          </marker>
                        </defs>
                      </svg>
                    </div>
                    <div className="mt-4 font-mono text-xs text-text-muted">OD 150mm · ID 130mm · Wall 10mm</div>
                  </div>
                </div>

                <section className="card p-6">
                  <div className="label-muted mb-4">Barlow Validation Table</div>
                  <div className="overflow-hidden">
                    <table className="w-full text-left border-collapse">
                      <thead className="bg-surface-2 text-text-muted text-[10px] uppercase tracking-wider font-sans">
                        <tr>
                          <th className="py-3 px-4 font-semibold">Parameter</th>
                          <th className="py-3 px-4 font-semibold">Original</th>
                          <th className="py-3 px-4 font-semibold">Updated</th>
                          <th className="py-3 px-4 font-semibold">Delta</th>
                        </tr>
                      </thead>
                      <tbody>
                        <TableRow data={["Wall Thickness", "12.00 mm", "10.00 mm", "-2.00 mm"]} colors={['text-text-muted', 'text-text-primary', 'text-success', 'text-danger']} />
                        <TableRow data={["Inner Diameter", "126.00 mm", "130.00 mm", "+4.00 mm"]} colors={['text-text-muted', 'text-text-primary', 'text-success', 'text-warn']} />
                        <TableRow data={["Burst Pressure", "18,400 PSI", "15,333 PSI", "-3,067 PSI"]} colors={['text-text-muted', 'text-text-primary', 'text-warn', 'text-danger']} />
                        <TableRow data={["Safety Factor", "3.68", "3.07", "-0.61"]} colors={['text-text-muted', 'text-success', 'text-warn', 'text-danger']} />
                      </tbody>
                    </table>
                  </div>
                </section>

                <div className="flex flex-wrap gap-4">
                  <button className="btn-outline flex items-center gap-2 text-xs">
                    <Download size={14} /> PART-001_original.step
                  </button>
                  <button className="btn-outline flex items-center gap-2 text-xs">
                    <Download size={14} /> PART-001_updated.step
                  </button>
                  <button className="btn-outline flex items-center gap-2 text-xs">
                    <Download size={14} /> comparison_render.png
                  </button>
                </div>
              </motion.div>
            )}

            {phase === 'architecture' && (
              <motion.div
                key="architecture"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="space-y-8"
              >
                <header>
                  <h2 className="text-2xl font-bold tracking-tighter font-sans uppercase">Production System Architecture · 5 Layers · 29 Data Flows</h2>
                </header>

                <div className="card p-8 bg-surface-2/10 overflow-hidden relative">
                  <svg viewBox="0 0 800 600" className="w-full h-auto max-h-[600px]">
                    {/* Layer 1: INPUT */}
                    <g transform="translate(50, 50)">
                      <rect width="700" height="80" rx="4" fill="rgba(59, 139, 212, 0.05)" stroke="#3B8BD4" strokeWidth="1" />
                      <text x="10" y="-10" className="label-muted fill-[#3B8BD4]">Layer 1 — INPUT</text>
                      <g transform="translate(20, 20)">
                        {["Email / SAP", "Web Interface", "REST API", "SAP Workflow"].map((box, i) => (
                          <g key={i} transform={`translate(${i * 170}, 0)`}>
                            <rect width="150" height="40" rx="2" fill="#3B8BD4" fillOpacity="0.2" stroke="#3B8BD4" strokeWidth="1" />
                            <text x="75" y="25" textAnchor="middle" className="fill-text-primary font-sans text-[10px] font-bold uppercase tracking-wider">{box}</text>
                          </g>
                        ))}
                      </g>
                    </g>

                    {/* Layer 2: AI REASONING */}
                    <g transform="translate(50, 170)">
                      <rect width="700" height="80" rx="4" fill="rgba(127, 119, 221, 0.05)" stroke="#7F77DD" strokeWidth="1" />
                      <text x="10" y="-10" className="label-muted fill-[#7F77DD]">Layer 2 — AI REASONING</text>
                      <g transform="translate(20, 20)">
                        <g transform="translate(0, 0)">
                          <rect width="180" height="40" rx="2" fill="#7F77DD" fillOpacity="0.2" stroke="#7F77DD" strokeWidth="1" />
                          <text x="90" y="25" textAnchor="middle" className="fill-text-primary font-sans text-[10px] font-bold uppercase tracking-wider">Parts Database</text>
                        </g>
                        <g transform="translate(200, 0)">
                          <rect width="260" height="40" rx="2" fill="#7F77DD" fillOpacity="0.4" stroke="#7F77DD" strokeWidth="2" className="animate-pulse" />
                          <text x="130" y="25" textAnchor="middle" className="fill-accent font-sans text-[11px] font-bold uppercase tracking-widest">Gemini 2.5 Flash (NLP + Reasoning)</text>
                        </g>
                        <g transform="translate(480, 0)">
                          <rect width="180" height="40" rx="2" fill="#7F77DD" fillOpacity="0.2" stroke="#7F77DD" strokeWidth="1" />
                          <text x="90" y="25" textAnchor="middle" className="fill-text-primary font-sans text-[10px] font-bold uppercase tracking-wider">PDM Knowledge Graph</text>
                        </g>
                      </g>
                    </g>

                    {/* Layer 3: IMPACT ENGINE */}
                    <g transform="translate(50, 290)">
                      <rect width="700" height="80" rx="4" fill="rgba(29, 158, 117, 0.05)" stroke="#1D9E75" strokeWidth="1" />
                      <text x="10" y="-10" className="label-muted fill-[#1D9E75]">Layer 3 — IMPACT ENGINE</text>
                      <g transform="translate(20, 20)">
                        {["Part Resolver", "Assembly Graph", "Inspection Matcher", "BOM Analyzer", "Document Register"].map((box, i) => (
                          <g key={i} transform={`translate(${i * 135}, 0)`}>
                            <rect width="125" height="40" rx="2" fill="#1D9E75" fillOpacity="0.2" stroke="#1D9E75" strokeWidth="1" />
                            <text x="62" y="25" textAnchor="middle" className="fill-text-primary font-sans text-[9px] font-bold uppercase tracking-wider">{box}</text>
                          </g>
                        ))}
                      </g>
                    </g>

                    {/* Layer 4: CAD ENGINE */}
                    <g transform="translate(50, 410)">
                      <rect width="700" height="80" rx="4" fill="rgba(186, 117, 23, 0.05)" stroke="#BA7517" strokeWidth="1" />
                      <text x="10" y="-10" className="label-muted fill-[#BA7517]">Layer 4 — CAD ENGINE</text>
                      <g transform="translate(20, 20)">
                        {["CadQuery Builder", "Barlow Validator", "STEP Exporter", "Render"].map((box, i) => (
                          <g key={i} transform={`translate(${i * 170}, 0)`}>
                            <rect width="150" height="40" rx="2" fill="#BA7517" fillOpacity="0.2" stroke="#BA7517" strokeWidth="1" />
                            <text x="75" y="25" textAnchor="middle" className="fill-text-primary font-sans text-[10px] font-bold uppercase tracking-wider">{box}</text>
                          </g>
                        ))}
                      </g>
                    </g>

                    {/* Layer 5: OUTPUT */}
                    <g transform="translate(50, 530)">
                      <rect width="700" height="60" rx="4" fill="rgba(216, 90, 48, 0.05)" stroke="#D85A30" strokeWidth="1" />
                      <text x="10" y="-10" className="label-muted fill-[#D85A30]">Layer 5 — OUTPUT</text>
                      <g transform="translate(20, 10)">
                        {["PDF Report", "Web Dashboard", "STEP Files", "CAD Comparison", "Phase 3 Architecture"].map((box, i) => (
                          <g key={i} transform={`translate(${i * 135}, 0)`}>
                            <rect width="125" height="40" rx="2" fill="#D85A30" fillOpacity="0.2" stroke="#D85A30" strokeWidth="1" />
                            <text x="62" y="25" textAnchor="middle" className="fill-text-primary font-sans text-[9px] font-bold uppercase tracking-wider">{box}</text>
                          </g>
                        ))}
                      </g>
                    </g>

                    {/* Animated Connectors */}
                    <g className="connectors">
                      {[130, 250, 370, 490].map((y, i) => (
                        <g key={i}>
                          {[100, 250, 400, 550, 700].map((x, j) => (
                            <line 
                              key={j}
                              x1={x} y1={y} x2={x} y2={y + 40} 
                              stroke="#1E2733" 
                              strokeWidth="1" 
                              strokeDasharray="4 4"
                              className="animate-flow"
                            />
                          ))}
                        </g>
                      ))}
                    </g>
                  </svg>

                  <style>{`
                    @keyframes flow {
                      from { stroke-dashoffset: 8; }
                      to { stroke-dashoffset: 0; }
                    }
                    .animate-flow {
                      animation: flow 1.5s linear infinite;
                    }
                  `}</style>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <section className="card p-6">
                    <div className="label-muted mb-4">Technology Stack</div>
                    <div className="space-y-3 font-mono text-xs">
                      <div className="flex justify-between border-b border-border pb-2">
                        <span className="text-text-muted">AI Reasoning</span>
                        <span className="text-accent">Gemini 2.5 Flash</span>
                      </div>
                      <div className="flex justify-between border-b border-border pb-2">
                        <span className="text-text-muted">CAD Engine</span>
                        <span className="text-accent">CadQuery 2.4 (OpenCASCADE)</span>
                      </div>
                      <div className="flex justify-between border-b border-border pb-2">
                        <span className="text-text-muted">Backend</span>
                        <span className="text-accent">Python 3.11 / FastAPI</span>
                      </div>
                      <div className="flex justify-between border-b border-border pb-2">
                        <span className="text-text-muted">Data Store</span>
                        <span className="text-accent">Neo4j (Knowledge Graph)</span>
                      </div>
                      <div className="flex justify-between border-b border-border pb-2">
                        <span className="text-text-muted">Frontend</span>
                        <span className="text-accent">React 19 / Tailwind CSS</span>
                      </div>
                    </div>
                  </section>

                  <section className="card p-6 bg-success/5 border-success/20 flex flex-col justify-center items-center text-center">
                    <div className="label-muted mb-4">ROI Summary</div>
                    <div className="text-4xl font-bold text-success tracking-tighter font-sans mb-2">$720,000 / year saved</div>
                    <div className="text-lg font-bold text-text-primary tracking-widest uppercase">Payback &lt; 6 months</div>
                    <div className="mt-4 text-[10px] font-mono text-text-muted max-w-xs">
                      Based on 1,200 EWRs/year at an average reduction of 60 engineering hours per request.
                    </div>
                  </section>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer Spacer */}
        <div className="h-20" />
      </main>
    </div>
  );
}