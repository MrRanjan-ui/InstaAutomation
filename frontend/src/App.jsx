import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import SystemDashboard from './components/SystemDashboard';
import CampaignView from './components/CampaignView';
import CampaignsDashboard from './components/CampaignsDashboard';
import CalendarView from './components/CalendarView';
import QueueView from './components/QueueView';
import AutomationView from './components/AutomationView';
import ScheduledJobsView from './components/ScheduledJobsView';
import ConfigView from './components/ConfigView';
import PostPreview from './components/PostPreview';
import ScheduleModal from './components/ScheduleModal';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [config, setConfig] = useState(null);
  const [posts, setPosts] = useState({ campaign_posts: [], random_posts: [] });
  const [isLoadingPosts, setIsLoadingPosts] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  // Routing state
  const [routeInfo, setRouteInfo] = useState({
    pathname: window.location.pathname,
    searchParams: new URLSearchParams(window.location.search)
  });

  // Modal state
  const [modalInfo, setModalInfo] = useState({
    isOpen: false,
    post: null,
    sourceTab: ''
  });

  // Listen for history popstate events
  useEffect(() => {
    const handlePopState = () => {
      setRouteInfo({
        pathname: window.location.pathname,
        searchParams: new URLSearchParams(window.location.search)
      });
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Fetch initial system configuration and posts data
  useEffect(() => {
    fetchConfig();
    fetchPostsData();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error('Error fetching config:', err);
    }
  };

  const fetchPostsData = async () => {
    try {
      setIsLoadingPosts(true);
      const res = await fetch('/api/posts');
      const data = await res.json();
      if (data.error) {
        setErrorMsg(data.error);
      } else {
        setPosts(data);
      }
    } catch (err) {
      setErrorMsg('Failed to communicate with scheduler API server.');
    } finally {
      setIsLoadingPosts(false);
    }
  };

  const handlePreviewNavigate = (postId, sourceSheet, rowIndex) => {
    const query = `?post_id=${encodeURIComponent(postId)}&source=${encodeURIComponent(sourceSheet)}${rowIndex ? `&row_index=${rowIndex}` : ''}`;
    window.history.pushState({}, '', `/preview${query}`);
    setRouteInfo({
      pathname: '/preview',
      searchParams: new URLSearchParams(query)
    });
  };

  const handleBackToDashboard = () => {
    window.history.pushState({}, '', '/');
    setRouteInfo({
      pathname: '/',
      searchParams: new URLSearchParams()
    });
    // Refresh post data when returning to dashboard
    fetchPostsData();
  };

  const handleOpenScheduleModal = (post, sourceTab) => {
    setModalInfo({
      isOpen: true,
      post,
      sourceTab
    });
  };

  const handleCloseScheduleModal = () => {
    setModalInfo({
      isOpen: false,
      post: null,
      sourceTab: ''
    });
  };

  // Check if we are on preview route
  if (routeInfo.pathname === '/preview') {
    const postId = routeInfo.searchParams.get('post_id');
    const sourceSheet = routeInfo.searchParams.get('source');
    const rowIndex = routeInfo.searchParams.get('row_index');

    return (
      <>
        <div className="glass-bg"></div>
        <PostPreview
          postId={postId}
          sourceSheet={sourceSheet}
          rowIndex={rowIndex}
          onBack={handleBackToDashboard}
        />
      </>
    );
  }

  return (
    <>
      <div className="glass-bg"></div>
      <div className="app-container">
        
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          config={config}
        />

        <main className="main-content">
          {errorMsg && (
            <div className="alert-banner">
              <span className="alert-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </span>
              <span className="alert-text">{errorMsg}</span>
              <button className="alert-close" onClick={() => setErrorMsg('')}>×</button>
            </div>
          )}

          {activeTab === 'dashboard' && (
            <SystemDashboard
              onTabNavigate={setActiveTab}
              onPreviewNavigate={handlePreviewNavigate}
            />
          )}

          {activeTab === 'campaign' && (
            <CampaignView
              posts={posts.campaign_posts}
              onScheduleClick={handleOpenScheduleModal}
              onPreviewNavigate={handlePreviewNavigate}
              isLoading={isLoadingPosts}
            />
          )}

          {activeTab === 'campaigns' && (
            <CampaignsDashboard
              onPreviewNavigate={handlePreviewNavigate}
            />
          )}

          {activeTab === 'calendar' && (
            <CalendarView
              onPreviewNavigate={handlePreviewNavigate}
            />
          )}

          {activeTab === 'queue' && (
            <QueueView
              posts={posts.random_posts}
              onScheduleClick={handleOpenScheduleModal}
              onPreviewNavigate={handlePreviewNavigate}
              isLoading={isLoadingPosts}
            />
          )}

          {activeTab === 'automation' && (
            <AutomationView
              onScheduleSuccess={fetchPostsData}
            />
          )}

          {activeTab === 'scheduled' && (
            <ScheduledJobsView onPreviewNavigate={handlePreviewNavigate} />
          )}

          {activeTab === 'config' && (
            <ConfigView
              config={config}
            />
          )}
        </main>
      </div>

      <ScheduleModal
        isOpen={modalInfo.isOpen}
        post={modalInfo.post}
        sourceTab={modalInfo.sourceTab}
        onClose={handleCloseScheduleModal}
        onScheduleSuccess={fetchPostsData}
      />
    </>
  );
}
