import React, { useState, useEffect } from 'react';

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
              <th>Action/Log</th>
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
                        <button className="btn secondary" onClick={() => handleDeleteJob(job.id)}>
                          Delete
                        </button>
                      )}
                      {job.status === 'Success' && (
                        <span style={{ color: 'var(--success-border)', fontSize: '0.85rem' }}>
                          ID: {job.published_id}
                        </span>
                      )}
                      {job.status === 'Failed' && (
                        <span
                          style={{ color: 'var(--error-border)', fontSize: '0.85rem' }}
                          title={job.error_message}
                        >
                          ⚠️ Failed
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
