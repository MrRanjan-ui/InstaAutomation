import React, { useState, useEffect } from 'react';

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
          <div className="card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <span>📅</span> Today's Scheduled Posts
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
          <h3 style={{ marginBottom: '1rem', fontFamily: 'Outfit, sans-serif' }}>📁 Active Campaigns</h3>
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
                    <div className="post-card-header" style={{ marginBottom: '0.5rem' }}>
                      <span className="badge status-posted">{camp.posted} Posted</span>
                      <span className="badge status-approved">{camp.scheduled} Scheduled</span>
                    </div>
                    <h3 style={{ marginBottom: '1rem' }}>{camp.campaign_name}</h3>
                    
                    <div style={{ marginBottom: '1.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                        <span>Completion Progress</span>
                        <span>{progressPercent}% ({posted}/{total})</span>
                      </div>
                      <div style={{ background: 'rgba(255, 255, 255, 0.05)', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ background: 'var(--accent-lime)', width: `${progressPercent}%`, height: '100%', borderRadius: '3px' }}></div>
                      </div>
                    </div>
                    
                    <div className="post-card-footer">
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{camp.pending} Pending</span>
                      <button
                        className="btn primary"
                        style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
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
          <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <div>
              <h2>Campaign: {selectedCampaign.campaignName}</h2>
              <p>Worksheet Details & Individual Posts</p>
            </div>
            <button className="btn secondary" style={{ padding: '0.8rem 1.5rem', borderRadius: '8px' }} onClick={handleBackToDashboard}>
              <span>⬅️</span> Back to Campaigns
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
                      style={{ cursor: 'pointer' }}
                      onClick={() => onPreviewNavigate(post.post_id, selectedCampaign.worksheetName, post.row_index)}
                    >
                      <div className="post-card-header" style={{ marginBottom: '1rem' }}>
                        <span className={statusClass}>{status}</span>
                        {post.schedule_time && (
                          <span className="badge status-approved" style={{ fontSize: '0.7rem' }}>
                            🕒 {new Date(post.schedule_time).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <h3 style={{ marginBottom: '1rem' }}>{post.post_id}</h3>
                      <p className="caption-preview" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {post.topic || 'No topic'}
                      </p>
                      
                      <div className="post-card-footer" style={{ marginTop: 'auto', paddingTop: '1rem' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          Row Index: {post.row_index}
                        </span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--accent-neon-blue)', fontWeight: 600 }}>
                          View Details →
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
