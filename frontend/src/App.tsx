import { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import ReasoningLog from './components/ReasoningLog';
import CodeViewer from './components/CodeViewer';
import EquityCurve from './components/EquityCurve';
import HypothesisHistory from './components/HypothesisHistory';
import './App.css';

const WS_URL = 'ws://localhost:8000/ws/logs';

export default function App() {
  const { logs, isConnected, isRunning, sendPrompt, clearLogs } = useWebSocket(WS_URL);
  const [prompt, setPrompt] = useState('');
  const [activeTab, setActiveTab] = useState<'live' | 'history'>('live');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isRunning) {
      sendPrompt(prompt.trim());
      setPrompt('');
    }
  };

  const examplePrompts = [
    'Analyse AAPL and test a SMA crossover strategy over the past 2 years',
    'Research BTC-USD and test a momentum-based strategy',
    'Compare RSI mean reversion vs trend following on MSFT',
    'Test a dual moving average strategy on SPY with optimized periods',
  ];

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1 className="logo">
            <span className="logo-icon">⚡</span>
            Autonomous Quant Swarm
          </h1>
          <span className="subtitle">AI-Powered Quantitative Research Agent</span>
        </div>
        <div className="header-right">
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      {/* Prompt Bar */}
      <div className="prompt-section">
        <form onSubmit={handleSubmit} className="prompt-form">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Analyse AAPL and test a momentum strategy over the past 2 years..."
            className="prompt-input"
            disabled={isRunning}
          />
          <button
            type="submit"
            className="prompt-button"
            disabled={!prompt.trim() || isRunning || !isConnected}
          >
            {isRunning ? (
              <>
                <span className="spinner" /> Running...
              </>
            ) : (
              '🚀 Run Agent'
            )}
          </button>
          <button
            type="button"
            className="clear-button"
            onClick={clearLogs}
            disabled={isRunning || logs.length === 0}
          >
            🗑️
          </button>
        </form>

        {/* Quick prompts */}
        {logs.length === 0 && !isRunning && (
          <div className="example-prompts">
            {examplePrompts.map((ep, i) => (
              <button
                key={i}
                className="example-btn"
                onClick={() => {
                  setPrompt(ep);
                }}
              >
                {ep}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Tab navigation */}
      <div className="tab-bar">
        <button
          className={`tab ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => setActiveTab('live')}
        >
          🔴 Live Session
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📋 History
        </button>
      </div>

      {/* Main Content */}
      {activeTab === 'live' ? (
        <main className="main-grid">
          <div className="left-col">
            <ReasoningLog logs={logs} isRunning={isRunning} />
          </div>
          <div className="right-col">
            <CodeViewer logs={logs} />
            <EquityCurve logs={logs} />
          </div>
        </main>
      ) : (
        <main className="history-view">
          <HypothesisHistory />
        </main>
      )}

      {/* Footer
      <footer className="footer">
        <span>Powered by Gemini 2.0 Flash • LangChain • backtrader • ChromaDB</span>
      </footer> */}
    </div>
  );
}
