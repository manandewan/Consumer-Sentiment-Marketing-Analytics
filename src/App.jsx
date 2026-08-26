import React, { useState } from 'react';
import Navbar from './components/Navbar';
import PipelineExecution from './components/PipelineExecution';
import AgentGraph from './components/AgentGraph';
import PromptHub from './components/PromptHub';
import { DEFAULT_AGENT_PROMPTS } from './data/agentPrompts';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('pipeline');
  const [prompts, setPrompts] = useState(DEFAULT_AGENT_PROMPTS);
  const [activeAgentId, setActiveAgentId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  const handleResetPrompts = () => {
    setPrompts(DEFAULT_AGENT_PROMPTS);
  };

  const handleSelectPromptFromGraph = (agentId) => {
    setActiveTab('prompts');
  };

  return (
    <div className="app-wrapper">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isRunning={isRunning}
      />

      <main className="app-main-content">
        {activeTab === 'pipeline' && (
          <PipelineExecution
            prompts={prompts}
            activeAgentId={activeAgentId}
            setActiveAgentId={setActiveAgentId}
            isRunning={isRunning}
            setIsRunning={setIsRunning}
          />
        )}

        {activeTab === 'graph' && (
          <AgentGraph
            activeAgentId={activeAgentId}
            prompts={prompts}
            onSelectPrompt={handleSelectPromptFromGraph}
          />
        )}

        {activeTab === 'prompts' && (
          <PromptHub
            prompts={prompts}
            setPrompts={setPrompts}
            onResetPrompts={handleResetPrompts}
          />
        )}
      </main>
    </div>
  );
}
