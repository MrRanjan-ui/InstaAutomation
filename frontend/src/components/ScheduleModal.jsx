import React, { useState } from 'react';

export default function ScheduleModal({ isOpen, post, sourceTab, onClose, onScheduleSuccess }) {
  const [scheduleType, setScheduleType] = useState('now');
  const [scheduleTime, setScheduleTime] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !post) return null;

  // Extract slide URLs
  const slideUrls = [];
  for (let i = 1; i <= 10; i++) {
    const val = post[`Slide_${i}_URL`] || post[`Slide_${i}_image`] || post[`Slide_${i}_Link`];
    if (val && typeof val === 'string' && val.startsWith('http')) {
      slideUrls.push(val.trim());
    }
  }
  if (slideUrls.length === 0) {
    Object.keys(post).forEach(k => {
      if (k.toLowerCase().includes('url') || k.toLowerCase().includes('link')) {
        const val = post[k];
        if (val && typeof val === 'string' && val.startsWith('http')) {
          slideUrls.push(val.trim());
        }
      }
    });
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    let targetTime = new Date().toISOString();
    
    if (scheduleType === 'later') {
      if (!scheduleTime) {
        alert('Please select a target date and time.');
        return;
      }
      targetTime = new Date(scheduleTime).toISOString();
    }

    const payload = {
      post_id: post.Post_ID,
      topic: post.Topic || '',
      source_sheet: sourceTab,
      caption: post.Caption || '',
      slide_urls: slideUrls,
      schedule_time: targetTime,
      row_index: post.row_index
    };

    try {
      setIsSubmitting(true);
      const res = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'success') {
        onScheduleSuccess();
        onClose();
      } else {
        alert('Scheduling failed: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error scheduling post: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal">
      <div className="modal-content card">
        <span className="close-modal" onClick={onClose}>&times;</span>
        <h3>Schedule: {post.Topic || post.Post_ID}</h3>
        <p className="subtitle" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Post ID: {post.Post_ID} | Source: {sourceTab}
        </p>
        
        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>Caption Preview</label>
            <textarea
              value={post.Caption || ''}
              rows={6}
              readOnly
              className="glass-input"
              style={{ resize: 'none' }}
            />
          </div>
          
          <div className="form-group">
            <label>Slides Preview</label>
            <div className="slides-preview-container">
              {slideUrls.map((url, idx) => (
                <img
                  key={idx}
                  src={url}
                  alt={`Slide ${idx + 1}`}
                  className="preview-thumb"
                />
              ))}
              {slideUrls.length === 0 && (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  No slide assets available in Google Sheet row
                </span>
              )}
            </div>
          </div>
          
          <div className="form-group row-flex">
            <div className="flex-col">
              <label>Schedule Type</label>
              <select
                value={scheduleType}
                onChange={(e) => setScheduleType(e.target.value)}
                className="glass-input"
              >
                <option value="now">Post Now (Immediate)</option>
                <option value="later">Post at Specific Time</option>
              </select>
            </div>
            
            {scheduleType === 'later' && (
              <div className="flex-col">
                <label>Select Date & Time</label>
                <input
                  type="datetime-local"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="glass-input"
                  required
                />
              </div>
            )}
          </div>
          
          <div className="form-actions">
            <button type="button" className="btn secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn primary" disabled={isSubmitting || slideUrls.length === 0}>
              {isSubmitting ? 'Scheduling...' : 'Confirm Schedule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
