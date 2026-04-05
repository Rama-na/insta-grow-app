/**
 * Displays LLM-generated insights from Azure AI agentaura.
 * Shows three sections when available:
 *   1. Baseline flow analysis
 *   2. Optimisation explanation
 *   3. Next-steps recommendations
 */
import { Bot, Lightbulb, ListChecks, FlaskConical } from 'lucide-react'

interface Props {
  baselineAnalysis?: string | null
  optimizationAnalysis?: string | null
  nextSteps?: string | null
}

function InsightBlock({
  icon,
  title,
  text,
  accent = 'blue',
}: {
  icon: React.ReactNode
  title: string
  text: string
  accent?: 'blue' | 'purple' | 'teal'
}) {
  const colours = {
    blue:   'border-blue-800 bg-blue-950/40 text-blue-300',
    purple: 'border-purple-800 bg-purple-950/40 text-purple-300',
    teal:   'border-teal-800 bg-teal-950/40 text-teal-300',
  }
  return (
    <div className={`rounded-xl border p-4 ${colours[accent]}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="opacity-80">{icon}</span>
        <span className="text-xs font-semibold uppercase tracking-wide opacity-80">{title}</span>
        <span className="ml-auto">
          <span className="badge-blue text-[10px]">AI · agentaura</span>
        </span>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">{text}</p>
    </div>
  )
}

export default function AIInsightPanel({ baselineAnalysis, optimizationAnalysis, nextSteps }: Props) {
  const hasAny = baselineAnalysis || optimizationAnalysis || nextSteps
  if (!hasAny) return null

  return (
    <div className="space-y-3">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <Bot size={15} className="text-blue-400" />
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
          AI Engineering Analysis
        </h3>
        <div className="flex-1 h-px bg-slate-800 ml-2" />
      </div>

      {/* Baseline flow analysis */}
      {baselineAnalysis && (
        <InsightBlock
          icon={<FlaskConical size={14} />}
          title="Baseline Flow Analysis"
          text={baselineAnalysis}
          accent="blue"
        />
      )}

      {/* Optimisation explanation */}
      {optimizationAnalysis && (
        <InsightBlock
          icon={<Lightbulb size={14} />}
          title="Why the Optimisation Worked"
          text={optimizationAnalysis}
          accent="purple"
        />
      )}

      {/* Next steps */}
      {nextSteps && (
        <InsightBlock
          icon={<ListChecks size={14} />}
          title="Further Recommendations"
          text={nextSteps}
          accent="teal"
        />
      )}
    </div>
  )
}
