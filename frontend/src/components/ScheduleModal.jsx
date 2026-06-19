import React, { useState, useEffect } from 'react';

export default function ScheduleModal({ isOpen, post, sourceTab, onClose, onScheduleSuccess }) {
  const [scheduleType, setScheduleType] = useState('now');
  const [scheduleTime, setScheduleTime] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localSlides, setLocalSlides] = useState([]);
  const [loadingSlides, setLoadingSlides] = useState(false);

  useEffect(() => {
    if (isOpen && post) {
      setLocalSlides([]);
      // Check if we already have slide URLs from sheet data
      const urls = [];
      for (let i = 1; i <= 10; i++) {
        const val = post[`Slide_${i}_URL`] || post[`Slide_${i}_image`] || post[`Slide_${i}_Link`];
        if (val && typeof val === 'string' && val.startsWith('http')) {
          urls.push(val.trim());
        }
      }
      
      if (urls.length > 0) {
        setLocalSlides(urls);
      } else {
        // Fetch details to find local slides on disk
        setLoadingSlides(true);
        const pId = post.Post_ID || post.post_id;
        fetch(`/api/post/details?post_id=${encodeURIComponent(pId)}&source_sheet=${encodeURIComponent(sourceTab)}&row_index=${post.row_index}`)
          .then(res => res.json())
          .then(data => {
            if (data.local_slides && data.local_slides.length > 0) {
              setLocalSlides(data.local_slides);
            }
          })
          .catch(err => console.error("Error fetching local slides:", err))
          .finally(() => setLoadingSlides(false));
      }
    }
  }, [isOpen, post, sourceTab]);

  if (!isOpen || !post) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Prepare slide URLs
    const targetSlideUrls = localSlides.map(url => {
      if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
      }
      return `${window.location.origin}${url}`;
    });

    if (scheduleType === 'now') {
      const payload = {
        post_id: post.Post_ID || post.post_id,
        source_sheet: sourceTab,
        row_index: post.row_index,
        caption: post.Caption || '',
        slide_urls: targetSlideUrls
      };

      try {
        setIsSubmitting(true);
        const res = await fetch('/api/publish/now', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        
        const contentType = res.headers.get('content-type');
        let data = {};
        if (contentType && contentType.includes('application/json')) {
          data = await res.json();
        } else {
          const text = await res.text();
          throw new Error(`Server returned non-JSON response (${res.status}): ${text.substring(0, 100)}...`);
        }

        if (res.ok && data.status === 'success') {
          alert(`Successfully published to Instagram! IG Post ID: ${data.published_id}`);
          onScheduleSuccess();
          onClose();
        } else {
          alert('Publishing failed: ' + (data.detail || 'Unknown error'));
        }
      } catch (err) {
        alert('Error publishing post: ' + err.message);
      } finally {
        setIsSubmitting(false);
      }
    } else {
      if (!scheduleTime) {
        alert('Please select a target date and time.');
        return;
      }
      const targetTime = new Date(scheduleTime).toISOString();

      const payload = {
        post_id: post.Post_ID || post.post_id,
        topic: post.Topic || '',
        source_sheet: sourceTab,
        caption: post.Caption || '',
        slide_urls: targetSlideUrls,
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
        
        const contentType = res.headers.get('content-type');
        let data = {};
        if (contentType && contentType.includes('application/json')) {
          data = await res.json();
        } else {
          const text = await res.text();
          throw new Error(`Server returned non-JSON response (${res.status}): ${text.substring(0, 100)}...`);
        }

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
    }
  };

  return (
    <div className="modal">
      <div className="modal-content card">
        <span className="close-modal" onClick={onClose}>&times;</span>
        <h3>Schedule: {post.Topic || post.Post_ID || post.post_id}</h3>
        <p className="subtitle" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Post ID: {post.Post_ID || post.post_id} | Source: {sourceTab}
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
              {loadingSlides ? (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Loading slides...</span>
              ) : localSlides.map((url, idx) => (
                <img
                  key={idx}
                  src={url}
                  alt={`Slide ${idx + 1}`}
                  className="preview-thumb"
                />
              ))}
              {!loadingSlides && localSlides.length === 0 && (
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
            <button type="submit" className="btn primary" disabled={isSubmitting || localSlides.length === 0}>
              {isSubmitting ? (scheduleType === 'now' ? 'Publishing...' : 'Scheduling...') : (scheduleType === 'now' ? 'Publish Now' : 'Confirm Schedule')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
