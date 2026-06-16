import React from 'react';

const Icons = {
  key: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
    </svg>
  ),
  bookOpen: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  )
};

export default function ConfigView({ config }) {
  return (
    <section className="content-section active">
      <header className="section-header">
        <h2>System Configuration</h2>
        <p>Check the integration status of Google Sheets, Meta Graph API, and Cloudinary.</p>
      </header>

      <div className="config-grid">
        <div className="card config-card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.2rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'inline-flex' }}>{Icons.key}</span>
            Credential Environment
          </h3>
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
            <span>MongoDB Database:</span>
            {config?.mongodb_configured ? (
              <span className="badge status-posted">Connected</span>
            ) : (
              <span className="badge status-generating">Missing</span>
            )}
          </div>
          <div className="config-item">
            <span>Instagram Account ID:</span>
            <code>{config?.instagram_account_id || 'Checking...'}</code>
          </div>
          {config?.token_status && (
            <>
              <div className="config-item" style={{ borderTop: '1px solid var(--card-border)', paddingTop: '0.8rem', marginTop: '0.8rem' }}>
                <span>Token Status:</span>
                <span className={`badge ${config.token_status.is_valid ? 'status-posted' : 'status-failed'}`}>
                  {config.token_status.is_valid ? 'Valid' : 'Invalid/Expired'}
                </span>
              </div>
              {config.token_status.is_valid && (
                <>
                  <div className="config-item">
                    <span>Token Scope Count:</span>
                    <code>{config.token_status.scopes?.length || 0} scopes authorized</code>
                  </div>
                  <div className="config-item">
                    <span>Days Until Expiry:</span>
                    <span style={{ 
                      fontWeight: 600,
                      color: config.token_status.days_remaining < 3 ? '#ef4444' :
                             config.token_status.days_remaining < 14 ? '#f59e0b' :
                             'var(--accent-emerald)'
                    }}>
                      {config.token_status.days_remaining > 365 ? 'Never (Long-lived)' : `${config.token_status.days_remaining} days`}
                    </span>
                  </div>
                  {config.token_status.expires_at && (
                    <div className="config-item">
                      <span>Expires At:</span>
                      <code>{new Date(config.token_status.expires_at).toLocaleString()}</code>
                    </div>
                  )}
                  {config.token_status.app_name && (
                    <div className="config-item">
                      <span>Registered App:</span>
                      <code>{config.token_status.app_name}</code>
                    </div>
                  )}
                </>
              )}
              {config.token_status.error && (
                <div className="config-item" style={{ color: '#ef4444', fontSize: '0.8rem' }}>
                  <span>Error:</span>
                  <code>{config.token_status.error}</code>
                </div>
              )}
            </>
          )}
        </div>
        
        <div className="card config-card instructions">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.2rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'inline-flex' }}>{Icons.bookOpen}</span>
            Operational Rules
          </h3>
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
