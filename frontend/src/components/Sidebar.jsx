import React from 'react';

export default function Sidebar({ activeTab, setActiveTab, config }) {
  const menuItems = [
    { id: 'campaign', label: '50-Day Campaign', icon: '📅' },
    { id: 'campaigns', label: 'Campaigns', icon: '📁' },
    { id: 'calendar', label: 'Calendar View', icon: '📅' },
    { id: 'queue', label: 'Random Queue', icon: '🎲' },
    { id: 'automation', label: 'Campaign Automation', icon: '🤖' },
    { id: 'scheduled', label: 'Scheduled Jobs', icon: '⏳' },
    { id: 'config', label: 'Configuration', icon: '⚙️' }
  ];

  return (
    <aside className="sidebar">
      <div>
        <div className="brand">
          <span className="brand-logo">🤖</span>
          <div className="brand-text">
            <h1>GoRan AI</h1>
            <p>Publisher Node</p>
          </div>
        </div>
        
        <nav className="nav-menu">
          {menuItems.map(item => (
            <button
              key={item.id}
              className={`nav-btn ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className="icon">{item.icon}</span> {item.label}
            </button>
          ))}
        </nav>
      </div>
      
      <div className="api-status-card">
        <div className="status-indicator">
          <span className="pulse green"></span>
          <span className="indicator-text">Meta Graph API: Online</span>
        </div>
        <p id="ig-account-name">
          {config?.instagram_account_id && config.instagram_account_id !== 'Not Configured'
            ? '@goran.dotin (Active)'
            : 'Not Configured'}
        </p>
      </div>
    </aside>
  );
}
