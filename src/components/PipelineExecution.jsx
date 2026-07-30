import React, { useState } from 'react';
import { PRESET_TARGETS, generateCustomTargetData, analyzeSnippets } from '../data/mockData';
import { getRecommendedSources } from '../data/sourceRecommender';
import ReportViewer from './ReportViewer';
import { Play, RotateCcw, CheckCircle2, Loader2, Network, Globe, BarChart3, FileText, ChevronRight, Search, Sparkles, Terminal, ShieldCheck, Compass, ExternalLink, Award } from 'lucide-react';

export default function PipelineExecution({ prompts, activeAgentId, setActiveAgentId, isRunning, setIsRunning }) {
  const [selectedPresetId, setSelectedPresetId] = useState('zomato');
  const [customInput, setCustomInput] = useState('');
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [logs, setLogs] = useState([]);
  const [executionData, setExecutionData] = useState(null);

  // Snippet Filters
  const [snippetFilter, setSnippetFilter] = useState('all');
  const [snippetSearch, setSnippetSearch] = useState('');

  const steps = [
    {
      id: 'orchestrator',
      title: 'Step 1: Pipeline Handoff',
      agent: 'The Orchestrator Agent',
      icon: Network,
      color: '#6366f1',
      desc: 'Orchestrator maps target to top Indian review portals and instructs Web Researcher.'
    },
    {
      id: 'researcher',
      title: 'Step 2: Indian OSINT Extraction',
      agent: 'The Web Researcher Agent',
      icon: Globe,
      color: '#10b981',
      desc: 'Extracting 200 verified reviews from MouthShut, Moneycontrol, CarWale, Flipkart & Gadgets360.'
    },
    {
      id: 'analyst',
      title: 'Step 3: Sentiment & Theme Analysis',
      agent: 'The Sentiment Analyst Agent',
      icon: BarChart3,
      color: '#06b6d4',
      desc: 'Scoring positive/neutral/negative percentage totals across all 200 Indian reviews (summing to 100%).'
    },
    {
      id: 'synthesizer',
      title: 'Step 4: Executive Report Synthesis',
      agent: 'The Report Writer Agent',
      icon: FileText,
      color: '#f59e0b',
      desc: 'Formatting structured Executive Markdown Customer Sentiment Report.'
    }
  ];

  const getTargetData = () => {
    if (customInput.trim()) {
      return generateCustomTargetData(customInput);
    }
    const preset = PRESET_TARGETS.find(p => p.id === selectedPresetId) || PRESET_TARGETS[0];
    const analysis = analyzeSnippets(preset.researcherData.snippets, preset.name);
    return {
      ...preset,
      analystData: {
        metrics: analysis.metrics,
        strengths: analysis.strengths,
        weaknesses: analysis.weaknesses
      },
      synthesizerData: {
        markdown: analysis.markdown
      },
      recommendedSources: getRecommendedSources(preset.name)
    };
  };

  const currentTarget = getTargetData();
  const recommendedMatrix = getRecommendedSources(currentTarget.name);

  // Filter snippets based on tab and search
  const filteredSnippets = currentTarget.researcherData.snippets.filter(s => {
    const matchesSentiment = snippetFilter === 'all' || s.sentiment === snippetFilter;
    const matchesSearch = !snippetSearch || s.text.toLowerCase().includes(snippetSearch.toLowerCase()) || s.category.toLowerCase().includes(snippetSearch.toLowerCase()) || s.source.toLowerCase().includes(snippetSearch.toLowerCase());
    return matchesSentiment && matchesSearch;
  });

  const addLog = (agentName, message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, agentName, message, type, id: Math.random() }]);
  };

  const handleStartPipeline = () => {
    if (isRunning) return;

    setIsRunning(true);
    setCurrentStepIndex(0);
    setActiveAgentId('orchestrator');
    setLogs([]);
    setExecutionData(null);

    const target = getTargetData();
    const recs = getRecommendedSources(target.name);

    // Log Step 1: Orchestrator
    addLog('Orchestrator', `Received target product request: "${target.name}".`);
    addLog('Orchestrator', `Querying Source Matrix Segment for "${target.name}" -> Category: ${recs.categoryName}.`);
    addLog('Orchestrator', `Selected Top Indian Sources: ${recs.bestSources.map(s => s.name).join(', ')}.`, 'action');
    addLog('Orchestrator', `Passing target name and source list to Web Researcher Agent...`, 'action');

    // Sequence execution timers
    setTimeout(() => {
      // Step 2: Web Researcher
      setCurrentStepIndex(1);
      setActiveAgentId('researcher');
      addLog('Web Researcher', `Scraping verified Indian platforms (${recs.bestSources.slice(0, 3).map(s => s.name).join(', ')})...`);
      addLog('Web Researcher', `Successfully extracted ${target.researcherData.sourcesCount} customer reviews with Indian regional context. Strict domain constraints satisfied.`, 'success');
      addLog('Orchestrator', `Received 200 raw reviews from Web Researcher. Handoff to Sentiment Analyst...`, 'action');
    }, 2200);

    setTimeout(() => {
      // Step 3: Sentiment Analyst
      setCurrentStepIndex(2);
      setActiveAgentId('analyst');
      addLog('Sentiment Analyst', `Analyzing sentiment distribution across all 200 feedback snippets...`);
      addLog('Sentiment Analyst', `Aggregate Sentiment Scores: ${target.analystData.metrics.positive}% Positive | ${target.analystData.metrics.neutral}% Neutral | ${target.analystData.metrics.negative}% Negative. Total = 100%.`, 'success');
      addLog('Sentiment Analyst', `Top Strengths Identified: "${target.analystData.strengths[0].theme}", "${target.analystData.strengths[1].theme}".`);
      addLog('Sentiment Analyst', `Top Weaknesses Identified: "${target.analystData.weaknesses[0].theme}", "${target.analystData.weaknesses[1].theme}".`);
      addLog('Orchestrator', `Received metrics payload from Sentiment Analyst. Handoff to Report Writer...`, 'action');
    }, 4500);

    setTimeout(() => {
      // Step 4: Report Writer / Synthesizer
      setCurrentStepIndex(3);
      setActiveAgentId('synthesizer');
      addLog('Report Writer', `Formatting final Executive Markdown Document for "${target.name}" adhering to strict template.`);
      addLog('Report Writer', `Customer Sentiment Report generated cleanly without conversational filler.`, 'success');
    }, 6800);

    setTimeout(() => {
      // Complete
      setIsRunning(false);
      setActiveAgentId(null);
      setCurrentStepIndex(4);
      setExecutionData(target);
      addLog('Orchestrator', `Pipeline execution completed cleanly. Returning formatted Markdown report to user.`, 'complete');
    }, 8500);
  };

  const handleSelectPreset = (id) => {
    if (isRunning) return;
    setSelectedPresetId(id);
    setCustomInput('');
  };

  return (
    <div className="pipeline-execution-container">
      {/* Target Selector Bar */}
      <div className="target-selection-card">
        <div className="selection-header">
          <div className="header-title">
            <Search size={18} />
            <span>Select Target Brand (India & Global)</span>
          </div>
          <span className="selection-sub">Pick a preset brand or type any custom brand name for instant source mapping & sentiment analysis</span>
        </div>

        <div className="presets-row">
          {PRESET_TARGETS.map(preset => (
            <button
              key={preset.id}
              className={`preset-chip ${selectedPresetId === preset.id && !customInput ? 'selected' : ''}`}
              onClick={() => handleSelectPreset(preset.id)}
              disabled={isRunning}
            >
              <img src={preset.logo} alt={preset.name} className="preset-logo" />
              <div className="preset-text">
                <span className="preset-name">{preset.name}</span>
                <span className="preset-cat">{preset.category}</span>
              </div>
            </button>
          ))}
        </div>

        <div className="custom-input-row">
          <div className="input-wrap">
            <Search className="input-search-icon" size={18} />
            <input
              type="text"
              placeholder="Or enter custom Indian/global brand (e.g., 'Swiggy', 'Blinkit', 'Mahindra XUV700', 'PostPe', 'boAt')..."
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              disabled={isRunning}
              className="custom-target-input"
            />
          </div>

          <button
            className={`run-pipeline-btn ${isRunning ? 'running' : ''}`}
            onClick={handleStartPipeline}
            disabled={isRunning}
          >
            {isRunning ? (
              <>
                <Loader2 size={18} className="spin-icon" />
                <span>Analyzing 200 Reviews...</span>
              </>
            ) : (
              <>
                <Play size={18} />
                <span>Execute Multi-Agent Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Target-to-Source Recommendation Matrix Card */}
      <div className="source-matrix-card">
        <div className="matrix-header">
          <div className="matrix-title">
            <Compass size={18} className="text-emerald-400" />
            <span>Optimal Source Recommendation Matrix</span>
            <span className="cat-tag">{recommendedMatrix.categoryName}</span>
          </div>
          <span className="matrix-subtitle">Product-to-Source Mapping Engine auto-recommends top Indian platforms for <strong>{currentTarget.name}</strong></span>
        </div>

        <div className="sources-grid">
          {recommendedMatrix.bestSources.map((src, idx) => (
            <div key={idx} className="source-item-card">
              <div className="source-item-top">
                <span className="source-name">{src.name}</span>
                {src.relevance && <span className="relevance-badge">{src.relevance} Match</span>}
              </div>
              <p className="source-rationale">{src.rationale}</p>
              <a href={src.url} target="_blank" rel="noreferrer" className="source-link">
                <span>View Domain</span>
                <ExternalLink size={12} />
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Execution Tracker Steps */}
      <div className="pipeline-tracker-row">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isCurrent = currentStepIndex === idx;
          const isDone = currentStepIndex > idx;

          return (
            <div
              key={step.id}
              className={`tracker-step-card ${isCurrent ? 'is-active' : ''} ${isDone ? 'is-done' : ''}`}
            >
              <div className="step-top-row">
                <div
                  className="step-icon-box"
                  style={{
                    background: isCurrent ? `${step.color}25` : isDone ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                    color: isCurrent ? step.color : isDone ? '#10b981' : '#64748b'
                  }}
                >
                  {isDone ? <CheckCircle2 size={20} /> : isCurrent ? <Loader2 size={20} className="spin-icon" /> : <Icon size={20} />}
                </div>
                <span className="step-idx-badge">{step.title}</span>
              </div>

              <h4>{step.agent.replace('The ', '')}</h4>
              <p className="step-desc">{step.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Execution Output split view */}
      <div className="execution-output-grid">
        {/* Terminal Live Stream */}
        <div className="terminal-card">
          <div className="terminal-header">
            <div className="terminal-title">
              <Terminal size={16} />
              <span>Multi-Agent Inter-Process Logs</span>
            </div>
            {isRunning && (
              <div className="streaming-badge">
                <span className="pulse-dot"></span>
                <span>Streaming Indian Reviews</span>
              </div>
            )}
          </div>

          <div className="terminal-logs-body">
            {logs.length === 0 ? (
              <div className="terminal-empty">
                <Sparkles size={24} className="text-slate-600 mb-2" />
                <p>Click "Execute Multi-Agent Pipeline" to observe Orchestrator and Worker agent log handoffs.</p>
              </div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className={`log-line type-${log.type}`}>
                  <span className="log-time">[{log.timestamp}]</span>
                  <span className="log-agent">{log.agentName}:</span>
                  <span className="log-msg">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Scraped Raw Snippets Inspector */}
        <div className="scraped-snippets-card">
          <div className="card-header-bar">
            <Globe size={18} className="text-emerald-400" />
            <h3>Web Researcher Indian OSINT Feedback</h3>
            <span className="snippets-count">{currentTarget.researcherData.snippets.length} Verified Snippets</span>
          </div>

          {/* Snippet Filter Controls */}
          <div className="snippet-controls-row">
            <div className="filter-pills">
              <button
                className={`filter-pill ${snippetFilter === 'all' ? 'active' : ''}`}
                onClick={() => setSnippetFilter('all')}
              >
                All ({currentTarget.researcherData.snippets.length})
              </button>
              <button
                className={`filter-pill ${snippetFilter === 'positive' ? 'active' : ''}`}
                onClick={() => setSnippetFilter('positive')}
              >
                Positive ({currentTarget.researcherData.snippets.filter(s => s.sentiment === 'positive').length})
              </button>
              <button
                className={`filter-pill ${snippetFilter === 'neutral' ? 'active' : ''}`}
                onClick={() => setSnippetFilter('neutral')}
              >
                Neutral ({currentTarget.researcherData.snippets.filter(s => s.sentiment === 'neutral').length})
              </button>
              <button
                className={`filter-pill ${snippetFilter === 'negative' ? 'active' : ''}`}
                onClick={() => setSnippetFilter('negative')}
              >
                Negative ({currentTarget.researcherData.snippets.filter(s => s.sentiment === 'negative').length})
              </button>
            </div>

            <input
              type="text"
              placeholder="Search inside 200 reviews..."
              value={snippetSearch}
              onChange={(e) => setSnippetSearch(e.target.value)}
              className="snippet-search-input"
            />
          </div>

          <div className="snippets-scroll-list">
            {filteredSnippets.length === 0 ? (
              <div className="text-center py-6 text-slate-500 font-mono text-xs">No reviews match current search filter.</div>
            ) : (
              filteredSnippets.map(snippet => (
                <div key={snippet.id} className="snippet-item-card">
                  <div className="snippet-top">
                    <span className="snippet-source">#{snippet.id} • {snippet.source}</span>
                    <span className="snippet-date">{snippet.date}</span>
                    <span className={`snippet-tag tag-${snippet.sentiment}`}>{snippet.sentiment}</span>
                  </div>
                  <p className="snippet-text">"{snippet.text}"</p>
                  <div className="snippet-cat-chip">{snippet.category}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Final Executive Report synthesis presentation */}
      {executionData && (
        <div className="final-report-section">
          <ReportViewer
            targetName={executionData.name}
            reportMarkdown={executionData.synthesizerData.markdown}
            analystMetrics={executionData.analystData.metrics}
            strengths={executionData.analystData.strengths}
            weaknesses={executionData.analystData.weaknesses}
            isComplete={true}
          />
        </div>
      )}
    </div>
  );
}
