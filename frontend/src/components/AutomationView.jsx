import React, { useState, useEffect } from 'react';

export default function AutomationView({ onScheduleSuccess }) {
  const [worksheets, setWorksheets] = useState([]);
  const [selectedWorksheet, setSelectedWorksheet] = useState('');
  
  // Bulk schedule form state
  const [startDate, setStartDate] = useState('');
  const [postTime, setPostTime] = useState('10:00');
  const [frequency, setFrequency] = useState('daily');
  const [intervalDays, setIntervalDays] = useState(1);
  const [statusLog, setStatusLog] = useState('Select a campaign from the dropdown to load its post sequence.');

  // Single post schedule state
  const [campaignPosts, setCampaignPosts] = useState([]);
  const [selectedSinglePostId, setSelectedSinglePostId] = useState('');
  const [singlePostTime, setSinglePostTime] = useState('');
  const [singlePostInfo, setSinglePostInfo] = useState('Choose a post to view its schedule status.');

  // Loading indicator for table
  const [isLoadingPosts, setIsLoadingPosts] = useState(false);

  useEffect(() => {
    fetchWorksheets();
    // Set default date to tomorrow
    const tom = new Date();
    tom.setDate(tom.getDate() + 1);
    setStartDate(tom.toISOString().split('T')[0]);
  }, []);

  const fetchWorksheets = async () => {
    try {
      const res = await fetch('/api/worksheets');
      const data = await res.json();
      setWorksheets((data.worksheets || []).filter(w => w !== 'Queue'));
    } catch (err) {
      console.error('Error fetching worksheets:', err);
    }
  };

  const handleWorksheetChange = (e) => {
    const ws = e.target.value;
    setSelectedWorksheet(ws);
    loadCampaignPosts(ws);
  };

  const loadCampaignPosts = async (worksheetName) => {
    if (!worksheetName) return;
    setIsLoadingPosts(true);
    try {
      const res = await fetch(`/api/campaign/posts?worksheet_name=${encodeURIComponent(worksheetName)}`);
      const data = await res.json();
      const posts = data.posts || [];
      setCampaignPosts(posts);
      
      // Reset single scheduler selections
      setSelectedSinglePostId('');
      setSinglePostTime('');
      setSinglePostInfo('Choose a post to view its schedule status.');
    } catch (err) {
      console.error('Error loading campaign posts:', err);
    } finally {
      setIsLoadingPosts(false);
    }
  };

  // Convert ISO scheduled time to local YYYY-MM-DDTHH:MM format for datetime-local input
  const getLocalDateTimeValue = (isoString) => {
    if (!isoString) return '';
    const dt = new Date(isoString);
    const offsetMs = dt.getTimezoneOffset() * 60 * 1000;
    return new Date(dt.getTime() - offsetMs).toISOString().slice(0, 16);
  };

  // Check if a post is locked for rescheduling
  const getPostLockStatus = (post) => {
    const isPastPostingTime = post.schedule_time && (new Date(post.schedule_time) <= new Date());
    const isPostingOrPosted = post.db_status === 'Posting' || post.db_status === 'Success' || post.sheet_status === 'Posted';
    return isPastPostingTime || isPostingOrPosted;
  };

  // Filter valid posts for single scheduler dropdown (non-locked, non-past)
  const validSingleSchedPosts = campaignPosts.filter(p => !getPostLockStatus(p));

  const handleSinglePostSelectChange = (postId) => {
    setSelectedSinglePostId(postId);
    const post = campaignPosts.find(p => p.post_id === postId);
    if (!post) return;

    if (post.schedule_time) {
      setSinglePostTime(getLocalDateTimeValue(post.schedule_time));
      setSinglePostInfo(
        `Topic: ${post.topic}\nSheet Status: ${post.sheet_status}\nDatabase Status: ${post.db_status || 'Pending'}\nScheduled Time: ${new Date(post.schedule_time).toLocaleString()}`
      );
    } else {
      // Set default to tomorrow at 10 AM
      const tom = new Date();
      tom.setDate(tom.getDate() + 1);
      tom.setHours(10, 0, 0, 0);
      setSinglePostTime(getLocalDateTimeValue(tom.toISOString()));
      setSinglePostInfo(`Topic: ${post.topic}\nSheet Status: ${post.sheet_status}\nStatus: Not Scheduled yet.`);
    }
  };

  // Handle single scheduler form submit
  const handleSingleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedWorksheet) {
      alert('Please select a campaign series first.');
      return;
    }
    if (!selectedSinglePostId) {
      alert('Please select a post first.');
      return;
    }
    if (!singlePostTime) {
      alert('Please select a date and time.');
      return;
    }

    const isoTime = new Date(singlePostTime).toISOString();
    setSinglePostInfo('Scheduling...');

    try {
      const res = await fetch('/api/campaign/update-single-schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          worksheet_name: selectedWorksheet,
          post_id: selectedSinglePostId,
          schedule_time: isoTime
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setSinglePostInfo(`Success: Scheduled ${selectedSinglePostId} successfully.`);
        setStatusLog(`Success: Scheduled post '${selectedSinglePostId}' for ${new Date(singlePostTime).toLocaleString()}.`);
        loadCampaignPosts(selectedWorksheet);
        onScheduleSuccess();
      } else {
        setSinglePostInfo(`Error: ${data.detail || 'Scheduling failed.'}`);
      }
    } catch (err) {
      setSinglePostInfo(`Network Error: ${err.message}`);
    }
  };

  // Inline table schedule update
  const handleInlineScheduleSave = async (postId, newTimeStr) => {
    if (!newTimeStr) {
      alert('Please select a date and time first.');
      return;
    }
    const isoTime = new Date(newTimeStr).toISOString();
    try {
      const res = await fetch('/api/campaign/update-single-schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          worksheet_name: selectedWorksheet,
          post_id: postId,
          schedule_time: isoTime
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setStatusLog(`Success: Updated schedule time for post '${postId}' to ${new Date(newTimeStr).toLocaleString()}.`);
        loadCampaignPosts(selectedWorksheet);
        onScheduleSuccess();
      } else {
        alert('Failed to update schedule: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error updating schedule: ' + err.message);
    }
  };

  // Bulk schedule
  const handleBulkScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedWorksheet) {
      alert('Please select a campaign series first.');
      return;
    }
    
    setStatusLog(`Scheduling campaign posts sequentially starting from ${startDate} at ${postTime}...`);

    try {
      const res = await fetch('/api/campaign/bulk-schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          worksheet_name: selectedWorksheet,
          start_date: startDate,
          posting_time: postTime,
          frequency: frequency,
          interval_days: intervalDays
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setStatusLog(`Success!\n\n${data.message}`);
        loadCampaignPosts(selectedWorksheet);
        onScheduleSuccess();
      } else {
        setStatusLog(`Error: ${data.detail || 'Bulk scheduling failed.'}`);
      }
    } catch (err) {
      setStatusLog(`Network Error: ${err.message}`);
    }
  };

  // Bulk unschedule
  const handleUnscheduleCampaign = async () => {
    if (!selectedWorksheet) {
      alert('Please select a campaign series first.');
      return;
    }

    if (!confirm(`Are you sure you want to remove ALL pending scheduled posts for the campaign series '${selectedWorksheet}'?`)) {
      return;
    }

    setStatusLog(`Unscheduling all pending posts for campaign '${selectedWorksheet}'...`);

    try {
      const res = await fetch('/api/campaign/unschedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          worksheet_name: selectedWorksheet
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setStatusLog(`Success!\n\n${data.message}`);
        loadCampaignPosts(selectedWorksheet);
        onScheduleSuccess();
      } else {
        setStatusLog(`Error: ${data.detail || 'Unscheduling failed.'}`);
      }
    } catch (err) {
      setStatusLog(`Network Error: ${err.message}`);
    }
  };

  return (
    <section className="content-section active">
      <header className="section-header">
        <h2>Campaign Automation (Cron Sequencer)</h2>
        <p>Select a Google Sheet campaign worksheet and bulk-schedule all posts sequentially.</p>
      </header>

      <div className="config-grid">
        {/* Settings Card */}
        <div className="card config-card">
          <h3>⚙️ Cron Sequencer Settings</h3>
          <form onSubmit={handleBulkScheduleSubmit} className="modal-form">
            <div className="form-group">
              <label>Select Campaign Series</label>
              <select
                value={selectedWorksheet}
                onChange={handleWorksheetChange}
                className="glass-input"
                required
                style={{ marginTop: '0.5rem' }}
              >
                <option value="" disabled>Select a campaign...</option>
                {worksheets.map(ws => (
                  <option key={ws} value={ws}>
                    {ws === '50DaysCampaign' ? '50-Day D2C Automation' : ws}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="form-group row-flex" style={{ marginTop: '1rem' }}>
              <div className="flex-col">
                <label>Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="glass-input"
                  required
                  style={{ marginTop: '0.5rem' }}
                />
              </div>
              <div className="flex-col">
                <label>Posting Time</label>
                <input
                  type="time"
                  value={postTime}
                  onChange={(e) => setPostTime(e.target.value)}
                  className="glass-input"
                  required
                  style={{ marginTop: '0.5rem' }}
                />
              </div>
            </div>

            <div className="form-group row-flex" style={{ marginTop: '1rem' }}>
              <div className="flex-col">
                <label>Posting Frequency</label>
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value)}
                  className="glass-input"
                  style={{ marginTop: '0.5rem' }}
                >
                  <option value="daily">Daily</option>
                  <option value="weekday">Every Weekday (Mon-Fri)</option>
                  <option value="custom">Custom Interval (Every X Days)</option>
                </select>
              </div>
              {frequency === 'custom' && (
                <div className="flex-col">
                  <label>Interval (Days)</label>
                  <input
                    type="number"
                    min="1"
                    value={intervalDays}
                    onChange={(e) => setIntervalDays(parseInt(e.target.value) || 1)}
                    className="glass-input"
                    required
                    style={{ marginTop: '0.5rem' }}
                  />
                </div>
              )}
            </div>

            <div className="form-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn secondary"
                style={{ padding: '0.8rem 1.5rem', borderRadius: '8px' }}
                onClick={handleUnscheduleCampaign}
                disabled={!selectedWorksheet}
              >
                Unschedule All
              </button>
              <button
                type="submit"
                className="btn primary"
                style={{ padding: '0.8rem 1.5rem', borderRadius: '8px' }}
                disabled={!selectedWorksheet}
              >
                Bulk Schedule Campaign
              </button>
            </div>
          </form>
        </div>

        {/* Status Log Card */}
        <div className="card config-card instructions" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <h3>💡 Automation Instructions</h3>
          <div className="status-log" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '1rem', whiteSpace: 'pre-line' }}>
            {statusLog}
          </div>
        </div>

        {/* Single Post Scheduler Card */}
        <div className="card config-card" id="single-schedule-card">
          <h3>🎯 Single Post Scheduler</h3>
          <form onSubmit={handleSingleScheduleSubmit} className="modal-form">
            <div className="form-group">
              <label>Select Campaign Post</label>
              <select
                value={selectedSinglePostId}
                onChange={(e) => handleSinglePostSelectChange(e.target.value)}
                className="glass-input"
                required
                style={{ marginTop: '0.5rem' }}
                disabled={!selectedWorksheet}
              >
                <option value="" disabled>Select a post...</option>
                {validSingleSchedPosts.map(p => (
                  <option key={p.post_id} value={p.post_id}>
                    {p.post_id} ({p.sheet_status || 'Pending'})
                  </option>
                ))}
              </select>
            </div>
            
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label>Posting Date & Time</label>
              <input
                type="datetime-local"
                value={singlePostTime}
                onChange={(e) => setSinglePostTime(e.target.value)}
                className="glass-input"
                required
                style={{ marginTop: '0.5rem' }}
                disabled={!selectedSinglePostId}
              />
            </div>
            
            <div style={{ fontSize: '0.85rem', color: 'var(--accent-neon-blue)', lineHeight: '1.4', minHeight: '2.5rem', marginTop: '0.75rem', whiteSpace: 'pre-line' }}>
              {singlePostInfo}
            </div>

            <div className="form-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifycontent: 'flex-end' }}>
              <button
                type="submit"
                className="btn primary"
                style={{ padding: '0.8rem 1.5rem', borderRadius: '8px' }}
                disabled={!selectedSinglePostId}
              >
                Schedule Post
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Campaign Post Sequence Table */}
      <div className="schedule-table-wrapper card" style={{ marginTop: '2rem', padding: '1.5rem' }}>
        <h3>Campaign Post Sequences</h3>
        <table className="schedule-table" style={{ width: '100%', marginTop: '1rem', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
              <th style={{ textAlign: 'left', padding: '0.75rem' }}>Post ID</th>
              <th style={{ textAlign: 'left', padding: '0.75rem' }}>Topic</th>
              <th style={{ textAlign: 'left', padding: '0.75rem' }}>Sheet Status</th>
              <th style={{ textAlign: 'left', padding: '0.75rem' }}>Scheduled Time</th>
              <th style={{ textAlign: 'left', padding: '0.75rem' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {isLoadingPosts ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                  Loading campaign posts...
                </td>
              </tr>
            ) : !selectedWorksheet ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                  Select a campaign above to load posts.
                </td>
              </tr>
            ) : campaignPosts.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                  No posts found in this campaign series.
                </td>
              </tr>
            ) : (
              campaignPosts.map(post => {
                const sheetStatus = (post.sheet_status || 'Pending').trim();
                let statusBadgeClass = 'badge';
                if (sheetStatus.toLowerCase() === 'approved' || sheetStatus.toLowerCase() === 'scheduled') {
                  statusBadgeClass += ' status-approved';
                } else if (sheetStatus.toLowerCase() === 'posted') {
                  statusBadgeClass += ' status-posted';
                } else {
                  statusBadgeClass += ' status-generating';
                }

                const isLocked = getPostLockStatus(post);
                
                return (
                  <tr key={post.post_id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                    <td style={{ padding: '0.75rem' }}><strong>{post.post_id}</strong></td>
                    <td style={{ padding: '0.75rem' }}>{post.topic}</td>
                    <td style={{ padding: '0.75rem' }}><span className={statusBadgeClass}>{sheetStatus}</span></td>
                    <td style={{ padding: '0.75rem' }}>
                      {!isLocked ? (
                        <input
                          type="datetime-local"
                          className="glass-input post-time-adjust"
                          value={getLocalDateTimeValue(post.schedule_time)}
                          onChange={(e) => {
                            const newTime = e.target.value;
                            setCampaignPosts(prev => prev.map(p => {
                              if (p.post_id === post.post_id) {
                                return { ...p, schedule_time: newTime ? new Date(newTime).toISOString() : null };
                              }
                              return p;
                            }));
                          }}
                          style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                        />
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                          {post.db_status === 'Posting'
                            ? '⚡ Publishing...'
                            : (post.sheet_status === 'Posted' ? 'Published' : 'Posting Time Reached')}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {!isLocked && post.schedule_time ? (
                        <button
                          className="btn primary"
                          style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                          onClick={() => handleInlineScheduleSave(post.post_id, post.schedule_time)}
                        >
                          Save
                        </button>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
