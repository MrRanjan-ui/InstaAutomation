import React, { useState, useEffect } from 'react';

const Icons = {
  plus: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  trash: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  ),
  edit: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  ),
  refresh: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  ),
  target: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  ),
  chat: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  ),
  info: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  )
};

export default function CommentAutomationView() {
  const [rules, setRules] = useState([]);
  const [logs, setLogs] = useState([]);
  const [igPosts, setIgPosts] = useState([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isPostSelectorOpen, setIsPostSelectorOpen] = useState(false);
  const [isLoadingPosts, setIsLoadingPosts] = useState(false);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);

  // Form State
  const [ruleId, setRuleId] = useState(null);
  const [ruleName, setRuleName] = useState('');
  const [selectedPostId, setSelectedPostId] = useState('all');
  const [selectedPostCaption, setSelectedPostCaption] = useState('All Posts / General');
  const [selectedPostThumbnail, setSelectedPostThumbnail] = useState('');
  const [keyword, setKeyword] = useState('');
  const [publicReply, setPublicReply] = useState('');
  const [privateReply, setPrivateReply] = useState('');
  const [requireFollow, setRequireFollow] = useState(false);

  useEffect(() => {
    fetchRules();
    fetchLogs();
    fetchIgPosts();
    
    // Auto-refresh logs every 15 seconds
    const interval = setInterval(() => {
      fetchLogs();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchRules = async () => {
    setIsLoadingRules(true);
    try {
      const res = await fetch('/api/automation/rules');
      const data = await res.json();
      setRules(data);
    } catch (err) {
      console.error('Error fetching rules:', err);
    } finally {
      setIsLoadingRules(false);
    }
  };

  const fetchLogs = async () => {
    setIsLoadingLogs(true);
    try {
      const res = await fetch('/api/automation/logs');
      const data = await res.json();
      setLogs(data);
    } catch (err) {
      console.error('Error fetching logs:', err);
    } finally {
      setIsLoadingLogs(false);
    }
  };

  const fetchIgPosts = async () => {
    setIsLoadingPosts(true);
    try {
      const res = await fetch('/api/instagram/posts');
      if (res.ok) {
        const data = await res.json();
        setIgPosts(data.data || []);
      }
    } catch (err) {
      console.error('Error fetching Instagram posts:', err);
    } finally {
      setIsLoadingPosts(false);
    }
  };

  const handleOpenCreateModal = () => {
    setRuleId(null);
    setRuleName('');
    setSelectedPostId('all');
    setSelectedPostCaption('All Posts / General');
    setSelectedPostThumbnail('');
    setKeyword('');
    setPublicReply('Sent you a DM! Check your inbox 📩');
    setPrivateReply('');
    setRequireFollow(false);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (rule) => {
    setRuleId(rule.id);
    setRuleName(rule.name);
    setSelectedPostId(rule.post_id);
    setSelectedPostCaption(rule.post_caption || (rule.post_id === 'all' ? 'All Posts / General' : `Post ID: ${rule.post_id}`));
    setKeyword(rule.keyword);
    setPublicReply(rule.public_reply);
    setPrivateReply(rule.private_reply);
    setRequireFollow(rule.require_follow);
    
    // Attempt to locate thumbnail from fetched posts
    const postObj = igPosts.find(p => p.id === rule.post_id);
    setSelectedPostThumbnail(postObj ? postObj.media_url : '');
    
    setIsModalOpen(true);
  };

  const handleSaveRule = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        id: ruleId,
        name: ruleName,
        post_id: selectedPostId,
        post_caption: selectedPostCaption,
        keyword: keyword,
        public_reply: publicReply,
        private_reply: privateReply,
        require_follow: requireFollow
      };
      
      const res = await fetch('/api/automation/rule/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setIsModalOpen(false);
        fetchRules();
      } else {
        alert('Failed to save rule: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error saving rule: ' + err.message);
    }
  };

  const handleDeleteRule = async (id) => {
    if (!confirm('Are you sure you want to delete this auto-DM rule?')) return;
    try {
      const res = await fetch(`/api/automation/rule/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchRules();
      }
    } catch (err) {
      alert('Error deleting rule: ' + err.message);
    }
  };

  const handleToggleRule = async (id) => {
    try {
      const res = await fetch(`/api/automation/rule/toggle/${id}`, { method: 'POST' });
      if (res.ok) {
        fetchRules();
      }
    } catch (err) {
      alert('Error toggling rule: ' + err.message);
    }
  };

  const selectPost = (post) => {
    if (post === 'all') {
      setSelectedPostId('all');
      setSelectedPostCaption('All Posts / General');
      setSelectedPostThumbnail('');
    } else {
      setSelectedPostId(post.id);
      setSelectedPostCaption(post.caption || `Post: ${post.id}`);
      setSelectedPostThumbnail(post.media_url);
    }
    setIsPostSelectorOpen(false);
  };

  return (
    <section className="content-section active">
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Comment Auto-DM Automation</h2>
          <p>Configure auto-replies and direct messages when users comment on your Instagram posts.</p>
        </div>
        <button className="btn primary" onClick={handleOpenCreateModal} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {Icons.plus} Create Rule
        </button>
      </header>

      {/* Rules Grid */}
      <div className="card" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>{Icons.target}</span>
          Active Automation Rules
        </h3>
        
        {isLoadingRules ? (
          <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>Loading rules...</p>
        ) : rules.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 2rem', color: 'var(--text-secondary)' }}>
            <p style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>No Comment Auto-DM rules configured yet.</p>
            <button className="btn secondary" onClick={handleOpenCreateModal}>Create your first rule</button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
            {rules.map(rule => (
              <div key={rule.id} className="card" style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--card-border)', padding: '1.2rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.8rem' }}>
                    <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>{rule.name}</h4>
                    <label className="switch" style={{ position: 'relative', display: 'inline-block', width: '38px', height: '20px' }}>
                      <input 
                        type="checkbox" 
                        checked={rule.is_active} 
                        onChange={() => handleToggleRule(rule.id)}
                        style={{ opacity: 0, width: 0, height: 0 }}
                      />
                      <span className={`slider round ${rule.is_active ? 'active' : ''}`} style={{
                        position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: rule.is_active ? 'var(--primary)' : '#555',
                        borderRadius: '34px', transition: '.3s',
                        display: 'flex', alignItems: 'center'
                      }}>
                        <span style={{
                          height: '14px', width: '14px', left: rule.is_active ? '20px' : '4px', bottom: '3px',
                          backgroundColor: 'white', borderRadius: '50%', position: 'absolute', transition: '.3s'
                        }} />
                      </span>
                    </label>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                    <strong>Trigger:</strong> Comments containing <span className="badge status-approved" style={{ fontSize: '0.75rem' }}>{rule.keyword === '*' ? 'Any comment' : rule.keyword}</span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                    <strong>Post:</strong> {rule.post_id === 'all' ? 'All Posts' : (rule.post_caption ? rule.post_caption.substring(0, 45) + '...' : `Post ${rule.post_id}`)}
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.8rem' }}>
                    <strong>Follow Gate:</strong> {rule.require_follow ? <span className="badge" style={{ background: 'rgba(235, 94, 40, 0.2)', color: '#eb5e28' }}>Required (2-Step)</span> : 'None (Immediate)'}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.8rem' }}>
                  <button className="btn secondary" onClick={() => handleOpenEditModal(rule)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    {Icons.edit} Edit
                  </button>
                  <button className="btn secondary" onClick={() => handleDeleteRule(rule.id)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', color: '#ff4d4d', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    {Icons.trash} Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Logs Table */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
            <span style={{ color: 'var(--text-secondary)' }}>{Icons.chat}</span>
            Activity and Message Logs
          </h3>
          <button className="btn secondary" onClick={fetchLogs} disabled={isLoadingLogs} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.5rem 1rem', fontSize: '0.85rem' }}>
            {Icons.refresh} Refresh Logs
          </button>
        </div>

        <div className="schedule-table-wrapper">
          <table className="schedule-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Time</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>User</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Comment</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '0.75rem' }}>Details / Operations</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                    No activity logs recorded yet. Automation triggers will be logged here.
                  </td>
                </tr>
              ) : (
                logs.map(log => {
                  let statusClass = 'badge';
                  if (log.status === 'processed') statusClass += ' status-posted'; // Green
                  else if (log.status === 'pending_follow') statusClass += ' status-approved'; // Orange
                  else if (log.status === 'ignored') statusClass += ' status-generating'; // Gray
                  else statusClass += ' status-generating'; // Fallback / Red-ish if failed (using CSS class mappings)
                  
                  // Custom styling override for failed
                  const isFailed = log.status === 'failed';
                  const failedStyle = isFailed ? { backgroundColor: 'rgba(239, 71, 111, 0.2)', color: '#ef476f' } : {};

                  return (
                    <tr key={log.id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                      <td style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <a href={`https://instagram.com/${log.username}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>
                          @{log.username}
                        </a>
                      </td>
                      <td style={{ padding: '0.75rem', fontSize: '0.85rem', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.comment_text}
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <span className={statusClass} style={failedStyle}>{log.status}</span>
                      </td>
                      <td style={{ padding: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {log.log || `Matched rule ID: ${log.rule_id || 'N/A'}`}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Rule Modal */}
      {isModalOpen && (
        <div className="modal active" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div className="card modal-content" style={{ width: '100%', maxWidth: '550px', padding: '2rem', maxHeight: '90vh', overflowY: 'auto' }}>
            <header className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3>{ruleId ? 'Edit Auto-DM Rule' : 'Create Auto-DM Rule'}</h3>
              <button className="close-modal-btn" onClick={() => setIsModalOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '1.5rem', cursor: 'pointer' }}>&times;</button>
            </header>

            <form onSubmit={handleSaveRule} className="modal-form" style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              <div className="form-group">
                <label>Rule Name</label>
                <input 
                  type="text" 
                  value={ruleName} 
                  onChange={(e) => setRuleName(e.target.value)} 
                  className="glass-input" 
                  placeholder="e.g. Ebook download automation"
                  required 
                  style={{ width: '100%', marginTop: '0.5rem' }}
                />
              </div>

              {/* Instagram Post Selector */}
              <div className="form-group" style={{ position: 'relative' }}>
                <label>Target Post</label>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginTop: '0.5rem' }}>
                  {selectedPostThumbnail && (
                    <img 
                      src={selectedPostThumbnail} 
                      alt="Thumbnail" 
                      style={{ width: '45px', height: '45px', borderRadius: '6px', objectFit: 'cover', border: '1px solid var(--card-border)' }} 
                    />
                  )}
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ fontSize: '0.9rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {selectedPostCaption}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {selectedPostId === 'all' ? 'Applies to any comment on any post' : `Post ID: ${selectedPostId}`}
                    </div>
                  </div>
                  <button 
                    type="button" 
                    className="btn secondary" 
                    onClick={() => setIsPostSelectorOpen(true)}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                  >
                    Select Post
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Trigger Keyword</label>
                <input 
                  type="text" 
                  value={keyword} 
                  onChange={(e) => setKeyword(e.target.value)} 
                  className="glass-input" 
                  placeholder="e.g. EBOOK (or type * to match any comment)" 
                  required 
                  style={{ width: '100%', marginTop: '0.5rem' }}
                />
                <small style={{ color: 'var(--text-secondary)', display: 'block', marginTop: '0.25rem' }}>
                  Matches when comment contains this keyword. Trigger is case-insensitive. Use <strong>*</strong> to trigger on all comments.
                </small>
              </div>

              {/* Require Follow Toggle */}
              <div className="form-group" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
                <div>
                  <label style={{ fontWeight: 500, marginBottom: '0.2rem', display: 'block' }}>Require Follow</label>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Verifies user follows @goran.dotin before sending DM.
                  </span>
                </div>
                <label className="switch" style={{ position: 'relative', display: 'inline-block', width: '38px', height: '20px' }}>
                  <input 
                    type="checkbox" 
                    checked={requireFollow} 
                    onChange={(e) => setRequireFollow(e.target.checked)}
                    style={{ opacity: 0, width: 0, height: 0 }}
                  />
                  <span className={`slider round ${requireFollow ? 'active' : ''}`} style={{
                    position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: requireFollow ? 'var(--primary)' : '#555',
                    borderRadius: '34px', transition: '.3s',
                    display: 'flex', alignItems: 'center'
                  }}>
                    <span style={{
                      height: '14px', width: '14px', left: requireFollow ? '20px' : '4px', bottom: '3px',
                      backgroundColor: 'white', borderRadius: '50%', position: 'absolute', transition: '.3s'
                    }} />
                  </span>
                </label>
              </div>

              <div className="form-group">
                <label>Public Comment Reply</label>
                <textarea 
                  value={publicReply} 
                  onChange={(e) => setPublicReply(e.target.value)} 
                  className="glass-input" 
                  placeholder="e.g. I just sent you a DM! Check your inbox 📩" 
                  rows={2}
                  style={{ width: '100%', marginTop: '0.5rem', resize: 'vertical' }}
                />
              </div>

              <div className="form-group">
                <label>Private DM Message</label>
                <textarea 
                  value={privateReply} 
                  onChange={(e) => setPrivateReply(e.target.value)} 
                  className="glass-input" 
                  placeholder="Here is the link you requested: https://example.com/ebook" 
                  required 
                  rows={4}
                  style={{ width: '100%', marginTop: '0.5rem', resize: 'vertical' }}
                />
              </div>

              <div className="form-actions" style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button type="button" className="btn secondary" onClick={() => setIsModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn primary">Save Rule</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Visual Post Selector Modal */}
      {isPostSelectorOpen && (
        <div className="modal active" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1100 }}>
          <div className="card modal-content" style={{ width: '100%', maxWidth: '650px', padding: '2rem', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
            <header className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3>Select Instagram Post</h3>
              <button className="close-modal-btn" onClick={() => setIsPostSelectorOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '1.5rem', cursor: 'pointer' }}>&times;</button>
            </header>

            <div style={{ overflowY: 'auto', flex: 1, paddingRight: '0.5rem' }}>
              {isLoadingPosts ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>Loading posts from Instagram...</p>
              ) : (
                <div>
                  {/* All Posts option */}
                  <div 
                    onClick={() => selectPost('all')}
                    className="card"
                    style={{ 
                      padding: '1rem', 
                      marginBottom: '1rem', 
                      cursor: 'pointer', 
                      background: selectedPostId === 'all' ? 'rgba(var(--primary-rgb), 0.1)' : 'rgba(255, 255, 255, 0.02)',
                      border: selectedPostId === 'all' ? '1.5px solid var(--primary)' : '1px solid var(--card-border)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      fontWeight: 600
                    }}
                  >
                    <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'black' }}>
                      🌟
                    </div>
                    <div>
                      <div>All Posts (General Rule)</div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Trigger rule for comments on any published post</span>
                    </div>
                  </div>

                  {/* Grid of posts */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                    {igPosts.map(post => (
                      <div 
                        key={post.id} 
                        onClick={() => selectPost(post)}
                        style={{
                          cursor: 'pointer',
                          borderRadius: '8px',
                          overflow: 'hidden',
                          position: 'relative',
                          border: selectedPostId === post.id ? '2px solid var(--primary)' : '1px solid var(--card-border)',
                          aspectRatio: '1',
                          background: 'black'
                        }}
                      >
                        {post.media_type === 'VIDEO' || post.media_url?.includes('.mp4') ? (
                          <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                            📹 Video
                          </div>
                        ) : (
                          <img 
                            src={post.media_url} 
                            alt={post.caption} 
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                          />
                        )}
                        <div style={{
                          position: 'absolute',
                          bottom: 0, left: 0, right: 0,
                          background: 'linear-gradient(transparent, rgba(0,0,0,0.85))',
                          padding: '0.5rem',
                          color: 'white',
                          fontSize: '0.7rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {post.caption || '(No caption)'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button className="btn secondary" onClick={() => setIsPostSelectorOpen(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
