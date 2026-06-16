import React from 'react';

export default function ConfigView({ config }) {
  return (
    <section className="content-section active">
      <header className="section-header">
        <h2>System Configuration</h2>
        <p>Check the integration status of Google Sheets, Meta Graph API, and Cloudinary.</p>
      </header>

      <div className="config-grid">
        <div className="card config-card">
          <h3>🔑 Credential Environment</h3>
          <div className="config-item">
            <span>Google Sheets ID:</span>
            <code>{config?.google_sheet_id || 'Checking...'}</code>
          </div>
          <div className="config-item">
            <span>Google service account json:</span>
            {config?.google_creds_configured ? (
              <span className="badge status-posted">Connected</span>
            ) : (
              <span className="badge status-generating">Missing</span>
            )}
          </div>
          <div className="config-item">
            <span>Cloudinary Cloud:</span>
            {config?.cloudinary_configured ? (
              <span className="badge status-posted">Connected</span>
            ) : (
              <span className="badge status-generating">Missing</span>
            )}
          </div>
          <div className="config-item">
            <span>Instagram Account ID:</span>
            <code>{config?.instagram_account_id || 'Checking...'}</code>
          </div>
        </div>
        
        <div className="card config-card instructions">
          <h3>💡 Operational Rules</h3>
          <ul>
            <li style={{ marginBottom: '1rem' }}>
              <strong>Fully Automated:</strong> Once a post is scheduled (or next up in the campaign sequence), the background worker processes it with zero manual intervention.
            </li>
            <li style={{ marginBottom: '1rem' }}>
              <strong>Pre-generated URLs:</strong> Ensure Cloudinary slide links are filled out in the Google Sheet for automatic scheduling.
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
