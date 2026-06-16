import React, { useState, useEffect } from 'react';

export default function PostPreview({ postId, sourceSheet, rowIndex, onBack }) {
  const [postDetails, setPostDetails] = useState(null);
  const [activeSlideIdx, setActiveSlideIdx] = useState(0);
  const [scheduleType, setScheduleType] = useState('now');
  const [scheduleTime, setScheduleTime] = useState('');
  const [showToast, setShowToast] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchPostDetails();
  }, [postId, sourceSheet, rowIndex]);

  const fetchPostDetails = async () => {
    try {
      setIsLoading(true);
      const url = `/api/post/details?post_id=${encodeURIComponent(postId)}&source_sheet=${encodeURIComponent(sourceSheet)}${rowIndex ? `&row_index=${rowIndex}` : ''}`;
      const res = await fetch(url);
      const data = await res.json();
      setPostDetails(data);
      setActiveSlideIdx(0);
    } catch (err) {
      console.error('Error fetching post details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const copyCaption = () => {
    if (!postDetails?.data?.Caption) return;
    navigator.clipboard.writeText(postDetails.data.Caption);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 2000);
  };

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!postDetails) return;

    let targetTime = new Date().toISOString();
    if (scheduleType === 'later') {
      if (!scheduleTime) {
        alert('Please select a target date and time.');
        return;
      }
      targetTime = new Date(scheduleTime).toISOString();
    }

    // Prepare slide URLs
    const slideUrls = postDetails.local_slides && postDetails.local_slides.length > 0
      ? postDetails.local_slides.map(path => `${window.location.origin}${path}`)
      : [];

    // If local slides are empty, extract from sheet data row
    if (slideUrls.length === 0 && postDetails.data) {
      for (let i = 1; i <= 10; i++) {
        const val = postDetails.data[`Slide_${i}_URL`] || postDetails.data[`Slide_${i}_image`] || postDetails.data[`Slide_${i}_Link`];
        if (val && typeof val === 'string' && val.startsWith('http')) {
          slideUrls.push(val.trim());
        }
      }
    }

    const payload = {
      post_id: postDetails.post_id,
      topic: postDetails.data?.Topic || '',
      source_sheet: postDetails.source_sheet,
      caption: postDetails.data?.Caption || '',
      slide_urls: slideUrls,
      schedule_time: targetTime,
      row_index: postDetails.row_index
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
        alert(`Successfully scheduled ${postDetails.post_id}!`);
        fetchPostDetails();
      } else {
        alert('Scheduling failed: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error scheduling post: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: '2.5rem', maxWidth: '1400px', margin: '0 auto', minHeight: '100vh' }}>
        <header className="preview-header">
          <div>
            <span className="back-link" onClick={onBack}>← Back to Dashboard</span>
            <h1 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '2.2rem', fontWeight: 800, marginTop: '0.5rem' }}>
              Loading Post Preview...
            </h1>
          </div>
        </header>
        <div className="preview-layout">
          <div className="card slide-viewer-card">
            <div className="active-slide-placeholder">Loading slide assets...</div>
          </div>
        </div>
      </div>
    );
  }

  if (!postDetails) {
    return (
      <div style={{ padding: '2.5rem', maxWidth: '1400px', margin: '0 auto', minHeight: '100vh' }}>
        <header className="preview-header">
          <div>
            <span className="back-link" onClick={onBack}>← Back to Dashboard</span>
            <h1 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '2.2rem', fontWeight: 800, marginTop: '0.5rem', color: 'var(--error-border)' }}>
              Error Loading Post
            </h1>
            <p>Post details could not be found or fetched.</p>
          </div>
        </header>
      </div>
    );
  }

  const slides = postDetails.local_slides || [];
  const activeSlideSrc = slides[activeSlideIdx];
  const postStatus = postDetails.data?.Status || 'Pending';

  let statusBadgeClass = 'badge';
  if (postStatus.toLowerCase() === 'approved' || postStatus.toLowerCase() === 'scheduled') {
    statusBadgeClass += ' status-approved';
  } else if (postStatus.toLowerCase() === 'posted') {
    statusBadgeClass += ' status-posted';
  } else {
    statusBadgeClass += ' status-generating';
  }

  return (
    <div style={{ padding: '2.5rem', maxWidth: '1400px', margin: '0 auto', minHeight: '100vh' }}>
      {/* Header */}
      <header className="preview-header">
        <div>
          <span className="back-link" onClick={onBack}>← Back to Dashboard</span>
          <h1 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '2.2rem', fontWeight: 800, marginTop: '0.5rem' }}>
            {postDetails.data?.Topic || postDetails.post_id}
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Post ID: {postDetails.post_id} | Row Index: {postDetails.row_index}
          </p>
        </div>
        <div>
          <span className={statusBadgeClass}>{postStatus}</span>
        </div>
      </header>

      {/* Main Layout */}
      <div className="preview-layout">
        {/* Left Pane: Slide Viewer */}
        <div className="card slide-viewer-card">
          <h2 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '1.25rem' }}>Slides Preview</h2>
          
          <div className="active-slide-container">
            {slides.length > 0 ? (
              <img
                src={activeSlideSrc}
                alt={`Slide ${activeSlideIdx + 1}`}
                className="active-slide-img"
              />
            ) : (
              <div className="active-slide-placeholder">No slide images available for rendering</div>
            )}
          </div>

          <div className="slide-controls">
            <button
              className="btn secondary"
              disabled={activeSlideIdx === 0}
              onClick={() => setActiveSlideIdx(prev => prev - 1)}
            >
              ◀ Previous
            </button>
            <span className="slide-indicator">
              Slide {slides.length > 0 ? activeSlideIdx + 1 : 0} of {slides.length}
            </span>
            <button
              className="btn secondary"
              disabled={activeSlideIdx === slides.length - 1 || slides.length === 0}
              onClick={() => setActiveSlideIdx(prev => prev + 1)}
            >
              Next ▶
            </button>
          </div>

          <div className="slides-filmstrip">
            {slides.map((src, idx) => (
              <img
                key={idx}
                src={src}
                alt={`Thumb ${idx + 1}`}
                className={`filmstrip-thumb ${idx === activeSlideIdx ? 'active' : ''}`}
                onClick={() => setActiveSlideIdx(idx)}
              />
            ))}
          </div>
        </div>

        {/* Right Pane: Caption & Schedule */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Caption Card */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '1.25rem' }}>Caption & Text Copy</h2>
              <div style={{ position: 'relative' }}>
                <button className="btn secondary" style={{ padding: '0.4rem 0.8rem' }} onClick={copyCaption}>
                  📋 Copy
                </button>
                <span className={`copy-success-toast ${showToast ? 'show' : ''}`} style={{ position: 'absolute', right: '100%', top: '5px' }}>
                  Copied!
                </span>
              </div>
            </div>
            <textarea
              className="glass-input caption-textarea"
              value={postDetails.data?.Caption || ''}
              readOnly
            />
          </div>

          {/* Quick Action / Schedule Card */}
          <div className="card">
            <h2 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '1.25rem', marginBottom: '1rem' }}>Schedule or Publish</h2>
            
            <div className="meta-grid">
              <div className="meta-box">
                <span>Source Sheet</span>
                <strong>{postDetails.source_sheet}</strong>
              </div>
              <div className="meta-box">
                <span>Row Index</span>
                <strong>{postDetails.row_index}</strong>
              </div>
            </div>

            <form onSubmit={handleScheduleSubmit} className="modal-form" style={{ marginTop: 0 }}>
              <div className="form-group row-flex">
                <div className="flex-col">
                  <label>Schedule Type</label>
                  <select
                    className="glass-input"
                    value={scheduleType}
                    onChange={(e) => setScheduleType(e.target.value)}
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
                      className="glass-input"
                      value={scheduleTime}
                      onChange={(e) => setScheduleTime(e.target.value)}
                      required
                    />
                  </div>
                )}
              </div>
              
              <div className="form-actions" style={{ marginTop: '0.5rem' }}>
                <button
                  type="submit"
                  className="btn primary"
                  disabled={isSubmitting || slides.length === 0}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  {isSubmitting ? 'Scheduling...' : 'Confirm Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
