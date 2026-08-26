import React, { useState, useRef } from 'react';
import { Network, Globe, BarChart3, FileText, Copy, Check, RotateCcw, Sliders, Sparkles, Code2, AlertCircle } from 'lucide-react';

export default function PromptHub({ prompts, setPrompts, onResetPrompts }) {
  const [selectedAgentId, setSelectedAgentId] = useState('orchestrator');
  const [copiedId, setCopiedId] = useState(null);
  const [notification, setNotification] = useState('');

  const editorRef = useRef(null);
  const currentAgent = prompts[selectedAgentId];

  const agentIcons = {
    orchestrator: Network,
    researcher: Globe,
    analyst: BarChart3,
    synthesizer: FileText
  };

  const handleCopyPrompt = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setNotification('System prompt copied to clipboard!');
    setTimeout(() => {
      setCopiedId(null);
      setNotification('');
    }, 2500);
  };

  const handlePromptChange = (newText) => {
    setPrompts(prev => ({
      ...prev,
      [selectedAgentId]: {
        ...prev[selectedAgentId],
        systemPrompt: newText
      }
    }));
  };

  const handleTempChange = (newTemp) => {
    setPrompts(prev => ({
      ...prev,
      [selectedAgentId]: {
        ...prev[selectedAgentId],
        temperature: parseFloat(newTemp)
      }
    }));
  };

  const handleSelectAgent = (agentId) => {
    setSelectedAgentId(agentId);
    if (window.innerWidth < 1024 && editorRef.current) {
      setTimeout(() => {
        editorRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 100);
    }
  };

  const handleConfirmReset = () => {
    if (window.confirm("Are you sure you want to reset all agent system instructions and temperatures to defaults?")) {
      onResetPrompts();
      setNotification('All prompts reset to defaults.');
      setTimeout(() => setNotification(''), 2500);
    }
  };

  return (
    <div className="prompt-hub-container">
      {notification && (
        <div className="toast-notification">
          <Check size={16} />
          <span>{notification}</span>
        </div>
      )}

      <div className="hub-header">
        <div className="hub-title-group">
          <h2>Multi-Agent System Prompt Hub</h2>
          <p>Inspect, customize, and tune system instructions for your CrewAI / LangGraph agent pipeline.</p>
        </div>

        <button className="secondary-btn danger-hover" onClick={handleConfirmReset}>
          <RotateCcw size={16} />
          <span>Reset All to Defaults</span>
        </button>
      </div>

      <div className="hub-layout">
        {/* Agent Selector Sidebar */}
        <div className="agent-selector-sidebar">
          {Object.values(prompts).map(agent => {
            const Icon = agentIcons[agent.id] || Code2;
            const isSelected = agent.id === selectedAgentId;

            return (
              <div
                key={agent.id}
                className={`sidebar-agent-card ${isSelected ? 'is-selected' : ''}`}
                onClick={() => handleSelectAgent(agent.id)}
                style={{
                  borderLeftColor: isSelected ? agent.color : 'transparent'
                }}
              >
                <div className="agent-card-icon" style={{ color: agent.color, background: `${agent.color}15` }}>
                  <Icon size={20} />
                </div>
                <div className="agent-card-meta">
                  <span className="agent-badge">{agent.badge}</span>
                  <h4>{agent.name}</h4>
                  <span className="agent-role">{agent.role}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Prompt Editor & Controls */}
        <div className="prompt-editor-panel" ref={editorRef}>
          <div className="editor-top-bar">
            <div className="agent-title-meta">
              <span className="agent-badge-pill" style={{ background: `${currentAgent.color}20`, color: currentAgent.color }}>
                {currentAgent.badge}
              </span>
              <h3>{currentAgent.name}</h3>
            </div>

            <div className="editor-actions">
              <button
                className="icon-btn"
                onClick={() => handleCopyPrompt(currentAgent.systemPrompt, currentAgent.id)}
                title="Copy System Prompt"
              >
                {copiedId === currentAgent.id ? <Check size={18} className="success-icon text-emerald-400" /> : <Copy size={18} />}
                <span>{copiedId === currentAgent.id ? 'Copied' : 'Copy Prompt'}</span>
              </button>
            </div>
          </div>

          <div className="agent-goal-banner">
            <strong>Goal:</strong> {currentAgent.goal}
          </div>

          <div className="prompt-editor-body">
            <div className="editor-label-row">
              <label>System Instructions (System Prompt)</label>
              <span className="char-count">{currentAgent.systemPrompt.length} chars</span>
            </div>
            <textarea
              className="prompt-textarea"
              value={currentAgent.systemPrompt}
              onChange={(e) => handlePromptChange(e.target.value)}
              rows={14}
              spellCheck="false"
            />
          </div>

          <div className="prompt-parameters-bar">
            <div className="param-group">
              <div className="param-label-row">
                <Sliders size={16} />
                <span>Temperature:</span>
                <strong>{currentAgent.temperature}</strong>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={currentAgent.temperature}
                onChange={(e) => handleTempChange(e.target.value)}
                className="range-input"
              />
            </div>

            <div className="param-group">
              <div className="param-label-row">
                <Sparkles size={16} />
                <span>Model Assignment:</span>
              </div>
              <span className="model-name-tag">{currentAgent.model}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
