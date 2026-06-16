import React from 'react';

export default function QueueView({ posts, onScheduleClick, onPreviewNavigate, isLoading }) {
  const getSlideUrls = (post) => {
    const urls = [];
    for (let i = 1; i <= 10; i++) {
      const val = post[`Slide_${i}_URL`] || post[`Slide_${i}_image`] || post[`Slide_${i}_Link`];
      if (val && typeof val === 'string' && val.startsWith('http')) {
        urls.push(val.trim());
      }
    }
    if (urls.length === 0) {
      Object.keys(post).forEach(k => {
        if (k.toLowerCase().includes('url') || k.toLowerCase().includes('link')) {
          const val = post[k];
          if (val && typeof val === 'string' && val.startsWith('http')) {
            urls.push(val.trim());
          }
        }
      });
    }
    return urls;
  };

  if (isLoading) {
    return (
      <section className="content-section active">
        <header className="section-header">
          <h2>Random Queue</h2>
          <p>Topic-based posts fetched from your primary Google Sheet queue tab.</p>
        </header>
        <div className="grid-layout">
          <div className="loading-skeleton-card"></div>
          <div className="loading-skeleton-card"></div>
        </div>
      </section>
    );
  }

  return (
    <section className="content-section active">
      <header className="section-header">
        <h2>Random Queue</h2>
        <p>Topic-based posts fetched from your primary Google Sheet queue tab.</p>
      </header>

      <div className="grid-layout">
        {posts.length === 0 ? (
          <p className="card" style={{ gridColumn: '1/-1' }}>No posts found in this sheet tab.</p>
        ) : (
          posts.map(post => {
            const status = (post.Status || 'Pending').trim();
            let badgeClass = 'badge';
            if (status.toLowerCase() === 'approved') badgeClass += ' status-approved';
            else if (status.toLowerCase() === 'generating') badgeClass += ' status-generating';
            else if (status.toLowerCase() === 'posted') badgeClass += ' status-posted';

            const slideUrls = getSlideUrls(post);

            return (
              <div
                key={post.Post_ID || Math.random()}
                className="card post-card"
                style={{ cursor: 'pointer' }}
                onClick={() => onPreviewNavigate(post.Post_ID, 'Queue', post.row_index)}
              >
                <div>
                  <div className="post-card-header">
                    <span className={badgeClass}>{status}</span>
                    <span className="slide-count-badge">🖼️ {slideUrls.length} Slides</span>
                  </div>
                  <h3>{post.Post_ID || 'Unnamed Post'}</h3>
                  <p className="caption-preview">{post.Caption || 'No caption text'}</p>
                </div>
                <div className="post-card-footer">
                  <span className="topic-label" style={{ fontSize: '0.8rem', color: 'var(--accent-neon-blue)' }}>
                    {post.Topic || ''}
                  </span>
                  <button
                    className="btn primary schedule-trigger-btn"
                    disabled={slideUrls.length === 0}
                    onClick={(e) => {
                      e.stopPropagation();
                      onScheduleClick(post, 'Queue');
                    }}
                  >
                    Schedule
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
