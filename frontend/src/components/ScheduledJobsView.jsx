import React, { useState, useEffect } from 'react';

const Icons = {
  warning: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  trash: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  )
};

export default function ScheduledJobsView() {
  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/schedule/list');
      const data = await res.json();
      setJobs(data || []);
    } catch (err) {
      console.error('Error fetching scheduled jobs list:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!confirm('Are you sure you want to delete this scheduled post?')) return;
    try {
      const res = await fetch(`/api/schedule/delete/${jobId}`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        fetchJobs();
      } else {
        alert('Delete failed');
      }
    } catch (err) {
      console.error('Delete job error:', err);
    }
  };

  return (
    <section className="content-section active">
      <header className="section-header">
        <h2>Scheduled & Published Jobs</h2>
        <p>Track live execution, pending schedules, and API publishing logs.</p>
      </header>

      <div className="schedule-table-wrapper card">
        <table className="schedule-table">
          <thead>
            <tr>
              <th>Post ID</th>
              <th>Source Tab</th>
              <th>Topic</th>
              <th>Schedule Time</th>
              <th>Status</th>
              <th>Action / Details</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                  Loading scheduled jobs...
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                  No jobs scheduled yet.
                </td>
              </tr>
            ) : (
              jobs.map(job => {
                let badgeClass = 'badge';
                if (job.status === 'Pending') badgeClass += ' status-generating';
                else if (job.status === 'Posting') badgeClass += ' status-approved';
                else if (job.status === 'Success') badgeClass += ' status-posted';
                else if (job.status === 'Failed') badgeClass += ' status-failed';

                const dateLocal = new Date(job.schedule_time).toLocaleString();

                return (
                  <tr key={job.id}>
                    <td><strong>{job.post_id}</strong></td>
                    <td><span className="badge">{job.source_sheet}</span></td>
                    <td>{job.topic || '-'}</td>
                    <td>{dateLocal}</td>
                    <td><span className={badgeClass}>{job.status}</span></td>
                    <td>
                      {job.status === 'Pending' && (
                        <button className="btn secondary" style={{ padding: '0.35rem 0.65rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }} onClick={() => handleDeleteJob(job.id)}>
                          {Icons.trash} Delete
                        </button>
                      )}
                      {job.status === 'Success' && (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                          ID: {job.published_id ? job.published_id.slice(0, 12) + '...' : 'Published'}
                        </span>
                      )}
                      {job.status === 'Failed' && (
                        <span
                          style={{ color: '#f87171', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                          title={job.error_message}
                        >
                          {Icons.warning} Failed
                        </span>
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
