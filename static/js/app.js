document.addEventListener('DOMContentLoaded', () => {
    // Determine current page based on location path or document elements
    if (document.getElementById('login-form') || document.getElementById('register-form')) {
        initAuthPage();
    } else if (document.getElementById('dashboard-view')) {
        initDashboardPage();
    }
});

// BASE API ENDPOINTS
const API_BASE = '/api';

/**
 * Handle authentication pages logic (Login & Register)
 */
function initAuthPage() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    
    // Login Submission
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            setLoading(submitBtn, true, 'Signing In...');
            
            const payload = {
                username: document.getElementById('username').value.trim(),
                password: document.getElementById('password').value
            };
            
            try {
                const res = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    showToast('Login successful!', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    showToast(data.error || 'Invalid credentials', 'danger');
                }
            } catch (err) {
                showToast('Network error. Please check your connection.', 'danger');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }
    
    // Registration Submission
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            if (password !== confirmPassword) {
                showToast('Passwords do not match.', 'danger');
                return;
            }
            
            setLoading(submitBtn, true, 'Creating Account...');
            
            const payload = { username, email, password };
            
            try {
                const res = await fetch(`${API_BASE}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    showToast('Registration successful! Redirecting to login...', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1500);
                } else {
                    showToast(data.error || 'Registration failed.', 'danger');
                }
            } catch (err) {
                showToast('Network error. Please try again.', 'danger');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }
}

/**
 * Handle Dashboard view toggles, predictions, history logs, and session management
 */
function initDashboardPage() {
    let currentUser = null;
    let allSymptoms = [];
    let cachedHistory = [];
    let myChartInstance = null;
    
    // UI Elements
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const navLinks = document.querySelectorAll('.sidebar .nav-link[data-section]');
    const sections = document.querySelectorAll('.dashboard-section');
    const logoutBtn = document.getElementById('logout-btn');
    
    // User Profile Hooks
    const profileName = document.getElementById('profile-name');
    const profileEmail = document.getElementById('profile-email');
    const welcomeUser = document.getElementById('welcome-user');
    
    // Predict Module Hooks
    const symptomSearch = document.getElementById('symptom-search');
    const symptomsGrid = document.getElementById('symptoms-grid');
    const predictForm = document.getElementById('predict-form');
    const selectedCount = document.getElementById('selected-count');
    const clearSelectedBtn = document.getElementById('clear-selected-btn');
    
    // Results Ring Hook
    const confidenceBar = document.querySelector('.confidence-bar');
    const confidenceValue = document.getElementById('confidence-val');
    const predictedDisease = document.getElementById('predicted-disease');
    const recommendationCard = document.getElementById('recommendation-card');
    
    // Checks authentication status first
    checkAuthStatus();
    
    // Mobile Sidebar toggle handler
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }
    
    // Close sidebar on mobile clicking item
    document.addEventListener('click', (e) => {
        if (window.innerWidth < 992 && sidebar.classList.contains('show')) {
            if (!sidebar.contains(e.target) && e.target !== sidebarToggle && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        }
    });

    // Navigation state handles
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetSection = link.getAttribute('data-section');
            
            // Toggle sidebar highlights
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Switch visible panel
            sections.forEach(sec => {
                if (sec.id === `${targetSection}-section`) {
                    sec.classList.remove('d-none');
                } else {
                    sec.classList.add('d-none');
                }
            });
            
            // Close mobile overlay sidebar after selection
            if (window.innerWidth < 992) {
                sidebar.classList.remove('show');
            }
            
            // Action trigger when entering specific view tabs
            if (targetSection === 'history') {
                loadHistoryTable();
            } else if (targetSection === 'profile') {
                loadProfileDetails();
            }
        });
    });
    
    // Clear Selected Button Handler
    if (clearSelectedBtn) {
        clearSelectedBtn.addEventListener('click', () => {
            const checkedInputs = symptomsGrid.querySelectorAll('input[type="checkbox"]:checked');
            checkedInputs.forEach(input => {
                input.checked = false;
                input.closest('.symptom-item').classList.remove('selected');
            });
            updateSelectedCount();
        });
    }
    
    // Logout Action handler
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const res = await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
                if (res.ok) {
                    showToast('Logged out successfully.', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1000);
                }
            } catch (err) {
                showToast('Logout request failed.', 'danger');
            }
        });
    }
    // History Table Search and Date Filters Event Listeners
    const historySearch = document.getElementById('history-search');
    const historyDateFrom = document.getElementById('history-date-from');
    const historyDateTo = document.getElementById('history-date-to');
    const historyFilterReset = document.getElementById('history-filter-reset');

    if (historySearch) {
        historySearch.addEventListener('input', applyHistoryFilters);
    }
    if (historyDateFrom) {
        historyDateFrom.addEventListener('change', applyHistoryFilters);
    }
    if (historyDateTo) {
        historyDateTo.addEventListener('change', applyHistoryFilters);
    }
    if (historyFilterReset) {
        historyFilterReset.addEventListener('click', () => {
            historySearch.value = '';
            historyDateFrom.value = '';
            historyDateTo.value = '';
            applyHistoryFilters();
        });
    }

    /**
     * Check if user session cookie is valid
     */
    async function checkAuthStatus() {
        try {
            const res = await fetch(`${API_BASE}/auth/me`);
            if (res.ok) {
                const data = await res.json();
                currentUser = data.user;
                
                // Populate welcoming metadata
                if (welcomeUser) welcomeUser.textContent = currentUser.username;
                
                // Initialize modules
                loadSymptomsList();
                loadDashboardStats();
            } else {
                window.location.href = '/login';
            }
        } catch (err) {
            window.location.href = '/login';
        }
    }
    
    /**
     * Get statistics summary for dashboard counters
     */
    async function loadDashboardStats() {
        try {
            const res = await fetch(`${API_BASE}/predictions/history`);
            if (res.ok) {
                const data = await res.json();
                cachedHistory = data.history;
                
                const totalRuns = cachedHistory.length;
                const totalRunsEl = document.getElementById('stat-total-runs');
                if (totalRunsEl) totalRunsEl.textContent = totalRuns;
                
                const latestDiseaseEl = document.getElementById('stat-latest-disease');
                const avgConfidenceEl = document.getElementById('stat-avg-confidence');
                
                if (totalRuns > 0) {
                    const latest = cachedHistory[0];
                    if (latestDiseaseEl) latestDiseaseEl.textContent = latest.predicted_disease;
                    
                    // Simple confidence average
                    const sumConf = cachedHistory.reduce((sum, item) => sum + item.confidence, 0);
                    const avgConf = (sumConf / totalRuns) * 100;
                    if (avgConfidenceEl) avgConfidenceEl.textContent = `${avgConf.toFixed(0)}%`;
                } else {
                    if (latestDiseaseEl) latestDiseaseEl.textContent = 'None';
                    if (avgConfidenceEl) avgConfidenceEl.textContent = '0%';
                }
                
                // Render distribution analytics chart
                renderAnalyticsChart(cachedHistory);
            }
        } catch (err) {
            console.error("Dashboard statistics load failed:", err);
        }
    }

    /**
     * Pull symptom mapping metadata list from models server
     */
    async function loadSymptomsList() {
        try {
            const res = await fetch(`${API_BASE}/symptoms`);
            if (res.ok) {
                const data = await res.json();
                allSymptoms = data.symptoms;
                renderSymptomCheckboxes();
            } else {
                showToast('Failed to load symptoms list features.', 'warning');
            }
        } catch (err) {
            showToast('Failed to connect to backend model features API.', 'danger');
        }
    }

    /**
     * Render checkboxes for symptoms inside the scrollable grid
     */
    function renderSymptomCheckboxes() {
        symptomsGrid.innerHTML = '';
        
        // Sort symptoms alphabetically for easy scanning
        const sorted = [...allSymptoms].sort();
        
        sorted.forEach(symptom => {
            const labelText = symptom.replace(/_/g, ' ');
            
            const div = document.createElement('div');
            div.className = 'symptom-item';
            div.innerHTML = `
                <input type="checkbox" id="sym-${symptom}" value="${symptom}">
                <label for="sym-${symptom}" class="w-100 d-block cursor-pointer">
                    <i class="bi bi-circle me-2 icon-check-state text-muted"></i>
                    ${capitalizeWords(labelText)}
                </label>
            `;
            
            // Custom selection event handling
            const checkbox = div.querySelector('input[type="checkbox"]');
            div.addEventListener('click', (e) => {
                // Prevent duplicate click handling if target was the label itself
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                }
                
                const icon = div.querySelector('.icon-check-state');
                if (checkbox.checked) {
                    div.classList.add('selected');
                    icon.className = 'bi bi-check-circle-fill me-2 icon-check-state text-teal';
                } else {
                    div.classList.remove('selected');
                    icon.className = 'bi bi-circle me-2 icon-check-state text-muted';
                }
                
                updateSelectedCount();
            });
            
            symptomsGrid.appendChild(div);
        });
        
        // Setup fuzzy search filtering
        symptomSearch.addEventListener('keyup', () => {
            const query = symptomSearch.value.toLowerCase().trim();
            const items = symptomsGrid.querySelectorAll('.symptom-item');
            
            items.forEach(item => {
                const value = item.querySelector('input').value.replace(/_/g, ' ').toLowerCase();
                if (value.includes(query)) {
                    item.classList.remove('d-none');
                } else {
                    item.classList.add('d-none');
                }
            });
        });
    }
    
    function updateSelectedCount() {
        const count = symptomsGrid.querySelectorAll('input[type="checkbox"]:checked').length;
        selectedCount.textContent = count;
    }

    // Prediction trigger event
    if (predictForm) {
        predictForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const checkedInputs = symptomsGrid.querySelectorAll('input[type="checkbox"]:checked');
            if (checkedInputs.length === 0) {
                showToast('Please select at least one symptom before analyzing.', 'warning');
                return;
            }
            
            const submitBtn = predictForm.querySelector('button[type="submit"]');
            setLoading(submitBtn, true, 'Running Diagnosis...');
            
            const selected = Array.from(checkedInputs).map(input => input.value);
            
            try {
                const res = await fetch(`${API_BASE}/predict`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symptoms: selected })
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    showToast('Prediction successfully generated!', 'success');
                    displayPredictionResult(data);
                    
                    // Force stats reload in background
                    loadDashboardStats();
                } else {
                    showToast(data.error || 'Prediction process failed.', 'danger');
                }
            } catch (err) {
                showToast('Network error during analysis.', 'danger');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }

    /**
     * Render circular confidence ring and predictions results card
     */
    function displayPredictionResult(data) {
        const resultWrapper = document.getElementById('prediction-result-wrapper');
        resultWrapper.classList.remove('d-none');
        
        // Scroll into view
        resultWrapper.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // Populate text metrics
        predictedDisease.textContent = data.disease;
        
        // Calculate circle SVG offset percentage
        const percentage = Math.round(data.confidence * 100);
        confidenceValue.textContent = `${percentage}%`;
        
        const circleLength = 376.99; // 2 * PI * r
        const dashOffset = circleLength - (data.confidence * circleLength);
        confidenceBar.style.strokeDashoffset = dashOffset;
        
        // Populate dynamic clinical details from database
        const details = data.disease_details;
        if (details) {
            document.getElementById('disease-description').textContent = details.description;
            document.getElementById('disease-doctor').innerHTML = `<i class="bi bi-person-fill-check me-1"></i>${details.recommended_doctor}`;
            
            // Render causes list
            const causesList = document.getElementById('disease-causes');
            causesList.innerHTML = details.causes.map(c => `<li>${c}</li>`).join('');
            
            // Render precautions list
            const precautionsList = document.getElementById('disease-precautions');
            precautionsList.innerHTML = details.precautions.map(p => `<li>${p}</li>`).join('');
        }
        
        // Configure PDF download button link
        const downloadPdfBtn = document.getElementById('download-pdf-btn');
        if (downloadPdfBtn) {
            if (data.prediction_id) {
                downloadPdfBtn.href = `${API_BASE}/predictions/${data.prediction_id}/pdf`;
                downloadPdfBtn.classList.remove('d-none');
            } else {
                downloadPdfBtn.classList.add('d-none');
            }
        }
    }

    /**
     * Fetch user predictions logs history and populate data table
     */
    async function loadHistoryTable() {
        const tbody = document.getElementById('history-tbody');
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4"><div class="spinner-border text-teal spinner-border-sm" role="status"></div> Loading...</td></tr>`;
        
        try {
            const res = await fetch(`${API_BASE}/predictions/history`);
            if (res.ok) {
                const data = await res.json();
                cachedHistory = data.history;
                applyHistoryFilters();
            } else {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">Failed to load prediction history.</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">Network error loading history.</td></tr>`;
        }
    }

    /**
     * Filters the cached predictions history by query inputs and date boundaries
     */
    function applyHistoryFilters() {
        const tbody = document.getElementById('history-tbody');
        if (!tbody) return;

        const searchEl = document.getElementById('history-search');
        const dateFromEl = document.getElementById('history-date-from');
        const dateToEl = document.getElementById('history-date-to');

        const query = (searchEl ? searchEl.value : '').toLowerCase().trim();
        const dateFrom = dateFromEl ? dateFromEl.value : '';
        const dateTo = dateToEl ? dateToEl.value : '';

        // Filter the cached history array
        const filtered = cachedHistory.filter(record => {
            // 1. Text filter check (matches disease name or symptoms list)
            const matchesDisease = record.predicted_disease.toLowerCase().includes(query);
            const matchesSymptoms = record.symptoms.some(s => s.replace(/_/g, ' ').toLowerCase().includes(query));
            const matchesText = !query || matchesDisease || matchesSymptoms;

            // Extract date string YYYY-MM-DD from record timestamp (SQLite returns ISO strings, e.g. "2026-06-22 13:42:25")
            const recordDateStr = record.created_at.slice(0, 10);

            // 2. Date From filter check
            const matchesDateFrom = !dateFrom || recordDateStr >= dateFrom;

            // 3. Date To filter check
            const matchesDateTo = !dateTo || recordDateStr <= dateTo;

            return matchesText && matchesDateFrom && matchesDateTo;
        });

        // Render filtered history rows
        tbody.innerHTML = '';
        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-muted">No prediction entries match the chosen filters.</td></tr>`;
            return;
        }

        filtered.forEach((record, index) => {
            const date = new Date(record.created_at + 'Z'); // parse as UTC
            const localDate = date.toLocaleString();
            
            const symptomBadges = record.symptoms.map(s => `
                <span class="badge-symptom">${capitalizeWords(s.replace(/_/g, ' '))}</span>
            `).join('');
            
            // Calculate sequential ID index
            const origIndex = cachedHistory.findIndex(item => item.id === record.id);
            const displayId = cachedHistory.length - origIndex;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="text-muted fw-bold small">#${displayId}</td>
                <td>${localDate}</td>
                <td>
                    <div class="d-flex flex-wrap gap-1" style="max-width: 450px;">
                        ${symptomBadges}
                    </div>
                </td>
                <td>
                    <span class="badge-disease">${record.predicted_disease}</span>
                    <small class="text-muted d-block mt-1">Confidence: ${(record.confidence * 100).toFixed(0)}%</small>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    /**
     * Generates a distribution bar chart of predicted diseases using Chart.js
     */
    function renderAnalyticsChart(history) {
        const ctx = document.getElementById('analytics-chart');
        if (!ctx) return;

        // Group history records by disease
        const counts = {};
        history.forEach(item => {
            const disease = item.predicted_disease;
            counts[disease] = (counts[disease] || 0) + 1;
        });

        const labels = Object.keys(counts);
        const data = Object.values(counts);

        // Destroy existing chart instance to prevent canvas recycling bugs
        if (myChartInstance) {
            myChartInstance.destroy();
        }

        if (labels.length === 0) {
            // Draw placeholder if no history exists
            const context = ctx.getContext('2d');
            context.clearRect(0, 0, ctx.width, ctx.height);
            context.font = '16px Outfit';
            context.fillStyle = '#94a3b8';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText('No diagnostic records found yet to generate analytics.', ctx.width / 2 || 150, ctx.height / 2 || 100);
            return;
        }

        myChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Diagnoses Count',
                    data: data,
                    backgroundColor: 'rgba(15, 118, 110, 0.8)', // Primary Teal
                    borderColor: 'rgb(15, 118, 110)',
                    borderWidth: 1.5,
                    borderRadius: 6,
                    maxBarThickness: 45
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleFont: { family: 'Outfit', size: 13 },
                        bodyFont: { family: 'Outfit', size: 12 },
                        cornerRadius: 6
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0,
                            font: { family: 'Outfit', size: 11 }
                        },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        ticks: {
                            font: { family: 'Outfit', size: 11 }
                        },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Render user profile statistics details
     */
    async function loadProfileDetails() {
        if (!currentUser) return;
        
        if (profileName) profileName.textContent = currentUser.username;
        if (profileEmail) profileEmail.textContent = currentUser.email;
        
        const dateJoined = new Date(currentUser.created_at + 'Z');
        const dateJoinedEl = document.getElementById('profile-date-joined');
        if (dateJoinedEl) dateJoinedEl.textContent = dateJoined.toLocaleDateString();
    }
}

/**
 * Loading state spinner helpers
 */
function setLoading(button, isLoading, text = 'Loading...') {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalHtml = button.innerHTML;
        button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ${text}`;
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalHtml || button.innerHTML;
    }
}

/**
 * Text utility helper: uppercase first letter of words
 */
function capitalizeWords(str) {
    return str.replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Universal alert popups
 */
function showToast(message, type = 'success') {
    // Check if toast wrapper already exists, or append one
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show shadow-lg mb-2`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-medium">
                <i class="bi ${type === 'success' ? 'bi-check-circle-fill' : type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto dismiss after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 3000);
    
    // Close button dismiss trigger
    toast.querySelector('.btn-close').addEventListener('click', () => {
        toast.remove();
    });
}
