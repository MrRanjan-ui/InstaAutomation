import React, { useState, useEffect } from 'react';

const Icons = {
  database: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
    </svg>
  ),
  sheets: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  instagram: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
    </svg>
  ),
  cloudinary: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v8" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  sync: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  ),
  seed: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v20" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      <circle cx="12" cy="12" r="10" />
    </svg>
  ),
  arrowRight: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  ),
  clock: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  check: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  alert: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  key: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3" />
    </svg>
  )
};

export default function SystemDashboard({ onTabNavigate, onPreviewNavigate }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [msg, setMsg] = useState({ text: '', type: '' });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/system/dashboard');
      const d = await res.json();
      setData(d);
    } catch (err) {
      console.error('Error fetching system dashboard:', err);
      showMsg('Failed to load system metrics. Is the backend running?', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const showMsg = (text, type = 'success') => {
    setMsg({ text, type });
    setTimeout(() => setMsg({ text: '', type: '' }), 5000);
  };

  const handleSeedIdeas = async () => {
    try {
      setActionLoading(true);
      const res = await fetch('/api/ideas/seed', { method: 'POST' });
      const resData = await res.json();
      if (res.ok) {
        showMsg(resData.message || 'Seeded 5 brand post ideas to sheets successfully!', 'success');
        fetchDashboardData();
      } else {
        showMsg(resData.detail || 'Failed to seed ideas.', 'error');
      }
    } catch (err) {
      showMsg('Network error while seeding ideas.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <section className="content-section active">
        <header className="section-header">
          <h2>System Control Center</h2>
          <p>Analyzing system pipelines, integration statuses, and scheduling queues...</p>
        </header>
        <div className="grid-layout" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
          <div className="loading-skeleton-card" style={{ height: '140px' }}></div>
          <div className="loading-skeleton-card" style={{ height: '140px' }}></div>
          <div className="loading-skeleton-card" style={{ height: '140px' }}></div>
          <div className="loading-skeleton-card" style={{ height: '140px' }}></div>
        </div>
        <div className="card" style={{ height: '200px' }}></div>
      </section>
    );
  }

  const { integrations, database_stats, campaigns, queue, today_schedule, recent_jobs } = data;

  // Compute total database jobs stats
  const totalDbJobs = (database_stats.Success || 0) + (database_stats.Pending || 0) + (database_stats.Failed || 0) + (database_stats.Posting || 0);
  const resolvedDbJobs = (database_stats.Success || 0) + (database_stats.Failed || 0);
  const successRate = resolvedDbJobs > 0 ? Math.round(((database_stats.Success || 0) / resolvedDbJobs) * 100) : 100;

  // Compute total campaign progress
  let totalCampaignPosts = 0;
  let totalCampaignPosted = 0;
  campaigns.forEach(c => {
    totalCampaignPosts += c.total_posts || 0;
    totalCampaignPosted += c.posted || 0;
  });
  const campaignProgressPercent = totalCampaignPosts > 0 ? Math.round((totalCampaignPosted / totalCampaignPosts) * 100) : 0;

  return (
    <section className="content-section active">
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>System Control Center</h2>
          <p>Real-time health monitor, active campaigns, scheduler queue, and logs.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            className="btn secondary" 
            onClick={fetchDashboardData} 
            disabled={actionLoading}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.55rem 0.95rem' }}
          >
            {Icons.sync} Refresh Stats
          </button>
          <button 
            className="btn primary" 
            onClick={handleSeedIdeas} 
            disabled={actionLoading}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.55rem 0.95rem' }}
          >
            {Icons.seed} Seed Brand Ideas
          </button>
        </div>
      </header>

      {msg.text && (
        <div className={`alert-banner ${msg.type === 'error' ? 'alert-danger' : 'alert-success'}`} style={{ marginBottom: '2rem' }}>
          <span className="alert-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            {msg.type === 'error' ? Icons.alert : Icons.check}
          </span>
          <span className="alert-text">{msg.text}</span>
          <button className="alert-close" onClick={() => setMsg({ text: '', type: '' })}>×</button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '2.5rem' }}>
        
        {/* Google Sheets Integration status card */}
        <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1rem', borderLeft: `3px solid ${integrations.google_sheets ? 'var(--accent-emerald)' : 'var(--error-border)'}` }}>
          <div style={{ padding: '0.6rem', background: integrations.google_sheets ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)', borderRadius: '10px', color: integrations.google_sheets ? 'var(--accent-emerald)' : '#ef4444', display: 'flex', alignItems: 'center' }}>
            {Icons.sheets}
          </div>
          <div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>Google Sheets DB</h4>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {integrations.google_sheets ? 'Connected via Service Account' : 'Missing service account configuration'}
            </p>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem', color: integrations.google_sheets ? 'var(--accent-emerald)' : '#ef4444', fontWeight: 600, marginTop: '0.5rem', textTransform: 'uppercase' }}>
              <span className={`pulse ${integrations.google_sheets ? 'green' : ''}`} style={{ background: integrations.google_sheets ? 'var(--accent-emerald)' : '#ef4444' }}></span>
              {integrations.google_sheets ? 'Active' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Cloudinary status card */}
        <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1rem', borderLeft: `3px solid ${integrations.cloudinary ? 'var(--accent-emerald)' : 'var(--error-border)'}` }}>
          <div style={{ padding: '0.6rem', background: integrations.cloudinary ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)', borderRadius: '10px', color: integrations.cloudinary ? 'var(--accent-emerald)' : '#ef4444', display: 'flex', alignItems: 'center' }}>
            {Icons.cloudinary}
          </div>
          <div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>Cloudinary Storage</h4>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {integrations.cloudinary ? 'Credentials Verified' : 'Missing API environment variables'}
            </p>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem', color: integrations.cloudinary ? 'var(--accent-emerald)' : '#ef4444', fontWeight: 600, marginTop: '0.5rem', textTransform: 'uppercase' }}>
              <span className={`pulse ${integrations.cloudinary ? 'green' : ''}`} style={{ background: integrations.cloudinary ? 'var(--accent-emerald)' : '#ef4444' }}></span>
              {integrations.cloudinary ? 'Active' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Meta Graph API status card */}
        <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1rem', borderLeft: `3px solid ${integrations.instagram ? 'var(--accent-emerald)' : 'var(--error-border)'}` }}>
          <div style={{ padding: '0.6rem', background: integrations.instagram ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)', borderRadius: '10px', color: integrations.instagram ? 'var(--accent-emerald)' : '#ef4444', display: 'flex', alignItems: 'center' }}>
            {Icons.instagram}
          </div>
          <div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>Meta Graph API</h4>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {integrations.instagram ? `Account: ${integrations.instagram_account}` : 'Missing Token or Account ID'}
            </p>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem', color: integrations.instagram ? 'var(--accent-emerald)' : '#ef4444', fontWeight: 600, marginTop: '0.5rem', textTransform: 'uppercase' }}>
              <span className={`pulse ${integrations.instagram ? 'green' : ''}`} style={{ background: integrations.instagram ? 'var(--accent-emerald)' : '#ef4444' }}></span>
              {integrations.instagram ? 'Active' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Token Health card */}
        {integrations.token_status ? (
          <div className="card" style={{ 
            padding: '1.5rem', 
            display: 'flex', 
            alignItems: 'flex-start', 
            gap: '1rem', 
            borderLeft: `3px solid ${
              !integrations.token_status.is_valid ? '#ef4444' : 
              integrations.token_status.days_remaining < 3 ? '#ef4444' :
              integrations.token_status.days_remaining < 14 ? '#f59e0b' :
              'var(--accent-emerald)'
            }` 
          }}>
            <div style={{ 
              padding: '0.6rem', 
              background: !integrations.token_status.is_valid ? 'rgba(239, 68, 68, 0.05)' : 
                          integrations.token_status.days_remaining < 14 ? 'rgba(245, 158, 11, 0.05)' :
                          'rgba(16, 185, 129, 0.05)', 
              borderRadius: '10px', 
              color: !integrations.token_status.is_valid ? '#ef4444' : 
                     integrations.token_status.days_remaining < 14 ? '#f59e0b' :
                     'var(--accent-emerald)', 
              display: 'flex', 
              alignItems: 'center' 
            }}>
              {Icons.key}
            </div>
            <div>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>Token Expiry</h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                {!integrations.token_status.is_valid ? 'Token is Invalid/Expired' : 
                 integrations.token_status.days_remaining > 365 ? 'Never Expires' : 
                 `Expires in ${integrations.token_status.days_remaining} days`}
              </p>
              <span style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                gap: '0.3rem', 
                fontSize: '0.7rem', 
                color: !integrations.token_status.is_valid ? '#ef4444' : 
                       integrations.token_status.days_remaining < 14 ? '#f59e0b' :
                       'var(--accent-emerald)', 
                fontWeight: 600, 
                marginTop: '0.5rem', 
                textTransform: 'uppercase' 
              }}>
                <span className={`pulse ${
                  !integrations.token_status.is_valid ? 'red' : 
                  integrations.token_status.days_remaining < 14 ? 'orange' : 'green'
                }`} style={{ 
                  background: !integrations.token_status.is_valid ? '#ef4444' : 
                              integrations.token_status.days_remaining < 14 ? '#f59e0b' :
                              'var(--accent-emerald)' 
                }}></span>
                {!integrations.token_status.is_valid ? 'Expired/Invalid' : 
                 integrations.token_status.days_remaining < 14 ? 'Expiring Soon' : 'Healthy'}
              </span>
            </div>
          </div>
        ) : (
          <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1rem', borderLeft: '3px solid #ef4444' }}>
            <div style={{ padding: '0.6rem', background: 'rgba(239, 68, 68, 0.05)', borderRadius: '10px', color: '#ef4444', display: 'flex', alignItems: 'center' }}>
              {Icons.key}
            </div>
            <div>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>Token Expiry</h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>No status available</p>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem', color: '#ef4444', fontWeight: 600, marginTop: '0.5rem', textTransform: 'uppercase' }}>
                <span className="pulse" style={{ background: '#ef4444' }}></span>
                Unconfigured
              </span>
            </div>
          </div>
        )}

      </div>

      {/* Main KPI Stats Row */}
      <div className="grid-layout" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '2.5rem' }}>
        
        {/* SQL Job Health */}
        <div className="card post-card" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)' }}>Publish Queue Health</span>
              <span className="badge status-posted" style={{ background: 'var(--success-bg)', border: '1px solid var(--success-border)', color: 'var(--accent-emerald)' }}>{successRate}% Success Rate</span>
            </div>
            <h2 style={{ fontSize: '2.2rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              {database_stats.Success || 0} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>/ {totalDbJobs} total jobs</span>
            </h2>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1rem' }}>
              <span className="badge status-generating" style={{ fontSize: '0.7rem' }}>{database_stats.Pending || 0} Pending</span>
              <span className="badge status-approved" style={{ fontSize: '0.7rem' }}>{database_stats.Posting || 0} Active</span>
              <span className="badge status-failed" style={{ fontSize: '0.7rem' }}>{database_stats.Failed || 0} Failed</span>
            </div>
          </div>
          <button 
            className="btn secondary" 
            style={{ width: '100%', padding: '0.45rem', marginTop: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', fontSize: '0.78rem' }}
            onClick={() => onTabNavigate('scheduled')}
          >
            Manage Scheduled Jobs {Icons.arrowRight}
          </button>
        </div>

        {/* Campaign Metrics KPI */}
        <div className="card post-card" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)' }}>Campaign Progression</span>
              <span className="badge status-approved">{campaigns.length} Series Active</span>
            </div>
            <h2 style={{ fontSize: '2.2rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              {campaignProgressPercent}% <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>({totalCampaignPosted} / {totalCampaignPosts} posts)</span>
            </h2>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', height: '5px', borderRadius: '3px', overflow: 'hidden', marginTop: '1.2rem', marginBottom: '0.5rem' }}>
              <div style={{ background: 'var(--accent-emerald)', width: `${campaignProgressPercent}%`, height: '100%' }}></div>
            </div>
          </div>
          <button 
            className="btn secondary" 
            style={{ width: '100%', padding: '0.45rem', marginTop: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', fontSize: '0.78rem' }}
            onClick={() => onTabNavigate('campaigns')}
          >
            View Campaigns {Icons.arrowRight}
          </button>
        </div>

        {/* Random Queue KPI */}
        <div className="card post-card" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)' }}>Random Post Queue</span>
              <span className="badge status-posted" style={{ background: 'var(--accent-blue-soft)', border: '1px solid rgba(59, 130, 246, 0.2)', color: 'var(--accent-blue)' }}>{queue.approved} Ready</span>
            </div>
            <h2 style={{ fontSize: '2.2rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              {queue.total} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>ideas stored in sheets</span>
            </h2>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1rem' }}>
              <span className="badge status-generating" style={{ fontSize: '0.7rem' }}>{queue.pending} Unapproved</span>
              <span className="badge status-posted" style={{ fontSize: '0.7rem' }}>{queue.posted} Published</span>
            </div>
          </div>
          <button 
            className="btn secondary" 
            style={{ width: '100%', padding: '0.45rem', marginTop: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', fontSize: '0.78rem' }}
            onClick={() => onTabNavigate('queue')}
          >
            Manage Random Queue {Icons.arrowRight}
          </button>
        </div>

      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '2rem', marginBottom: '2.5rem' }}>
        
        {/* Today's Unified Schedule */}
        <div className="card" style={{ padding: '1.8rem' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.2rem', fontSize: '1.1rem', fontWeight: 600 }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center' }}>{Icons.clock}</span>
            Today's Scheduling Timeline
          </h3>
          <div className="schedule-table-wrapper" style={{ maxHeight: '350px', overflowY: 'auto' }}>
            <table className="schedule-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--card-border)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem' }}>Source Type</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem' }}>Post ID</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem' }}>Time</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {today_schedule.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '3.5rem 2rem' }}>
                      No campaign or random posts scheduled for today.
                    </td>
                  </tr>
                ) : (
                  today_schedule.map(post => {
                    let statusClass = 'badge';
                    if (post.status === 'Pending') statusClass += ' status-generating';
                    else if (post.status === 'Posting') statusClass += ' status-approved';
                    else if (post.status === 'Success') statusClass += ' status-posted';
                    else if (post.status === 'Failed') statusClass += ' status-failed';

                    const timeLocal = new Date(post.schedule_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const isQueue = post.source_sheet === 'Queue';

                    return (
                      <tr 
                        key={post.id} 
                        style={{ borderBottom: '1px solid var(--card-border)', fontSize: '0.88rem', cursor: onPreviewNavigate ? 'pointer' : 'default' }}
                        onClick={() => onPreviewNavigate && onPreviewNavigate(post.post_id, post.source_sheet, post.row_index)}
                      >
                        <td style={{ padding: '0.75rem' }}>
                          <span className="badge" style={{ background: isQueue ? 'var(--accent-blue-soft)' : 'var(--accent-emerald-soft)', color: isQueue ? 'var(--accent-blue)' : 'var(--accent-emerald)', border: `1px solid ${isQueue ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)'}` }}>
                            {isQueue ? 'Random Post' : 'Campaign'}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem' }}><strong>{post.post_id}</strong></td>
                        <td style={{ padding: '0.75rem' }}>{timeLocal}</td>
                        <td style={{ padding: '0.75rem' }}><span className={statusClass}>{post.status}</span></td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions and Stats Dashboard summary */}
        <div className="card" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.2rem', fontSize: '1.1rem', fontWeight: 600 }}>
              <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center' }}>{Icons.database}</span>
              Active Campaigns Registry
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '250px', overflowY: 'auto', paddingRight: '0.5rem' }}>
              {campaigns.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No campaign worksheets registered.</p>
              ) : (
                campaigns.map(camp => {
                  const campProgress = camp.total_posts > 0 ? Math.round((camp.posted / camp.total_posts) * 100) : 0;
                  return (
                    <div key={camp.worksheet_name} style={{ background: 'rgba(255, 255, 255, 0.01)', border: '1px solid var(--card-border)', borderRadius: '8px', padding: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                        <strong>{camp.campaign_name}</strong>
                        <span style={{ color: 'var(--text-secondary)' }}>{campProgress}% ({camp.posted}/{camp.total_posts})</span>
                      </div>
                      <div style={{ background: 'rgba(255, 255, 255, 0.03)', height: '3px', borderRadius: '1px', overflow: 'hidden' }}>
                        <div style={{ background: 'var(--accent-emerald)', width: `${campProgress}%`, height: '100%' }}></div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1.2rem', marginTop: '1.2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <button 
              className="btn secondary" 
              style={{ padding: '0.5rem', fontSize: '0.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem' }}
              onClick={() => onTabNavigate('automation')}
            >
              Bulk Scheduler
            </button>
            <button 
              className="btn secondary" 
              style={{ padding: '0.5rem', fontSize: '0.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem' }}
              onClick={() => onTabNavigate('calendar')}
            >
              Calendar Map
            </button>
          </div>
        </div>

      </div>

      {/* Recent Activity Log */}
      <div className="card" style={{ padding: '1.8rem', marginBottom: '2rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.2rem', fontSize: '1.1rem', fontWeight: 600 }}>
          <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center' }}>{Icons.database}</span>
          Recent Scheduled Jobs Log (Last 10 Executions)
        </h3>
        <div className="schedule-table-wrapper">
          <table className="schedule-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--card-border)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Job ID</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Post ID</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Source Sheet</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Schedule Time</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Details / Errors</th>
              </tr>
            </thead>
            <tbody>
              {recent_jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                    No jobs recorded in scheduler database.
                  </td>
                </tr>
              ) : (
                recent_jobs.map(job => {
                  let statusClass = 'badge';
                  if (job.status === 'Pending') statusClass += ' status-generating';
                  else if (job.status === 'Posting') statusClass += ' status-approved';
                  else if (job.status === 'Success') statusClass += ' status-posted';
                  else if (job.status === 'Failed') statusClass += ' status-failed';

                  return (
                    <tr 
                      key={job.id} 
                      style={{ borderBottom: '1px solid var(--card-border)', fontSize: '0.85rem', cursor: onPreviewNavigate ? 'pointer' : 'default' }}
                      onClick={() => onPreviewNavigate && onPreviewNavigate(job.post_id, job.source_sheet, job.row_index)}
                    >
                      <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>#{job.id}</td>
                      <td style={{ padding: '0.75rem' }}><strong>{job.post_id}</strong></td>
                      <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>{job.source_sheet}</td>
                      <td style={{ padding: '0.75rem' }}>{new Date(job.schedule_time).toLocaleString()}</td>
                      <td style={{ padding: '0.75rem' }}><span className={statusClass}>{job.status}</span></td>
                      <td style={{ padding: '0.75rem', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {job.status === 'Success' && (
                          <span style={{ color: 'var(--accent-emerald)', fontSize: '0.78rem' }}>IG Publish ID: {job.published_id}</span>
                        )}
                        {job.status === 'Failed' && (
                          <span style={{ color: '#ef4444', fontSize: '0.78rem' }} title={job.error_message}>{job.error_message}</span>
                        )}
                        {job.status === 'Pending' && (
                          <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>Waiting for schedule time</span>
                        )}
                        {job.status === 'Posting' && (
                          <span style={{ color: 'var(--accent-blue)', fontSize: '0.78rem' }}>Instagram container creation in progress...</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
