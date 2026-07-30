import React, { useState } from 'react';
import { Network, Globe, BarChart3, FileText, ArrowDownRight, ArrowRight, ShieldCheck, Zap, Info, CheckCircle2, ChevronRight } from 'lucide-react';

export default function AgentGraph({ activeAgentId, prompts, onSelectPrompt }) {
  const [selectedNode, setSelectedNode] = useState('orchestrator');

  const nodes = [
    {
      id: 'orchestrator',
      name: 'The Orchestrator Agent',
      role: 'Lead Data Pipeline Orchestrator (Supervisor)',
      icon: Network,
      color: '#6366f1',
      bgGlow: 'rgba(99, 102, 241, 0.15)',
      borderColor: 'rgba(99, 102, 241, 0.4)',
      type: 'Supervisor',
      desc: 'Controls pipeline flow, delegates tasks to workers sequentially, and aggregates raw data to final report.'
    },
    {
      id: 'researcher',
      name: 'The Web Researcher Agent',
      role: 'Expert OSINT Consumer Researcher',
      icon: Globe,
      color: '#10b981',
      bgGlow: 'rgba(16, 185, 129, 0.15)',
      borderColor: 'rgba(16, 185, 129, 0.4)',
      type: 'Worker 1',
      desc: 'Scrapes verified domains (Trustpilot, G2, major news) for 15-30 raw feedback snippets.'
    },
    {
      id: 'analyst',
      name: 'The Sentiment Analyst Agent',
      role: 'Lead Data Scientist',
      icon: BarChart3,
      color: '#06b6d4',
      bgGlow: 'rgba(6, 182, 212, 0.15)',
      borderColor: 'rgba(6, 182, 212, 0.4)',
      type: 'Worker 2',
      desc: 'Scores sentiment percentages (Positive/Neutral/Negative = 100%) and extracts top 2 Strengths & Weaknesses.'
    },
    {
      id: 'synthesizer',
      name: 'The Report Writer Agent',
      role: 'Executive Communications Architect',
      icon: FileText,
      color: '#f59e0b',
      bgGlow: 'rgba(245, 158, 11, 0.15)',
      borderColor: 'rgba(245, 158, 11, 0.4)',
      type: 'Worker 3',
      desc: 'Formats structured Executive Markdown Sentiment Reports adhering to strict template formatting.'
    }
  ];

  const currentNode = nodes.find(n => n.id === selectedNode) || nodes[0];
  const nodePrompt = prompts[selectedNode];

  return (
    <div className="agent-graph-container">
      <div className="graph-header-banner">
        <div className="banner-title-group">
          <h2>Hierarchical Multi-Agent Topology</h2>
          <p>Supervisor / Worker orchestration pattern powered by 4 specialized LLM personas</p>
        </div>
        <div className="banner-badges">
          <span className="badge supervisor"><Zap size={14} /> 1 Supervisor Node</span>
          <span className="badge worker"><ShieldCheck size={14} /> 3 Worker Nodes</span>
        </div>
      </div>

      <div className="graph-layout">
        {/* Interactive Diagram canvas */}
        <div className="diagram-canvas">
          {/* Supervisor Row */}
          <div className="topology-row supervisor-row">
            <div
              className={`node-card supervisor-card ${activeAgentId === 'orchestrator' ? 'is-executing' : ''} ${selectedNode === 'orchestrator' ? 'is-selected' : ''}`}
              onClick={() => setSelectedNode('orchestrator')}
              style={{
                borderColor: selectedNode === 'orchestrator' ? '#6366f1' : 'rgba(99, 102, 241, 0.3)',
                boxShadow: selectedNode === 'orchestrator' ? '0 0 25px rgba(99, 102, 241, 0.25)' : 'none'
              }}
            >
              <div className="node-header">
                <div className="node-icon-box" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8' }}>
                  <Network size={22} />
                </div>
                <div className="node-titles">
                  <span className="node-badge supervisor">Orchestrator (Supervisor)</span>
                  <h3>The Orchestrator</h3>
                </div>
                {activeAgentId === 'orchestrator' && <div className="pulse-dot"></div>}
              </div>
              <p className="node-desc">Coordinates data flow between Web Researcher, Sentiment Analyst, and Report Writer.</p>
            </div>
          </div>

          {/* Connection Lines Visualizer */}
          <div className="flow-lines-container">
            <div className="flow-line left-branch">
              <span className="line-label">1. Delegation</span>
            </div>
            <div className="flow-line center-branch">
              <span className="line-label">2. Payload Handoff</span>
            </div>
            <div className="flow-line right-branch">
              <span className="line-label">3. Final Synthesis</span>
            </div>
          </div>

          {/* Workers Row */}
          <div className="topology-row workers-row">
            {nodes.slice(1).map(node => {
              const Icon = node.icon;
              const isActive = activeAgentId === node.id;
              const isSelected = selectedNode === node.id;

              return (
                <div
                  key={node.id}
                  className={`node-card worker-card ${isActive ? 'is-executing' : ''} ${isSelected ? 'is-selected' : ''}`}
                  onClick={() => setSelectedNode(node.id)}
                  style={{
                    borderColor: isSelected ? node.color : node.borderColor,
                    boxShadow: isSelected ? `0 0 20px ${node.bgGlow}` : 'none'
                  }}
                >
                  <div className="node-header">
                    <div className="node-icon-box" style={{ background: node.bgGlow, color: node.color }}>
                      <Icon size={20} />
                    </div>
                    <div className="node-titles">
                      <span className="node-badge worker">{node.type}</span>
                      <h3>{node.name.replace('The ', '')}</h3>
                    </div>
                    {isActive && <div className="pulse-dot"></div>}
                  </div>
                  <p className="node-desc">{node.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Node Inspector Drawer */}
        <div className="node-inspector">
          <div className="inspector-header">
            <div className="inspector-icon" style={{ background: currentNode.bgGlow, color: currentNode.color }}>
              {React.createElement(currentNode.icon, { size: 24 })}
            </div>
            <div>
              <h3>{currentNode.name}</h3>
              <span className="inspector-subtitle">{currentNode.role}</span>
            </div>
          </div>

          <div className="inspector-section">
            <h4>Agent Responsibility</h4>
            <p className="inspector-desc">{currentNode.desc}</p>
          </div>

          <div className="inspector-section">
            <div className="section-title-row">
              <h4>Configured System Prompt</h4>
              <button className="text-btn" onClick={() => onSelectPrompt(currentNode.id)}>
                Edit Prompt <ChevronRight size={14} />
              </button>
            </div>
            <div className="prompt-preview-box">
              <pre>{nodePrompt?.systemPrompt || 'Loading prompt...'}</pre>
            </div>
          </div>

          <div className="inspector-footer">
            <div className="meta-item">
              <span className="meta-label">Temperature:</span>
              <span className="meta-val">{nodePrompt?.temperature ?? 0.2}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Model:</span>
              <span className="meta-val">{nodePrompt?.model ?? 'Gemini 3.6 Flash'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
