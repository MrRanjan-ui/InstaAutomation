document.addEventListener("DOMContentLoaded", () => {
    // Current state values
    let campaignPosts = [];
    let randomPosts = [];
    let selectedPost = null;

    // ─── Sidebar Navigation ────────────────────────────────────
    const navButtons = document.querySelectorAll(".nav-btn");
    const sections = document.querySelectorAll(".content-section");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            navButtons.forEach(b => b.classList.remove("active"));
            sections.forEach(s => s.classList.remove("active"));
            
            btn.classList.add("active");
            const targetId = btn.getAttribute("data-target");
            document.getElementById(targetId).classList.add("active");
        });
    });

    // ─── Fetch Data on Startup ────────────────────────────────
    fetchConfig();
    fetchPosts();
    fetchScheduledJobs();

    // ─── Fetch Configuration Info ─────────────────────────────
    async function fetchConfig() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            
            document.getElementById("cfg-sheet-id").innerText = data.google_sheet_id || "None";
            
            const credsBadge = document.getElementById("cfg-creds-status");
            if (data.google_creds_configured) {
                credsBadge.innerText = "Connected";
                credsBadge.className = "badge status-approved";
            } else {
                credsBadge.innerText = "Missing";
                credsBadge.className = "badge status-generating";
            }

            const cloudBadge = document.getElementById("cfg-cloudinary-status");
            if (data.cloudinary_configured) {
                cloudBadge.innerText = "Connected";
                cloudBadge.className = "badge status-approved";
            } else {
                cloudBadge.innerText = "Missing";
                cloudBadge.className = "badge status-generating";
            }

            document.getElementById("cfg-ig-id").innerText = data.instagram_account_id || "None";
            if (data.instagram_account_id !== "Not Configured") {
                document.getElementById("ig-account-name").innerText = `@goran.dotin (Active)`;
            }
        } catch (err) {
            console.error("Config fetch failed", err);
        }
    }

    // ─── Fetch and Render Posts ────────────────────────────────
    async function fetchPosts() {
        const campaignGrid = document.getElementById("campaign-grid");
        const randomGrid = document.getElementById("random-grid");

        try {
            const res = await fetch("/api/posts");
            const data = await res.json();

            if (data.error) {
                showErrorBanner(data.error);
                campaignGrid.innerHTML = `<p class="card" style="grid-column: 1/-1;">⚠️ ${data.error}</p>`;
                randomGrid.innerHTML = `<p class="card" style="grid-column: 1/-1;">⚠️ ${data.error}</p>`;
                return;
            }

            campaignPosts = data.campaign_posts || [];
            randomPosts = data.random_posts || [];

            renderPostGrid(campaignPosts, campaignGrid, "50DaysCampaign");
            renderPostGrid(randomPosts, randomGrid, "Queue");
        } catch (err) {
            showErrorBanner("Failed to communicate with scheduler API server.");
        }
    }

    function renderPostGrid(posts, container, sourceTab) {
        container.innerHTML = "";
        
        if (posts.length === 0) {
            container.innerHTML = `<p class="card" style="grid-column: 1/-1;">No posts found in this sheet tab.</p>`;
            return;
        }

        posts.forEach(post => {
            const card = document.createElement("div");
            card.className = "card post-card";

            const status = (post.Status || "Pending").trim();
            let badgeClass = "badge";
            if (status.toLowerCase() === "approved") badgeClass += " status-approved";
            else if (status.toLowerCase() === "generating") badgeClass += " status-generating";
            else if (status.toLowerCase() === "posted") badgeClass += " status-posted";

            // Extract slide URLs if they exist in the record
            const slideUrls = getSlideUrlsFromRow(post);

            card.innerHTML = `
                <div class="post-card-header">
                    <span class="${badgeClass}">${status}</span>
                    <span class="slide-count-badge">🖼️ ${slideUrls.length} Slides</span>
                </div>
                <h3>${post.Post_ID || "Unnamed Post"}</h3>
                <p class="caption-preview">${post.Caption || "No caption text"}</p>
                <div class="post-card-footer">
                    <span class="topic-label" style="font-size: 0.8rem; color: var(--accent-neon-blue);">${post.Topic || ""}</span>
                    <button class="btn primary schedule-trigger-btn" ${slideUrls.length === 0 ? 'disabled' : ''}>
                        Schedule
                    </button>
                </div>
            `;

            // Setup Preview redirection on card click (excluding schedule button)
            card.style.cursor = "pointer";
            card.addEventListener("click", (e) => {
                if (e.target.closest(".schedule-trigger-btn")) {
                    return;
                }
                const url = `/preview?post_id=${encodeURIComponent(post.Post_ID)}&source=${encodeURIComponent(sourceTab)}&row_index=${post.row_index}`;
                window.location.href = url;
            });

            // Setup Modal trigger
            const scheduleBtn = card.querySelector(".schedule-trigger-btn");
            if (scheduleBtn) {
                scheduleBtn.addEventListener("click", (e) => {
                    e.stopPropagation(); // Prevent card click trigger
                    openScheduleModal(post, sourceTab, slideUrls);
                });
            }

            container.appendChild(card);
        });
    }

    // Extract slide Cloudinary/public links from the row columns
    function getSlideUrlsFromRow(row) {
        const urls = [];
        // Loop columns to find Slide_1_URL, Slide_2_URL, or any column value starting with http
        for (let i = 1; i <= 10; i++) {
            const val = row[`Slide_${i}_URL`] || row[`Slide_${i}_image`] || row[`Slide_${i}_Link`];
            if (val && typeof val === "string" && val.startsWith("http")) {
                urls.push(val.trim());
            }
        }
        // Fallback check: if there is no explicit Slide URL columns, search all columns for http image urls
        if (urls.length === 0) {
            Object.keys(row).forEach(k => {
                if (k.toLowerCase().includes("url") || k.toLowerCase().includes("link")) {
                    const val = row[k];
                    if (val && typeof val === "string" && val.startsWith("http")) {
                        urls.push(val.trim());
                    }
                }
            });
        }
        return urls;
    }

    // ─── Modal Scheduling Dialog ───────────────────────────────
    const modal = document.getElementById("schedule-modal");
    const closeModalElements = document.querySelectorAll(".close-modal, .close-modal-btn");
    const scheduleType = document.getElementById("schedule-type");
    const timePickerWrapper = document.getElementById("time-picker-wrapper");
    const scheduleForm = document.getElementById("schedule-form");

    function openScheduleModal(post, sourceTab, slideUrls) {
        selectedPost = { post, sourceTab, slideUrls };

        document.getElementById("modal-post-title").innerText = `Schedule: ${post.Topic || post.Post_ID}`;
        document.getElementById("modal-post-subtitle").innerText = `Post ID: ${post.Post_ID} | Source: ${sourceTab}`;
        document.getElementById("post-caption").value = post.Caption || "";

        // Preview images
        const previewContainer = document.getElementById("modal-slides-preview");
        previewContainer.innerHTML = "";
        slideUrls.forEach(url => {
            const img = document.createElement("img");
            img.src = url;
            img.className = "preview-thumb";
            previewContainer.appendChild(img);
        });

        // Reset inputs
        scheduleType.value = "now";
        timePickerWrapper.classList.add("hidden");
        document.getElementById("schedule-datetime").value = "";

        modal.style.display = "block";
    }

    closeModalElements.forEach(el => {
        el.addEventListener("click", () => {
            modal.style.display = "none";
        });
    });

    scheduleType.addEventListener("change", () => {
        if (scheduleType.value === "later") {
            timePickerWrapper.classList.remove("hidden");
        } else {
            timePickerWrapper.classList.add("hidden");
        }
    });

    scheduleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!selectedPost) return;

        let scheduleTime = new Date().toISOString();
        if (scheduleType.value === "later") {
            const pickerVal = document.getElementById("schedule-datetime").value;
            if (!pickerVal) {
                alert("Please select a target date and time.");
                return;
            }
            scheduleTime = new Date(pickerVal).toISOString();
        }

        const payload = {
            post_id: selectedPost.post.Post_ID,
            topic: selectedPost.post.Topic || "",
            source_sheet: selectedPost.sourceTab,
            caption: selectedPost.post.Caption || "",
            slide_urls: selectedPost.slideUrls,
            schedule_time: scheduleTime,
            row_index: selectedPost.post.row_index
        };

        try {
            const res = await fetch("/api/schedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === "success") {
                modal.style.display = "none";
                fetchScheduledJobs();
                fetchPosts(); // Reload cards to verify state changes
            }
        } catch (err) {
            alert("Error scheduling post: " + err.message);
        }
    });

    // ─── Fetch and Render Schedule & History Table ──────────────
    async function fetchScheduledJobs() {
        const tbody = document.getElementById("schedule-tbody");
        try {
            const res = await fetch("/api/schedule/list");
            const jobs = await res.json();

            tbody.innerHTML = "";
            if (jobs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No jobs scheduled yet.</td></tr>`;
                return;
            }

            jobs.forEach(job => {
                const tr = document.createElement("tr");

                let badgeClass = "badge";
                if (job.status === "Pending") badgeClass += " status-generating";
                else if (job.status === "Posting") badgeClass += " status-approved";
                else if (job.status === "Success") badgeClass += " status-posted";
                else if (job.status === "Failed") badgeClass += " status-failed";

                const dateLocal = new Date(job.schedule_time).toLocaleString();

                let actionHtml = "";
                if (job.status === "Pending") {
                    actionHtml = `<button class="btn secondary btn-cancel-job" data-id="${job.id}">Delete</button>`;
                } else if (job.status === "Success") {
                    actionHtml = `<span style="color: var(--success-border); font-size: 0.85rem;">ID: ${job.published_id}</span>`;
                } else if (job.status === "Failed") {
                    actionHtml = `<span style="color: var(--error-border); font-size: 0.85rem;" title="${job.error_message}">⚠️ Failed</span>`;
                }

                tr.innerHTML = `
                    <td><strong>${job.post_id}</strong></td>
                    <td><span class="badge">${job.source_sheet}</span></td>
                    <td>${job.topic || "-"}</td>
                    <td>${dateLocal}</td>
                    <td><span class="${badgeClass}">${job.status}</span></td>
                    <td>${actionHtml}</td>
                `;

                const cancelBtn = tr.querySelector(".btn-cancel-job");
                if (cancelBtn) {
                    cancelBtn.addEventListener("click", () => deleteJob(job.id));
                }

                tbody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error fetching jobs table", err);
        }
    }

    async function deleteJob(id) {
        if (!confirm("Are you sure you want to delete this scheduled post?")) return;
        try {
            const res = await fetch(`/api/schedule/delete/${id}`, { method: "POST" });
            const data = await res.json();
            if (data.status === "success") {
                fetchScheduledJobs();
            }
        } catch (err) {
            console.error("Delete job failed", err);
        }
    }

    // ─── Error Notification Banner ─────────────────────────────
    function showErrorBanner(msg) {
        const banner = document.getElementById("error-banner");
        document.getElementById("error-message").innerText = msg;
        banner.classList.remove("hidden");
    }

    window.closeErrorBanner = function() {
        document.getElementById("error-banner").classList.add("hidden");
    };

    // ─── Campaign Automation & Cron Sequencer ──────────────────
    const campaignSelect = document.getElementById("campaign-select");
    const bulkFrequency = document.getElementById("bulk-frequency");
    const bulkIntervalWrapper = document.getElementById("bulk-interval-wrapper");
    const bulkScheduleForm = document.getElementById("bulk-schedule-form");
    const btnUnscheduleCampaign = document.getElementById("btn-unschedule-campaign");
    const automationPostsTbody = document.getElementById("automation-posts-tbody");
    const bulkStatusLog = document.getElementById("bulk-status-log");

    // Single Post Scheduler Elements
    const singlePostSelect = document.getElementById("single-post-select");
    const singlePostTime = document.getElementById("single-post-time");
    const singlePostInfo = document.getElementById("single-post-info");
    const singleScheduleForm = document.getElementById("single-schedule-form");
    let loadedCampaignPosts = [];

    function populateSinglePostDropdown(posts) {
        if (!singlePostSelect) return;
        const currentSelected = singlePostSelect.value;
        singlePostSelect.innerHTML = '<option value="" disabled selected>Select a post...</option>';
        
        posts.forEach(post => {
            const isPast = post.schedule_time && (new Date(post.schedule_time) <= new Date());
            const isPostingOrPosted = post.db_status === "Posting" || post.db_status === "Success" || post.sheet_status === "Posted";
            if (isPostingOrPosted || isPast) {
                return;
            }
            const opt = document.createElement("option");
            opt.value = post.post_id;
            opt.innerText = `${post.post_id} (${post.sheet_status || 'Pending'})`;
            singlePostSelect.appendChild(opt);
        });

        // Restore selection if it still exists in the list and remains valid
        const isStillValidSelected = currentSelected && posts.some(p => {
            const isPast = p.schedule_time && (new Date(p.schedule_time) <= new Date());
            const isPostingOrPosted = p.db_status === "Posting" || p.db_status === "Success" || p.sheet_status === "Posted";
            return p.post_id === currentSelected && !isPostingOrPosted && !isPast;
        });

        if (isStillValidSelected) {
            singlePostSelect.value = currentSelected;
        } else {
            singlePostTime.value = "";
            singlePostInfo.innerText = "Choose a post to view its schedule status.";
        }
    }

    if (singlePostSelect) {
        singlePostSelect.addEventListener("change", () => {
            const postId = singlePostSelect.value;
            const post = loadedCampaignPosts.find(p => p.post_id === postId);
            if (!post) return;
            
            if (post.schedule_time) {
                const dt = new Date(post.schedule_time);
                const offsetMs = dt.getTimezoneOffset() * 60 * 1000;
                const localISO = new Date(dt.getTime() - offsetMs).toISOString().slice(0, 16);
                singlePostTime.value = localISO;
                singlePostInfo.innerHTML = `<strong>Topic:</strong> ${post.topic}<br><strong>Sheet Status:</strong> ${post.sheet_status}<br><strong>Database Status:</strong> ${post.db_status || 'Pending'}<br><strong>Scheduled Time:</strong> ${new Date(post.schedule_time).toLocaleString()}`;
            } else {
                // Pre-populate with tomorrow at 10:00 AM
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                tomorrow.setHours(10, 0, 0, 0);
                const offsetMs = tomorrow.getTimezoneOffset() * 60 * 1000;
                const localISO = new Date(tomorrow.getTime() - offsetMs).toISOString().slice(0, 16);
                singlePostTime.value = localISO;
                singlePostInfo.innerHTML = `<strong>Topic:</strong> ${post.topic}<br><strong>Sheet Status:</strong> ${post.sheet_status}<br><strong>Status:</strong> Not Scheduled yet.`;
            }
        });
    }

    if (singleScheduleForm) {
        singleScheduleForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const worksheet = campaignSelect.value;
            if (!worksheet) {
                alert("Please select a campaign series first.");
                return;
            }
            const postId = singlePostSelect.value;
            if (!postId) {
                alert("Please select a post first.");
                return;
            }
            const scheduleVal = singlePostTime.value;
            if (!scheduleVal) {
                alert("Please select a date and time.");
                return;
            }
            
            const isoTime = new Date(scheduleVal).toISOString();
            singlePostInfo.innerText = `Scheduling ${postId} for ${new Date(scheduleVal).toLocaleString()}...`;
            
            try {
                const res = await fetch("/api/campaign/update-single-schedule", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        worksheet_name: worksheet,
                        post_id: postId,
                        schedule_time: isoTime
                    })
                });
                const data = await res.json();
                if (res.ok && data.status === "success") {
                    singlePostInfo.innerHTML = `<span style="color: var(--accent-neon-green)">Success: Scheduled ${postId} successfully.</span>`;
                    bulkStatusLog.innerText = `Success: Scheduled post '${postId}' for ${new Date(scheduleVal).toLocaleString()}.`;
                    loadCampaignPostsTable();
                    fetchScheduledJobs();
                    fetchPosts();
                } else {
                    singlePostInfo.innerHTML = `<span style="color: var(--error-border)">Error: ${data.detail || "Scheduling failed."}</span>`;
                }
            } catch (err) {
                singlePostInfo.innerHTML = `<span style="color: var(--error-border)">Network Error: ${err.message}</span>`;
            }
        });
    }

    // Fetch worksheets to populate dropdown
    async function loadCampaignWorksheets() {
        try {
            const res = await fetch("/api/worksheets");
            const data = await res.json();
            
            if (data.worksheets && data.worksheets.length > 0) {
                campaignSelect.innerHTML = `<option value="" disabled selected>Select a campaign...</option>`;
                data.worksheets.forEach(w => {
                    if (w !== "Queue") {
                        const opt = document.createElement("option");
                        opt.value = w;
                        opt.innerText = w === "50DaysCampaign" ? "50-Day D2C Automation" : w;
                        campaignSelect.appendChild(opt);
                    }
                });
            }
        } catch (err) {
            console.error("Error loading worksheets list", err);
        }
    }
    loadCampaignWorksheets();

    // Toggle custom interval days field visibility
    bulkFrequency.addEventListener("change", () => {
        if (bulkFrequency.value === "custom") {
            bulkIntervalWrapper.classList.remove("hidden");
        } else {
            bulkIntervalWrapper.classList.add("hidden");
        }
    });

    // Load campaign posts sequence
    campaignSelect.addEventListener("change", () => {
        loadCampaignPostsTable();
    });

    async function loadCampaignPostsTable() {
        const worksheet = campaignSelect.value;
        if (!worksheet) return;

        automationPostsTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 2rem;">Loading campaign posts...</td></tr>`;

        try {
            const res = await fetch(`/api/campaign/posts?worksheet_name=${encodeURIComponent(worksheet)}`);
            const data = await res.json();
            const posts = data.posts || [];
            loadedCampaignPosts = posts;
            populateSinglePostDropdown(posts);

            automationPostsTbody.innerHTML = "";
            if (posts.length === 0) {
                automationPostsTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No posts found in this campaign.</td></tr>`;
                return;
            }

            posts.forEach(post => {
                const tr = document.createElement("tr");
                tr.style.borderBottom = "1px solid var(--card-border)";

                let statusBadgeClass = "badge";
                const sheetStatus = (post.sheet_status || "Pending").trim();
                if (sheetStatus.toLowerCase() === "approved" || sheetStatus.toLowerCase() === "scheduled") {
                    statusBadgeClass += " status-approved";
                } else if (sheetStatus.toLowerCase() === "posted") {
                    statusBadgeClass += " status-posted";
                } else {
                    statusBadgeClass += " status-generating";
                }

                // Format schedule time for input field
                let timeInputValue = "";
                if (post.schedule_time) {
                    const dt = new Date(post.schedule_time);
                    const offsetMs = dt.getTimezoneOffset() * 60 * 1000;
                    const localISO = new Date(dt.getTime() - offsetMs).toISOString().slice(0, 16);
                    timeInputValue = localISO;
                }

                const isPastPostingTime = post.schedule_time && (new Date(post.schedule_time) <= new Date());
                const isPostingOrPosted = post.db_status === "Posting" || post.db_status === "Success" || post.sheet_status === "Posted";
                const isLocked = isPastPostingTime || isPostingOrPosted;

                tr.innerHTML = `
                    <td style="padding: 0.75rem;"><strong>${post.post_id}</strong></td>
                    <td style="padding: 0.75rem;">${post.topic}</td>
                    <td style="padding: 0.75rem;"><span class="${statusBadgeClass}">${sheetStatus}</span></td>
                    <td style="padding: 0.75rem;">
                        ${!isLocked ? `
                            <input type="datetime-local" class="glass-input post-time-adjust" value="${timeInputValue}" style="padding: 0.4rem; font-size: 0.85rem;" data-post-id="${post.post_id}">
                        ` : `
                            <span style="color: var(--text-secondary); font-size: 0.85rem;">
                                ${post.db_status === "Posting" ? "⚡ Publishing..." : (post.sheet_status === "Posted" ? "Published" : "Posting Time Reached")}
                            </span>
                        `}
                    </td>
                    <td style="padding: 0.75rem;">
                        ${!isLocked && post.schedule_time ? `
                            <button class="btn primary btn-save-single-sched" data-post-id="${post.post_id}" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">Save</button>
                        ` : `-`}
                    </td>
                `;

                // Add event listener for single schedule adjustment save
                const saveBtn = tr.querySelector(".btn-save-single-sched");
                if (saveBtn) {
                    saveBtn.addEventListener("click", async () => {
                        const input = tr.querySelector(".post-time-adjust");
                        const newTime = input.value;
                        if (!newTime) {
                            alert("Please select a date and time first.");
                            return;
                        }
                        const isoTime = new Date(newTime).toISOString();
                        
                        try {
                            const updateRes = await fetch("/api/campaign/update-single-schedule", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    worksheet_name: worksheet,
                                    post_id: post.post_id,
                                    schedule_time: isoTime
                                })
                            });
                            const updateData = await updateRes.json();
                            if (updateData.status === "success") {
                                bulkStatusLog.innerText = `Success: Updated schedule time for post '${post.post_id}' to ${new Date(newTime).toLocaleString()}.`;
                                loadCampaignPostsTable();
                                fetchScheduledJobs();
                            } else {
                                alert("Failed to update schedule: " + updateData.detail);
                            }
                        } catch (err) {
                            alert("Error updating schedule: " + err.message);
                        }
                    });
                }

                automationPostsTbody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error loading campaign posts", err);
            automationPostsTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--error-border); padding: 2rem;">Error communicating with server API.</td></tr>`;
        }
    }

    // Set default date picker to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById("bulk-start-date").value = tomorrow.toISOString().split("T")[0];

    // Submit bulk scheduler form
    bulkScheduleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const worksheet = campaignSelect.value;
        if (!worksheet) {
            alert("Please select a campaign series first.");
            return;
        }

        const startDate = document.getElementById("bulk-start-date").value;
        const postTime = document.getElementById("bulk-post-time").value;
        const frequency = bulkFrequency.value;
        const intervalDays = parseInt(document.getElementById("bulk-interval-days").value) || 1;

        bulkStatusLog.innerText = `Scheduling campaign posts sequentially starting from ${startDate} at ${postTime}...`;

        try {
            const res = await fetch("/api/campaign/bulk-schedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    worksheet_name: worksheet,
                    start_date: startDate,
                    posting_time: postTime,
                    frequency: frequency,
                    interval_days: intervalDays
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                bulkStatusLog.innerText = `Success!\n\n${data.message}`;
                loadCampaignPostsTable();
                fetchScheduledJobs();
                fetchPosts(); // Refresh home grid
            } else {
                bulkStatusLog.innerText = `Error: ${data.detail || "Bulk scheduling failed."}`;
            }
        } catch (err) {
            bulkStatusLog.innerText = `Network Error: ${err.message}`;
        }
    });

    // Unschedule all pending posts for campaign
    btnUnscheduleCampaign.addEventListener("click", async () => {
        const worksheet = campaignSelect.value;
        if (!worksheet) {
            alert("Please select a campaign series first.");
            return;
        }

        if (!confirm(`Are you sure you want to remove ALL pending scheduled posts for the campaign series '${worksheet}'?`)) {
            return;
        }

        bulkStatusLog.innerText = `Unscheduling all pending posts for campaign '${worksheet}'...`;

        try {
            const res = await fetch("/api/campaign/unschedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    worksheet_name: worksheet
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                bulkStatusLog.innerText = `Success!\n\n${data.message}`;
                loadCampaignPostsTable();
                fetchScheduledJobs();
                fetchPosts();
            } else {
                bulkStatusLog.innerText = `Error: ${data.detail || "Unscheduling failed."}`;
            }
        } catch (err) {
            bulkStatusLog.innerText = `Network Error: ${err.message}`;
        }
    });

    // ─── Campaigns Tab Dashboard ───────────────────────────────
    const campaignsListGrid = document.getElementById("campaigns-list-grid");
    const todayPostsTbody = document.getElementById("today-posts-tbody");
    const campaignsDashboardView = document.getElementById("campaigns-dashboard-view");
    const campaignsDetailView = document.getElementById("campaigns-detail-view");
    const campaignDetailTitle = document.getElementById("campaign-detail-title");
    const campaignDetailSubtitle = document.getElementById("campaign-detail-subtitle");
    const campaignDetailPostsGrid = document.getElementById("campaign-detail-posts-grid");
    const btnBackToCampaigns = document.getElementById("btn-back-to-campaigns");

    async function fetchCampaignsOverview() {
        if (!campaignsListGrid) return;
        campaignsListGrid.innerHTML = '<div class="loading-skeleton-card"></div><div class="loading-skeleton-card"></div>';
        
        try {
            const res = await fetch("/api/campaigns/overview");
            const data = await res.json();
            
            renderTodayPosts(data.today_posts || []);
            renderCampaignsList(data.campaigns || []);
        } catch (err) {
            console.error("Error fetching campaigns overview", err);
            if (campaignsListGrid) {
                campaignsListGrid.innerHTML = `<p class="card" style="grid-column: 1/-1;">⚠️ Failed to load campaigns dashboard: ${err.message}</p>`;
            }
        }
    }

    function renderTodayPosts(posts) {
        if (!todayPostsTbody) return;
        todayPostsTbody.innerHTML = "";
        
        if (posts.length === 0) {
            todayPostsTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No posts scheduled for today.</td></tr>`;
            return;
        }
        
        posts.forEach(post => {
            const tr = document.createElement("tr");
            tr.style.borderBottom = "1px solid var(--card-border)";
            
            let statusClass = "badge";
            if (post.status === "Pending") statusClass += " status-generating";
            else if (post.status === "Posting") statusClass += " status-approved";
            else if (post.status === "Success") statusClass += " status-posted";
            else if (post.status === "Failed") statusClass += " status-failed";
            
            const timeLocal = new Date(post.schedule_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const campaignName = post.source_sheet === "50DaysCampaign" ? "50-Day D2C Automation" : post.source_sheet;
            
            tr.innerHTML = `
                <td style="padding: 0.75rem;"><strong>${campaignName}</strong></td>
                <td style="padding: 0.75rem;">${post.post_id}</td>
                <td style="padding: 0.75rem;">${post.topic || "-"}</td>
                <td style="padding: 0.75rem;">${timeLocal}</td>
                <td style="padding: 0.75rem;"><span class="${statusClass}">${post.status}</span></td>
            `;
            
            todayPostsTbody.appendChild(tr);
        });
    }

    function renderCampaignsList(campaigns) {
        if (!campaignsListGrid) return;
        campaignsListGrid.innerHTML = "";
        
        if (campaigns.length === 0) {
            campaignsListGrid.innerHTML = `<p class="card" style="grid-column: 1/-1;">No campaigns found.</p>`;
            return;
        }
        
        campaigns.forEach(camp => {
            const card = document.createElement("div");
            card.className = "card post-card";
            
            const total = camp.total_posts || 0;
            const posted = camp.posted || 0;
            const progressPercent = total > 0 ? Math.round((posted / total) * 100) : 0;
            
            card.innerHTML = `
                <div class="post-card-header" style="margin-bottom: 0.5rem;">
                    <span class="badge status-posted">${camp.posted} Posted</span>
                    <span class="badge status-approved">${camp.scheduled} Scheduled</span>
                </div>
                <h3 style="margin-bottom: 1rem;">${camp.campaign_name}</h3>
                
                <div style="margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                        <span>Completion Progress</span>
                        <span>${progressPercent}% (${posted}/${total})</span>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.05); height: 6px; border-radius: 3px; overflow: hidden;">
                        <div style="background: var(--accent-lime); width: ${progressPercent}%; height: 100%; border-radius: 3px;"></div>
                    </div>
                </div>
                
                <div class="post-card-footer">
                    <span style="font-size: 0.8rem; color: var(--text-secondary);">${camp.pending} Pending</span>
                    <button class="btn primary view-camp-detail-btn" style="padding: 0.5rem 1rem; font-size: 0.8rem;">
                        View Posts
                    </button>
                </div>
            `;
            
            const btn = card.querySelector(".view-camp-detail-btn");
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                showCampaignDetail(camp.worksheet_name, camp.campaign_name, camp);
            });
            
            campaignsListGrid.appendChild(card);
        });
    }

    async function showCampaignDetail(worksheet, name, camp) {
        campaignsDashboardView.classList.add("hidden");
        campaignsDetailView.classList.remove("hidden");
        
        campaignDetailTitle.innerText = `Campaign: ${name}`;
        campaignDetailSubtitle.innerText = `${camp.total_posts} total posts | ${camp.posted} published | ${camp.scheduled} scheduled | ${camp.pending} pending`;
        
        campaignDetailPostsGrid.innerHTML = '<div class="loading-skeleton-card"></div><div class="loading-skeleton-card"></div><div class="loading-skeleton-card"></div>';
        
        try {
            const res = await fetch(`/api/campaign/posts?worksheet_name=${encodeURIComponent(worksheet)}`);
            const data = await res.json();
            const posts = data.posts || [];
            
            campaignDetailPostsGrid.innerHTML = "";
            if (posts.length === 0) {
                campaignDetailPostsGrid.innerHTML = `<p class="card" style="grid-column: 1/-1;">No posts found in this campaign.</p>`;
                return;
            }
            
            posts.forEach(post => {
                const card = document.createElement("div");
                card.className = "card post-card";
                
                let badgeClass = "badge";
                const status = (post.sheet_status || "Pending").trim();
                if (status.toLowerCase() === "approved" || status.toLowerCase() === "scheduled") badgeClass += " status-approved";
                else if (status.toLowerCase() === "posted") badgeClass += " status-posted";
                else badgeClass += " status-generating";
                
                let timeText = "";
                if (post.schedule_time) {
                    timeText = `<div style="font-size: 0.75rem; color: var(--accent-neon-blue); margin-top: 0.5rem;">⏳ Scheduled: ${new Date(post.schedule_time).toLocaleString()}</div>`;
                }
                
                card.innerHTML = `
                    <div class="post-card-header">
                        <span class="${badgeClass}">${status}</span>
                    </div>
                    <h3 style="margin-top: 0.5rem; margin-bottom: 0.5rem;">${post.post_id}</h3>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        ${post.topic}
                    </p>
                    ${timeText}
                    <div class="post-card-footer" style="margin-top: 1rem; display: flex; justify-content: flex-end;">
                        <button class="btn secondary preview-camp-post-btn" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">
                            Preview Post
                        </button>
                    </div>
                `;
                
                card.style.cursor = "pointer";
                const redirectHandler = () => {
                    const url = `/preview?post_id=${encodeURIComponent(post.post_id)}&source=${encodeURIComponent(worksheet)}&row_index=${post.row_index}`;
                    window.location.href = url;
                };
                card.addEventListener("click", redirectHandler);
                card.querySelector(".preview-camp-post-btn").addEventListener("click", (e) => {
                    e.stopPropagation();
                    redirectHandler();
                });
                
                campaignDetailPostsGrid.appendChild(card);
            });
        } catch (err) {
            console.error("Error loading campaign details", err);
            campaignDetailPostsGrid.innerHTML = `<p class="card" style="grid-column: 1/-1; color: var(--error-border)">⚠️ Error loading posts: ${err.message}</p>`;
        }
    }

    if (btnBackToCampaigns) {
        btnBackToCampaigns.addEventListener("click", () => {
            campaignsDetailView.classList.add("hidden");
            campaignsDashboardView.classList.remove("hidden");
            fetchCampaignsOverview();
        });
    }

    const campaignsTabBtn = document.querySelector('[data-target="campaigns-sec"]');
    if (campaignsTabBtn) {
        campaignsTabBtn.addEventListener("click", () => {
            campaignsDetailView.classList.add("hidden");
            campaignsDashboardView.classList.remove("hidden");
            fetchCampaignsOverview();
        });
    }

    // ─── Schedule Calendar View ────────────────────────────────
    const calendarDaysGrid = document.getElementById("calendar-days-grid");
    const calendarMonthYear = document.getElementById("calendar-month-year");
    const btnPrevMonth = document.getElementById("btn-prev-month");
    const btnNextMonth = document.getElementById("btn-next-month");
    const calendarTabBtn = document.querySelector('[data-target="calendar-sec"]');

    let calendarCurrentDate = new Date();
    let calendarJobs = [];

    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    async function loadCalendarJobs() {
        try {
            const res = await fetch("/api/schedule/list");
            calendarJobs = await res.json();
            renderCalendar();
        } catch (err) {
            console.error("Error fetching calendar jobs", err);
        }
    }

    function renderCalendar() {
        if (!calendarDaysGrid || !calendarMonthYear) return;
        calendarDaysGrid.innerHTML = "";

        const year = calendarCurrentDate.getFullYear();
        const month = calendarCurrentDate.getMonth();

        // Update Header Title
        calendarMonthYear.innerText = `${monthNames[month]} ${year}`;

        // Get first day of month and total days
        const firstDayIndex = new Date(year, month, 1).getDay();
        const totalDays = new Date(year, month + 1, 0).getDate();

        // Render Empty Padding Days
        for (let i = 0; i < firstDayIndex; i++) {
            const emptyCell = document.createElement("div");
            emptyCell.className = "calendar-day empty";
            calendarDaysGrid.appendChild(emptyCell);
        }

        const today = new Date();

        // Render Actual Calendar Days
        for (let day = 1; day <= totalDays; day++) {
            const dayCell = document.createElement("div");
            dayCell.className = "calendar-day";

            // Highlight Today
            if (day === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                dayCell.classList.add("today");
            }

            // Day Number label
            const numLabel = document.createElement("div");
            numLabel.className = "calendar-day-number";
            numLabel.innerText = day;
            dayCell.appendChild(numLabel);

            // Filter jobs scheduled for this specific date
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayJobs = calendarJobs.filter(job => {
                if (!job.schedule_time) return false;
                return job.schedule_time.startsWith(dateStr);
            });

            // Populate jobs as tag pills
            dayJobs.forEach(job => {
                const pill = document.createElement("div");
                const statusLower = (job.status || "Pending").toLowerCase();
                pill.className = `calendar-post-pill status-${statusLower}`;
                
                const jobTime = new Date(job.schedule_time);
                const timeLocal = jobTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                pill.innerText = `${timeLocal} | ${job.post_id}`;
                pill.title = `Topic: ${job.topic || 'Untitled'}\nStatus: ${job.status}\nSource: ${job.source_sheet}`;
                
                pill.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const url = `/preview?post_id=${encodeURIComponent(job.post_id)}&source=${encodeURIComponent(job.source_sheet)}&row_index=${job.row_index || ''}`;
                    window.location.href = url;
                });

                dayCell.appendChild(pill);
            });

            calendarDaysGrid.appendChild(dayCell);
        }
    }

    if (btnPrevMonth) {
        btnPrevMonth.addEventListener("click", () => {
            calendarCurrentDate.setMonth(calendarCurrentDate.getMonth() - 1);
            renderCalendar();
        });
    }

    if (btnNextMonth) {
        btnNextMonth.addEventListener("click", () => {
            calendarCurrentDate.setMonth(calendarCurrentDate.getMonth() + 1);
            renderCalendar();
        });
    }

    if (calendarTabBtn) {
        calendarTabBtn.addEventListener("click", () => {
            loadCalendarJobs();
        });
    }
});
