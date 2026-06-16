document.addEventListener("DOMContentLoaded", () => {
    // URL Parameters
    const urlParams = new URLSearchParams(window.location.search);
    const postId = urlParams.get("post_id");
    const sourceSheet = urlParams.get("source");
    const rowIndex = urlParams.get("row_index");

    if (!postId || !sourceSheet) {
        document.body.innerHTML = `
            <div style="padding: 2.5rem; max-width: 600px; margin: 5rem auto; text-align: center;" class="card">
                <h2>⚠️ Invalid Request</h2>
                <p style="color: var(--text-secondary); margin-top: 1rem;">Missing post_id or source parameters.</p>
                <a href="/" class="btn secondary" style="margin-top: 1.5rem; display: inline-flex;">Back to Dashboard</a>
            </div>
        `;
        return;
    }

    // State Variables
    let postData = null;
    let slides = [];
    let activeSlideIndex = 0;

    // Elements
    const prevBtn = document.getElementById("prev-slide-btn");
    const nextBtn = document.getElementById("next-slide-btn");
    const slideIndicator = document.getElementById("slide-indicator");
    const activeFrame = document.getElementById("active-slide-frame");
    const filmstrip = document.getElementById("filmstrip-container");
    const captionTextarea = document.getElementById("caption-content");
    const copyBtn = document.getElementById("copy-caption-btn");
    const copyToast = document.getElementById("copy-toast");

    // Fetch Details on load
    fetchPostDetails();

    // ─── Fetch Details ──────────────────────────────────────────
    async function fetchPostDetails() {
        try {
            const url = `/api/post/details?post_id=${encodeURIComponent(postId)}&source_sheet=${encodeURIComponent(sourceSheet)}${rowIndex ? `&row_index=${rowIndex}` : ''}`;
            const res = await fetch(url);
            
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Failed to load post details.");
            }

            const data = await res.json();
            postData = data;
            
            renderPostInfo(data);
            extractSlides(data);
            renderSlides();
        } catch (err) {
            console.error("Error fetching details:", err);
            activeFrame.innerHTML = `<div class="active-slide-placeholder" style="color: var(--error-border);">⚠️ Error: ${err.message}</div>`;
        }
    }

    // ─── Render Text Info ───────────────────────────────────────
    function renderPostInfo(data) {
        const row = data.data;
        document.getElementById("post-topic").innerText = row.Topic || row.Post_ID || "Unnamed Post";
        document.getElementById("post-subtitle").innerText = `Post ID: ${data.post_id} | Source Worksheet: ${data.source_sheet}`;
        
        // Status Badge
        const status = (row.Status || "Pending").trim();
        const statusBadge = document.getElementById("post-status");
        statusBadge.innerText = status;
        statusBadge.className = "badge";
        if (status.toLowerCase() === "approved") statusBadge.classList.add("status-approved");
        else if (status.toLowerCase() === "generating") statusBadge.classList.add("status-generating");
        else if (status.toLowerCase() === "posted") statusBadge.classList.add("status-posted");

        // Caption & Meta
        captionTextarea.value = row.Caption || "No caption text.";
        document.getElementById("meta-source").innerText = data.source_sheet;
        document.getElementById("meta-row").innerText = data.row_index || "-";
    }

    // ─── Extract Slide URLs ─────────────────────────────────────
    function extractSlides(data) {
        const row = data.data;
        const tempSlides = [];

        // 1. Check Google Sheet columns Slide_1_URL to Slide_10_URL
        for (let i = 1; i <= 10; i++) {
            const val = row[`Slide_${i}_URL`] || row[`Slide_${i}_image`] || row[`Slide_${i}_Link`];
            if (val && typeof val === "string" && val.startsWith("http")) {
                tempSlides.push(val.trim());
            }
        }

        // 2. If no explicit columns, scan all row properties for URLs
        if (tempSlides.length === 0) {
            Object.keys(row).forEach(k => {
                if (k.toLowerCase().includes("url") || k.toLowerCase().includes("link")) {
                    const val = row[k];
                    if (val && typeof val === "string" && val.startsWith("http")) {
                        tempSlides.push(val.trim());
                    }
                }
            });
        }

        // 3. Fallback: If no sheet URLs, check for local slides mounted at /post
        if (tempSlides.length === 0 && data.local_slides && data.local_slides.length > 0) {
            data.local_slides.forEach(url => {
                tempSlides.push(url);
            });
        }

        slides = tempSlides;
    }

    // ─── Render Slides ──────────────────────────────────────────
    function renderSlides() {
        if (slides.length === 0) {
            activeFrame.innerHTML = `
                <div class="active-slide-placeholder">
                    <p style="font-size: 1.5rem; margin-bottom: 0.5rem;">🖼️ No slides found</p>
                    <p style="font-size: 0.9rem;">To see slide previews, add public URLs in the Google Sheet or place PNG images in folder: <code>d:\\InstagramPost\\post\\${postData.post_id}\\</code></p>
                </div>
            `;
            filmstrip.innerHTML = "";
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            slideIndicator.innerText = "Slide 0 of 0";
            return;
        }

        // Render Active Slide
        showActiveSlide();

        // Render Filmstrip
        filmstrip.innerHTML = "";
        slides.forEach((url, idx) => {
            const thumb = document.createElement("img");
            thumb.src = url;
            thumb.className = `filmstrip-thumb ${idx === activeSlideIndex ? 'active' : ''}`;
            thumb.title = `Slide ${idx + 1}`;
            
            thumb.addEventListener("click", () => {
                activeSlideIndex = idx;
                showActiveSlide();
            });
            filmstrip.appendChild(thumb);
        });
    }

    function showActiveSlide() {
        const url = slides[activeSlideIndex];
        
        activeFrame.innerHTML = `
            <img src="${url}" class="active-slide-img" alt="Slide ${activeSlideIndex + 1}">
        `;

        // Update indicators & controls
        slideIndicator.innerText = `Slide ${activeSlideIndex + 1} of ${slides.length}`;
        prevBtn.disabled = activeSlideIndex === 0;
        nextBtn.disabled = activeSlideIndex === slides.length - 1;

        // Highlight thumb
        const thumbs = filmstrip.querySelectorAll(".filmstrip-thumb");
        thumbs.forEach((t, idx) => {
            if (idx === activeSlideIndex) {
                t.classList.add("active");
                t.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
            } else {
                t.classList.remove("active");
            }
        });
    }

    // ─── Slide Navigation ──────────────────────────────────────
    prevBtn.addEventListener("click", () => {
        if (activeSlideIndex > 0) {
            activeSlideIndex--;
            showActiveSlide();
        }
    });

    nextBtn.addEventListener("click", () => {
        if (activeSlideIndex < slides.length - 1) {
            activeSlideIndex++;
            showActiveSlide();
        }
    });

    // Support keyboard arrow keys navigation
    document.addEventListener("keydown", (e) => {
        if (slides.length === 0) return;
        if (e.key === "ArrowLeft" && activeSlideIndex > 0) {
            activeSlideIndex--;
            showActiveSlide();
        } else if (e.key === "ArrowRight" && activeSlideIndex < slides.length - 1) {
            activeSlideIndex++;
            showActiveSlide();
        }
    });

    // ─── Copy Caption ──────────────────────────────────────────
    copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(captionTextarea.value).then(() => {
            copyToast.classList.add("show");
            setTimeout(() => {
                copyToast.classList.remove("show");
            }, 2000);
        }).catch(err => {
            alert("Failed to copy caption: " + err);
        });
    });

    // ─── Quick Schedule Action ─────────────────────────────────
    const scheduleForm = document.getElementById("schedule-form");
    const scheduleType = document.getElementById("schedule-type");
    const timePickerWrapper = document.getElementById("time-picker-wrapper");

    scheduleType.addEventListener("change", () => {
        if (scheduleType.value === "later") {
            timePickerWrapper.classList.remove("hidden");
        } else {
            timePickerWrapper.classList.add("hidden");
        }
    });

    scheduleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!postData || slides.length === 0) {
            alert("Cannot schedule: no slide images found.");
            return;
        }

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
            post_id: postData.post_id,
            topic: postData.data.Topic || "",
            source_sheet: postData.source_sheet,
            caption: postData.data.Caption || "",
            slide_urls: slides,
            schedule_time: scheduleTime,
            row_index: postData.row_index
        };

        try {
            const res = await fetch("/api/schedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === "success") {
                alert(`Successfully scheduled post: ${postData.post_id}`);
                window.location.href = "/";
            } else {
                alert("Failed to schedule post: " + data.message);
            }
        } catch (err) {
            alert("Error scheduling post: " + err.message);
        }
    });
});
