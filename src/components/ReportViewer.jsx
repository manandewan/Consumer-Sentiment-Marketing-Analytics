import React, { useState } from 'react';
import { Copy, Check, Download, Sparkles, TrendingUp, AlertTriangle, FileText, BarChart2, Award, ThumbsUp, ThumbsDown } from 'lucide-react';
import confetti from 'canvas-confetti';

export default function ReportViewer({ targetName, reportMarkdown, analystMetrics, strengths, weaknesses, isComplete }) {
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState('formatted'); // 'formatted' | 'raw'

  const handleCopy = () => {
    navigator.clipboard.writeText(reportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownload = () => {
    confetti({ particleCount: 80, spread: 60, origin: { y: 0.6 } });
    const element = document.createElement("a");
    const file = new Blob([reportMarkdown], { type: 'text/markdown' });
    element.href = URL.createObjectURL(file);
    element.download = `Customer_Sentiment_Report_${targetName.replace(/\s+/g, '_')}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="report-viewer-card">
      <div className="report-header">
        <div className="report-title-meta">
          <div className="report-badge">
            <Sparkles size={16} />
            <span>Executive Synthesis Output</span>
          </div>
          <h2>Customer Sentiment Report: {targetName}</h2>
        </div>

        <div className="report-actions">
          <div className="view-toggle">
            <button
              className={`toggle-btn ${viewMode === 'formatted' ? 'active' : ''}`}
              onClick={() => setViewMode('formatted')}
            >
              Formatted View
            </button>
            <button
              className={`toggle-btn ${viewMode === 'raw' ? 'active' : ''}`}
              onClick={() => setViewMode('raw')}
            >
              Raw Markdown
            </button>
          </div>

          <button className="action-btn" onClick={handleCopy} title="Copy Markdown">
            {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>

          <button className="action-btn primary" onClick={handleDownload} title="Download Report">
            <Download size={16} />
            <span>Export Report (.md)</span>
          </button>
        </div>
      </div>

      {viewMode === 'formatted' ? (
        <div className="report-body">
          {/* Sentiment Stats Bar */}
          <div className="sentiment-metrics-section">
            <div className="section-subtitle">
              <BarChart2 size={16} />
              <span>Overall Public Sentiment Distribution</span>
            </div>

            <div className="metrics-cards-grid">
              <div className="metric-card positive">
                <div className="metric-header">
                  <ThumbsUp size={18} />
                  <span>Positive</span>
                </div>
                <div className="metric-value">{analystMetrics?.positive ?? 75}%</div>
                <div className="metric-bar-bg">
                  <div className="metric-bar-fill positive" style={{ width: `${analystMetrics?.positive ?? 75}%` }}></div>
                </div>
              </div>

              <div className="metric-card neutral">
                <div className="metric-header">
                  <TrendingUp size={18} />
                  <span>Neutral</span>
                </div>
                <div className="metric-value">{analystMetrics?.neutral ?? 10}%</div>
                <div className="metric-bar-bg">
                  <div className="metric-bar-fill neutral" style={{ width: `${analystMetrics?.neutral ?? 10}%` }}></div>
                </div>
              </div>

              <div className="metric-card negative">
                <div className="metric-header">
                  <ThumbsDown size={18} />
                  <span>Negative</span>
                </div>
                <div className="metric-value">{analystMetrics?.negative ?? 15}%</div>
                <div className="metric-bar-bg">
                  <div className="metric-bar-fill negative" style={{ width: `${analystMetrics?.negative ?? 15}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Key Strengths & Weaknesses Cards */}
          <div className="themes-grid">
            <div className="theme-card strengths">
              <div className="theme-card-header">
                <Award size={18} />
                <h3>Key Strengths (What users love)</h3>
              </div>
              <ul className="theme-list">
                {(strengths || []).map((item, idx) => (
                  <li key={idx} className="theme-item">
                    <strong className="theme-title">{item.theme}:</strong>
                    <span className="theme-desc">{item.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="theme-card weaknesses">
              <div className="theme-card-header">
                <AlertTriangle size={18} />
                <h3>Key Weaknesses (What needs improvement)</h3>
              </div>
              <ul className="theme-list">
                {(weaknesses || []).map((item, idx) => (
                  <li key={idx} className="theme-item">
                    <strong className="theme-title">{item.theme}:</strong>
                    <span className="theme-desc">{item.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Formatted Markdown Box */}
          <div className="executive-markdown-render">
            <div className="render-header">
              <FileText size={16} />
              <span>Full Generated Markdown Report</span>
            </div>
            <pre className="markdown-pre">{reportMarkdown}</pre>
          </div>
        </div>
      ) : (
        <div className="raw-markdown-editor">
          <textarea
            className="raw-textarea"
            value={reportMarkdown}
            readOnly
            rows={18}
          />
        </div>
      )}
    </div>
  );
}
