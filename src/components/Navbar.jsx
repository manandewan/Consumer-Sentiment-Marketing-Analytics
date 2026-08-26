import React from 'react';
import { Activity, FileCode2, PlayCircle, Sparkles, Layers } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, currentModel, isRunning }) {
  return (
    <header className="app-navbar">
      <div className="navbar-left">
        <div className="logo-badge">
          <div className="logo-icon-wrap prism-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <polygon points="12,2 22,8 18,22 6,22 2,8" stroke="url(#navGrad)" strokeWidth="2" fill="rgba(99,102,241,0.2)"/>
              <path d="M6 16 Q 9 19, 12 13 T 18 7" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round"/>
              <circle cx="18" cy="7" r="2" fill="#10b981"/>
              <circle cx="12" cy="13" r="2" fill="#38bdf8"/>
              <circle cx="6" cy="16" r="2" fill="#6366f1"/>
              <defs>
                <linearGradient id="navGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38bdf8"/>
                  <stop offset="100%" stopColor="#10b981"/>
                </linearGradient>
              </defs>
            </svg>
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
        <div className="model-chip" title={currentModel}>
          <Sparkles className="sparkle-icon" />
          <span className="model-label desktop-only">Model:</span>
          <span className="model-val desktop-only">{currentModel}</span>
          <span className="model-val mobile-only">Gemini 3.6</span>
        </div>
      </div>
    </header>
  );
}
