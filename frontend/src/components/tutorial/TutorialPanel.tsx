/**
 * TutorialPanel - Displays contextual help and guides for each workflow stage
 */

import { useState, useCallback } from 'react';
import { useSettingsStore } from '../../stores/settingsStore';
import type {
  StageTutorial,
  TutorialSection,
  TermDefinition,
} from '../../content/tutorials';

interface TutorialPanelProps {
  tutorial: StageTutorial;
  stageId: string;
}

export function TutorialPanel({ tutorial, stageId }: TutorialPanelProps) {
  const { tutorialMode, dismissTutorial, dismissedTutorials } = useSettingsStore();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['0']));
  const [showQuickStart, setShowQuickStart] = useState(true);
  const [activeTab, setActiveTab] = useState<'guide' | 'glossary' | 'tips'>('guide');

  const isDismissed = dismissedTutorials.includes(stageId);

  const toggleSection = useCallback((index: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  // Don't render if tutorial mode is off or this tutorial is dismissed
  if (!tutorialMode || isDismissed) {
    return null;
  }

  // Collect all terminology from this tutorial
  const allTerms: TermDefinition[] = [];
  const seenTerms = new Set<string>();
  tutorial.sections.forEach((section) => {
    section.terminology?.forEach((term) => {
      if (!seenTerms.has(term.term.toLowerCase())) {
        seenTerms.add(term.term.toLowerCase());
        allTerms.push(term);
      }
    });
  });
  allTerms.sort((a, b) => a.term.localeCompare(b.term));

  // Collect all tips
  const allTips: string[] = [];
  tutorial.sections.forEach((section) => {
    section.tips?.forEach((tip) => allTips.push(tip));
  });

  // Collect all warnings
  const allWarnings: string[] = [];
  tutorial.sections.forEach((section) => {
    section.warnings?.forEach((warning) => allWarnings.push(warning));
  });

  return (
    <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/20 border border-indigo-700/40 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-indigo-700/30">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600/30 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{tutorial.title}</h3>
              <p className="text-sm text-indigo-300">Tutorial Mode</p>
            </div>
          </div>
          <button
            onClick={() => dismissTutorial(stageId)}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700/50 rounded transition-colors"
            title="Dismiss tutorial for this stage"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Introduction */}
        <p className="mt-3 text-sm text-gray-300 leading-relaxed">
          {tutorial.introduction}
        </p>

        {/* Tabs */}
        <div className="flex gap-1 mt-4 p-1 bg-gray-800/50 rounded-lg">
          <button
            onClick={() => setActiveTab('guide')}
            className={`flex-1 py-1.5 px-3 text-xs font-medium rounded transition-colors ${
              activeTab === 'guide'
                ? 'bg-indigo-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
            }`}
          >
            Step-by-Step
          </button>
          <button
            onClick={() => setActiveTab('glossary')}
            className={`flex-1 py-1.5 px-3 text-xs font-medium rounded transition-colors ${
              activeTab === 'glossary'
                ? 'bg-indigo-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
            }`}
          >
            Glossary ({allTerms.length})
          </button>
          <button
            onClick={() => setActiveTab('tips')}
            className={`flex-1 py-1.5 px-3 text-xs font-medium rounded transition-colors ${
              activeTab === 'tips'
                ? 'bg-indigo-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
            }`}
          >
            Tips & Issues
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-h-96 overflow-y-auto">
        {activeTab === 'guide' && (
          <div className="p-4 space-y-4">
            {/* Quick Start */}
            {tutorial.quickStart.length > 0 && (
              <div className="p-3 bg-green-900/20 border border-green-700/30 rounded-lg">
                <button
                  onClick={() => setShowQuickStart(!showQuickStart)}
                  className="flex items-center justify-between w-full text-left"
                >
                  <div className="flex items-center gap-2">
                    <svg
                      className="w-4 h-4 text-green-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                    <span className="text-sm font-medium text-green-400">Quick Start</span>
                  </div>
                  <svg
                    className={`w-4 h-4 text-green-400 transition-transform ${
                      showQuickStart ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
                {showQuickStart && (
                  <ol className="mt-3 space-y-2">
                    {tutorial.quickStart.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                        <span className="flex-shrink-0 w-5 h-5 bg-green-600/30 text-green-400 rounded-full flex items-center justify-center text-xs font-medium">
                          {i + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}

            {/* Sections */}
            {tutorial.sections.map((section, index) => (
              <SectionCard
                key={index}
                section={section}
                index={String(index)}
                isExpanded={expandedSections.has(String(index))}
                onToggle={toggleSection}
              />
            ))}
          </div>
        )}

        {activeTab === 'glossary' && (
          <div className="p-4">
            <div className="space-y-3">
              {allTerms.map((term, i) => (
                <TermCard key={i} term={term} />
              ))}
              {allTerms.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4">
                  No terminology defined for this stage.
                </p>
              )}
            </div>
          </div>
        )}

        {activeTab === 'tips' && (
          <div className="p-4 space-y-4">
            {/* Tips */}
            {allTips.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-indigo-300 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                  Pro Tips
                </h4>
                <ul className="space-y-2">
                  {allTips.map((tip, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-gray-300 pl-2 border-l-2 border-indigo-600/50"
                    >
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings */}
            {allWarnings.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-amber-400 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  Important Notes
                </h4>
                <ul className="space-y-2">
                  {allWarnings.map((warning, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-amber-200/80 pl-2 border-l-2 border-amber-600/50"
                    >
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Common Issues */}
            {tutorial.commonIssues && tutorial.commonIssues.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-red-300 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                    />
                  </svg>
                  Troubleshooting
                </h4>
                <div className="space-y-3">
                  {tutorial.commonIssues.map((issue, i) => (
                    <div key={i} className="p-2 bg-gray-800/50 rounded border border-gray-700/50">
                      <p className="text-sm font-medium text-red-300">
                        {issue.problem}
                      </p>
                      <p className="text-sm text-gray-400 mt-1">
                        <span className="text-green-400">Fix:</span> {issue.solution}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-indigo-700/30 bg-gray-900/30">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Tutorial Mode is ON</span>
          <button
            onClick={() => dismissTutorial(stageId)}
            className="text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Hide for this stage
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function SectionCard({
  section,
  index,
  isExpanded,
  onToggle,
}: {
  section: TutorialSection;
  index: string;
  isExpanded: boolean;
  onToggle: (index: string) => void;
}) {
  return (
    <div className="border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => onToggle(index)}
        className="w-full p-3 flex items-center justify-between text-left bg-gray-800/30 hover:bg-gray-800/50 transition-colors"
      >
        <span className="text-sm font-medium text-white">{section.title}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-3 space-y-4 bg-gray-900/20">
          {/* Content */}
          <p className="text-sm text-gray-300">{section.content}</p>

          {/* Steps */}
          {section.steps && section.steps.length > 0 && (
            <div className="space-y-3">
              {section.steps.map((step, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-indigo-600/30 text-indigo-400 rounded-full flex items-center justify-center text-xs font-bold">
                    {i + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{step.title}</p>
                    <p className="text-sm text-gray-400 mt-0.5">{step.description}</p>
                    {step.tip && (
                      <p className="text-xs text-indigo-400 mt-1 flex items-center gap-1">
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        {step.tip}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Inline Terminology */}
          {section.terminology && section.terminology.length > 0 && (
            <div className="pt-3 border-t border-gray-700/50">
              <h5 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Key Terms
              </h5>
              <div className="grid gap-2">
                {section.terminology.slice(0, 4).map((term, i) => (
                  <div key={i} className="text-xs">
                    <span className="font-medium text-indigo-300">{term.term}:</span>{' '}
                    <span className="text-gray-400">{term.definition}</span>
                  </div>
                ))}
                {section.terminology.length > 4 && (
                  <p className="text-xs text-gray-500">
                    +{section.terminology.length - 4} more terms in Glossary tab
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TermCard({ term }: { term: TermDefinition }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-2 flex items-center justify-between text-left bg-gray-800/30 hover:bg-gray-800/50 transition-colors"
      >
        <span className="text-sm font-medium text-indigo-300">{term.term}</span>
        <svg
          className={`w-3 h-3 text-gray-400 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-2 bg-gray-900/20 space-y-2">
          <p className="text-sm text-gray-300">{term.definition}</p>
          {term.example && (
            <p className="text-xs text-gray-500">
              <span className="text-gray-400">Example:</span> {term.example}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
