import React, { useState, useEffect } from 'react';

const Icons = {
  calendar: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
  folder: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  ),
  arrowLeft: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  ),
  arrowRight: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  ),
  clock: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
};

export default function CampaignsDashboard({ onPreviewNavigate }) {
  const [dashboardData, setDashboardData] = useState({ campaigns: [], today_posts: [] });
  const [selectedCampaign, setSelectedCampaign] = useState(null); // { worksheetName, campaignName }
  const [campaignPosts, setCampaignPosts] = useState([]);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
  const [isLoadingPosts, setIsLoadingPosts] = useState(false);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setIsLoadingDashboard(true);
      const res = await fetch('/api/campaigns/overview');
      const data = await res.json();
      setDashboardData(data);
    } catch (err) {
      console.error('Error fetching campaigns overview:', err);
    } finally {
      setIsLoadingDashboard(false);
    }
  };

  const handleViewCampaignPosts = async (worksheetName, campaignName) => {
    setSelectedCampaign({ worksheetName, campaignName });
    try {
      setIsLoadingPosts(true);
      const res = await fetch(`/api/campaign/posts?worksheet_name=${encodeURIComponent(worksheetName)}`);
      const data = await res.json();
      setCampaignPosts(data.posts || []);
    } catch (err) {
      console.error('Error fetching campaign posts:', err);
    } finally {
      setIsLoadingPosts(false);
    }
  };

  const handleBackToDashboard = () => {
    setSelectedCampaign(null);
    setCampaignPosts([]);
    fetchDashboard();
  };

  if (isLoadingDashboard) {
    return (
      <section className="content-section active">
        <header className="section-header">
          <h2>Campaigns Dashboard</h2>
          <p>Track all active campaign series, completion progress, and today's schedule.</p>
        </header>
        <div className="card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
          <div className="loading-skeleton-card" style={{ height: '120px' }}></div>
        </div>
        <div className="grid-layout">
          <div className="loading-skeleton-card"></div>
          <div className="loading-skeleton-card"></div>
        </div>
      </section>
    );
  }

  return (
    <section className="content-section active">
      {!selectedCampaign ? (
        // Master view
        <div>
          <header className="section-header">
            <h2>Campaigns Dashboard</h2>
            <p>Track all active campaign series, completion progress, and today's schedule.</p>
          </header>

          {/* Today's Scheduled Posts */}
          <div className="card" style={{ marginBottom: '2.5rem', padding: '1.8rem' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.2rem', fontSize: '1.1rem', fontWeight: 600 }}>
              <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center' }}>{Icons.calendar}</span>
              Today's Scheduled Posts
            </h3>
            <div className="schedule-table-wrapper">
              <table className="schedule-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
                    <th style={{ textAlign: 'left', padding: '0.75rem' }}>Campaign</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem' }}>Post ID</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem' }}>Topic</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem' }}>Time</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboardData.today_posts.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                        No posts scheduled for today.
                      </td>
                    </tr>
                  ) : (
                    dashboardData.today_posts.map(post => {
                      let statusClass = 'badge';
                      if (post.status === 'Pending') statusClass += ' status-generating';
                      else if (post.status === 'Posting') statusClass += ' status-approved';
                      else if (post.status === 'Success') statusClass += ' status-posted';
                      else if (post.status === 'Failed') statusClass += ' status-failed';

                      const timeLocal = new Date(post.schedule_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                      const campaignLabel = post.source_sheet === '50DaysCampaign' ? '50-Day D2C Automation' : post.source_sheet;

                      return (
                        <tr key={post.id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                          <td style={{ padding: '0.75rem' }}><strong>{campaignLabel}</strong></td>
                          <td style={{ padding: '0.75rem' }}>{post.post_id}</td>
                          <td style={{ padding: '0.75rem' }}>{post.topic || '-'}</td>
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

          {/* Active Campaigns */}
          <h3 style={{ marginBottom: '1.2rem', fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center' }}>{Icons.folder}</span>
            Active Campaigns
          </h3>
          <div className="grid-layout">
            {dashboardData.campaigns.length === 0 ? (
              <p className="card" style={{ gridColumn: '1/-1' }}>No campaigns found.</p>
            ) : (
              dashboardData.campaigns.map(camp => {
                const total = camp.total_posts || 0;
                const posted = camp.posted || 0;
                const progressPercent = total > 0 ? Math.round((posted / total) * 100) : 0;

                return (
                  <div key={camp.worksheet_name} className="card post-card">
                    <div>
                      <div className="post-card-header" style={{ marginBottom: '1rem' }}>
                        <span className="badge status-posted">{camp.posted} Posted</span>
                        <span className="badge status-approved">{camp.scheduled} Scheduled</span>
                      </div>
                      <h3 style={{ marginBottom: '1.2rem' }}>{camp.campaign_name}</h3>
                      
                      <div style={{ marginBottom: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                          <span>Completion Progress</span>
                          <span>{progressPercent}% ({posted}/{total})</span>
                        </div>
                        <div style={{ background: 'rgba(255, 255, 255, 0.03)', height: '4px', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ background: 'var(--accent-emerald)', width: `${progressPercent}%`, height: '100%', borderRadius: '2px' }}></div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="post-card-footer">
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{camp.pending} Pending</span>
                      <button
                        className="btn secondary"
                        style={{ padding: '0.45rem 0.85rem' }}
                        onClick={() => handleViewCampaignPosts(camp.worksheet_name, camp.campaign_name)}
                      >
                        View Posts
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        // Detail view
        <div>
          <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
            <div>
              <h2>{selectedCampaign.campaignName}</h2>
              <p>Worksheet Details & Individual Posts</p>
            </div>
            <button className="btn secondary" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }} onClick={handleBackToDashboard}>
              {Icons.arrowLeft} Back to Dashboard
            </button>
          </header>

          {isLoadingPosts ? (
            <div className="grid-layout">
              <div className="loading-skeleton-card"></div>
              <div className="loading-skeleton-card"></div>
              <div className="loading-skeleton-card"></div>
            </div>
          ) : (
            <div className="grid-layout">
              {campaignPosts.length === 0 ? (
                <p className="card" style={{ gridColumn: '1/-1' }}>No posts found in this campaign.</p>
              ) : (
                campaignPosts.map(post => {
                  let statusClass = 'badge';
                  const status = post.sheet_status || 'Pending';
                  if (status.toLowerCase() === 'posted') statusClass += ' status-posted';
                  else if (status.toLowerCase() === 'scheduled') statusClass += ' status-approved';
                  else statusClass += ' status-generating';

                  return (
                    <div
                      key={post.post_id}
                      className="card post-card"
                      onClick={() => onPreviewNavigate(post.post_id, selectedCampaign.worksheetName, post.row_index)}
                    >
                      <div>
                        <div className="post-card-header" style={{ marginBottom: '1rem' }}>
                          <span className={statusClass}>{status}</span>
                          {post.schedule_time && (
                            <span className="badge status-approved" style={{ fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}>
                              {Icons.clock} {new Date(post.schedule_time).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                        <h3 style={{ marginBottom: '1rem' }}>{post.post_id}</h3>
                        <p className="caption-preview" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          {post.topic || 'No topic'}
                        </p>
                      </div>
                      
                      <div className="post-card-footer" style={{ marginTop: 'auto', paddingTop: '1rem' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Row Index: {post.row_index}
                        </span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}>
                          View Details {Icons.arrowRight}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
