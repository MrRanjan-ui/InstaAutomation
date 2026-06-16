import React, { useState, useEffect } from 'react';

export default function CalendarView({ onPreviewNavigate }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [scheduledJobs, setScheduledJobs] = useState([]);

  useEffect(() => {
    fetchScheduledJobs();
  }, []);

  const fetchScheduledJobs = async () => {
    try {
      const res = await fetch('/api/schedule/list');
      const data = await res.json();
      setScheduledJobs(data || []);
    } catch (err) {
      console.error('Error loading scheduled jobs for calendar:', err);
    }
  };

  const handlePrevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    
    // First day of month
    const firstDay = new Date(year, month, 1);
    const startOffset = firstDay.getDay(); // 0 is Sunday, 6 is Saturday
    
    // Number of days in month
    const totalDays = new Date(year, month + 1, 0).getDate();
    
    return { startOffset, totalDays, year, month };
  };

  const { startOffset, totalDays, year, month } = getDaysInMonth(currentDate);

  // Month names
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  // Helper to check if a day is today
  const isToday = (dayNum) => {
    const today = new Date();
    return today.getDate() === dayNum &&
           today.getMonth() === month &&
           today.getFullYear() === year;
  };

  // Generate calendar cells
  const cells = [];
  // Fill empty days for offset
  for (let i = 0; i < startOffset; i++) {
    cells.push({ isEmpty: true });
  }
  // Fill actual days of the month
  for (let i = 1; i <= totalDays; i++) {
    const cellDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
    
    // Find scheduled posts on this day
    const postsOnDay = scheduledJobs.filter(job => {
      if (!job.schedule_time) return false;
      const jobDate = new Date(job.schedule_time);
      const jobDateStr = `${jobDate.getFullYear()}-${String(jobDate.getMonth() + 1).padStart(2, '0')}-${String(jobDate.getDate()).padStart(2, '0')}`;
      return jobDateStr === cellDateStr;
    });

    // Sort posts by time on that day
    postsOnDay.sort((a, b) => new Date(a.schedule_time) - new Date(b.schedule_time));

    cells.push({
      isEmpty: false,
      dayNumber: i,
      dateString: cellDateStr,
      posts: postsOnDay
    });
  }

  return (
    <section className="content-section active">
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h2>Schedule Calendar</h2>
          <p>Visual monthly overview of all scheduled and published postings.</p>
        </div>
        
        {/* Month Navigation Controls */}
        <div className="calendar-controls" style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'var(--card-bg)', padding: '0.5rem 1rem', borderRadius: '12px', border: '1px solid var(--card-border)' }}>
          <button className="btn secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }} onClick={handlePrevMonth}>◀</button>
          <span style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: '1.1rem', minWidth: '140px', textAlign: 'center' }}>
            {monthNames[month]} {year}
          </span>
          <button className="btn secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }} onClick={handleNextMonth}>▶</button>
        </div>
      </header>

      {/* Calendar Grid Card */}
      <div className="card" style={{ padding: '1.5rem', overflowX: 'auto' }}>
        <div className="calendar-container" style={{ minWidth: '700px' }}>
          {/* Days of week headers */}
          <div className="calendar-weekdays" style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px', paddingBottom: '1rem', borderBottom: '1px solid var(--card-border)' }}>
            <div>Sun</div>
            <div>Mon</div>
            <div>Tue</div>
            <div>Wed</div>
            <div>Thu</div>
            <div>Fri</div>
            <div>Sat</div>
          </div>
          
          {/* Days grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gridAutoRows: 'minmax(120px, auto)', gap: '1px', background: 'var(--card-border)', marginTop: '1px' }}>
            {cells.map((cell, idx) => {
              if (cell.isEmpty) {
                return <div key={`empty-${idx}`} className="calendar-day empty"></div>;
              }
              
              return (
                <div
                  key={`day-${cell.dayNumber}`}
                  className={`calendar-day ${isToday(cell.dayNumber) ? 'today' : ''}`}
                >
                  <div className="calendar-day-number">{cell.dayNumber}</div>
                  
                  {cell.posts.map(post => {
                    const timeStr = new Date(post.schedule_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                    let statusClass = 'status-pending';
                    if (post.status === 'Posting') statusClass = 'status-posting';
                    else if (post.status === 'Success') statusClass = 'status-success';
                    else if (post.status === 'Failed') statusClass = 'status-failed';

                    const tooltipText = `Topic: ${post.topic || '-'}\nStatus: ${post.status}\nCampaign: ${post.source_sheet === '50DaysCampaign' ? '50-Day D2C Campaign' : post.source_sheet}`;

                    return (
                      <div
                        key={post.id}
                        className={`calendar-post-pill ${statusClass}`}
                        title={tooltipText}
                        onClick={() => onPreviewNavigate(post.post_id, post.source_sheet, post.row_index)}
                      >
                        {timeStr} | {post.post_id.slice(0, 15)}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
