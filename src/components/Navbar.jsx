import React from 'react';
import { Bot, Cpu, Network, FileCode2, PlayCircle, Sparkles, Layers } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, currentModel, isRunning }) {
  return (
    <header className="app-navbar">
      <div className="navbar-left">
        <div className="logo-badge">
          <div className="logo-icon-wrap">
            <Network className="logo-icon" />
          </div>
          <div className="logo-text-group">
            <div className="logo-title">
              MARKETING <span className="logo-accent">2.0</span>
            </div>
            <div className="logo-subtitle">Multi-Agent Sentiment Engine</div>
          </div>
        </div>

        <div className="architecture-tag">
          <span className="dot pulse"></span>
          <span>Supervisor / Worker Architecture (2026 Standard)</span>
        </div>
      </div>

      <nav className="navbar-nav">
        <button
          className={`nav-item ${activeTab === 'pipeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('pipeline')}
        >
          <PlayCircle className="nav-icon" />
          <span>Pipeline Simulator</span>
          {isRunning && <span className="running-indicator"></span>}
        </button>

        <button
          className={`nav-item ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          <Layers className="nav-icon" />
          <span>Agent Topology</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'prompts' ? 'active' : ''}`}
          onClick={() => setActiveTab('prompts')}
        >
          <FileCode2 className="nav-icon" />
          <span>System Prompts Hub</span>
          <span className="badge-count">4 Agents</span>
        </button>
      </nav>

      <div className="navbar-right">
        <div className="model-chip">
          <Sparkles className="sparkle-icon" />
          <span className="model-label">Model:</span>
          <span className="model-val">{currentModel}</span>
        </div>
      </div>
    </header>
  );
}
