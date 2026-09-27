document.addEventListener('DOMContentLoaded', () => {
    const videoElement = document.getElementById('live-video');
    const riskLevel = document.getElementById('risk-level');
    const cause = document.getElementById('cause');
    const prob = document.getElementById('prob');
    const objectsList = document.getElementById('objects-list');
    const alerts = document.getElementById('alerts');

    // New elements
    const speedCurrent = document.getElementById('speed-current');
    const weatherType = document.getElementById('weather-type');
    const visibility = document.getElementById('visibility');
    const collisionRisk = document.getElementById('collision-risk');
    const statCritical = document.getElementById('stat-critical');
    const statWarning = document.getElementById('stat-warning');
    const statTotal = document.getElementById('stat-total');
    const reportBtn = document.getElementById('report-btn');

    let alertHistory = [];
    let lastAlertTime = 0;

    // ============== VIDEO STREAM MANAGEMENT ==============
    function initializeVideoStream() {
        if (videoElement) {
            videoElement.src = '/video_feed?' + new Date().getTime();
            videoElement.onerror = () => {
                console.warn('[VIDEO] Stream error, retrying...');
                setTimeout(initializeVideoStream, 2000);
            };
            videoElement.onload = () => {
                console.log('[VIDEO] ✓ Stream connected');
            };
            console.log('[VIDEO] Stream initialization');
        }
    }
    initializeVideoStream();

    // Periodically refresh video stream to prevent stalling
    setInterval(() => {
        if (videoElement && !videoElement.src.includes('timestamp')) {
            videoElement.src = '/video_feed?' + new Date().getTime();
        }
    }, 30000); // Refresh every 30 seconds

    // ============== RISK GAUGE CHART ==============
    const ctx = document.getElementById('risk-gauge').getContext('2d');
    const gauge = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Risk', 'Safe'],
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#ff4444', '#00ff88'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '70%',
            rotation: -90,
            circumference: 180,
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });

    // Report button handler with better UX
    if (reportBtn) {
        reportBtn.addEventListener('click', () => {
            const originalText = reportBtn.textContent;
            reportBtn.textContent = '⏳ Generating...';
            reportBtn.disabled = true;

            fetch('/report')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        console.log('[REPORT] ✓ Generated:', data.report);
                        alert('✓ Report generated successfully!\nLocation: ' + data.report);
                    } else {
                        alert('⚠ Report status: ' + (data.error || 'Unknown'));
                    }
                })
                .catch(err => {
                    console.error('[REPORT] ❌ Error:', err);
                    alert('❌ Error generating report: ' + err.message);
                })
                .finally(() => {
                    reportBtn.textContent = originalText;
                    reportBtn.disabled = false;
                });
        });
    }

    // Check system health
    function checkHealth() {
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'INITIALIZING') {
                    console.log('System initializing... frames:', data.frames);
                    objectsList.textContent = `System initializing... (${data.frames} frames)`;
                } else if (data.status === 'READY') {
                    console.log('System ready!');
                    if (objectsList.textContent.includes('initializing')) {
                        objectsList.textContent = 'Ready - detecting objects...';
                    }
                } else if (data.error) {
                    console.error('System error:', data.error);
                    riskLevel.textContent = 'RISK: ERROR';
                    riskLevel.className = 'risk high';
                    objectsList.textContent = '⚠ Error: ' + data.error;
                }
            })
            .catch(err => {
                console.log('Health check error:', err);
            });
    }

    // Update statistics with smooth animation
    function updateStatistics() {
        fetch('/statistics')
            .then(response => response.json())
            .then(data => {
                // Animate stat updates
                if (statCritical && data.critical !== undefined) {
                    animateNumber(statCritical, parseInt(data.critical) || 0);
                }
                if (statWarning && data.warning !== undefined) {
                    animateNumber(statWarning, parseInt(data.warning) || 0);
                }
                if (statTotal && data.total !== undefined) {
                    animateNumber(statTotal, parseInt(data.total) || 0);
                }
                console.log('[STATS] Updated:', data);
            })
            .catch(err => console.log('[STATS] Error:', err));
    }

    // Helper function to animate number changes
    function animateNumber(element, targetValue) {
        const currentValue = parseInt(element.textContent) || 0;
        if (currentValue === targetValue) return;

        const step = (targetValue - currentValue) / 10;
        let current = currentValue;
        const interval = setInterval(() => {
            current += step;
            if ((step > 0 && current >= targetValue) || (step < 0 && current <= targetValue)) {
                element.textContent = targetValue;
                clearInterval(interval);
            } else {
                element.textContent = Math.round(current);
            }
        }, 50);
    }

    // Update recent alerts with smooth animation
    function updateAlerts() {
        fetch('/alerts')
            .then(response => response.json())
            .then(data => {
                if (data.recent && data.recent.length > 0) {
                    const alertItems = data.recent.slice(0, 5)
                        .map(alert => {
                            const level = alert.level || 'INFO';
                            const levelClass = level.toLowerCase();
                            return `<li class="alert-${levelClass}">[${alert.type || 'SYSTEM'}] <strong>${level}:</strong> ${alert.cause || alert.message}</li>`;
                        })
                        .join('');

                    // Fade in new alerts
                    alerts.style.opacity = '0.7';
                    alerts.innerHTML = alertItems;
                    alerts.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => {
                        alerts.style.opacity = '1';
                    }, 50);

                    console.log('[ALERTS] Updated:', data.recent.length, 'alerts');
                } else if (alerts.innerHTML === '') {
                    alerts.innerHTML = '<li style="color: #a0a0c0; font-style: italic;">No alerts yet - system running normally</li>';
                }
            })
            .catch(err => console.log('[ALERTS] Error:', err));
    }

    // Update dashboard with data from backend
    function updateDashboard() {
        fetch('/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Update risk level
                if (data.risk_level) {
                    riskLevel.textContent = `RISK: ${data.risk_level}`;
                    const riskClass = data.risk_level.toLowerCase().replace('...', '');
                    riskLevel.className = `risk ${riskClass}`;
                }

                // Update cause
                if (data.cause) {
                    cause.textContent = `CAUSE: ${data.cause}`;
                }

                // Update probability and gauge
                if (data.prob !== undefined) {
                    const probValue = parseFloat(data.prob) || 0;
                    prob.textContent = `PROBABILITY: ${probValue.toFixed(2)}`;

                    // Update gauge
                    const riskValue = probValue * 100;
                    gauge.data.datasets[0].data = [riskValue, 100 - riskValue];

                    // Color based on risk value
                    let gaugeColor = '#00ff88'; // Green - Low
                    if (riskValue > 70) {
                        gaugeColor = '#ff4444'; // Red - High
                    } else if (riskValue > 40) {
                        gaugeColor = '#ffff00'; // Yellow - Medium
                    }

                    gauge.data.datasets[0].backgroundColor = [gaugeColor, '#333'];
                    gauge.update('none');
                }

                // Update objects
                if (data.objects) {
                    objectsList.textContent = `${data.objects}`;
                }

                // Update speed
                if (data.speed) {
                    speedCurrent.textContent = data.speed;
                    // Color code by speed
                    if (parseFloat(data.speed) > 80) {
                        speedCurrent.style.color = '#ff4444';
                    } else if (parseFloat(data.speed) > 60) {
                        speedCurrent.style.color = '#ffff00';
                    } else {
                        speedCurrent.style.color = '#00ff88';
                    }
                }

                // Update weather
                if (data.weather) {
                    weatherType.textContent = data.weather;
                }

                if (data.visibility) {
                    visibility.textContent = data.visibility;
                }

                // Update collision risk
                if (data.collision_risk) {
                    collisionRisk.textContent = data.collision_risk;
                    // Color code
                    if (data.collision_risk === 'CRITICAL') {
                        collisionRisk.style.color = '#ff4444';
                    } else if (data.collision_risk === 'WARNING') {
                        collisionRisk.style.color = '#ffff00';
                    } else {
                        collisionRisk.style.color = '#00ff88';
                    }
                }

                // Add new alerts
                if (data.new_alert) {
                    const now = Date.now();
                    if (now - lastAlertTime > 1000) {
                        alertHistory.unshift(`[${new Date().toLocaleTimeString()}] ${data.new_alert}`);
                        if (alertHistory.length > 5) alertHistory.pop();
                        lastAlertTime = now;

                        alerts.innerHTML = alertHistory
                            .map(alert => `<li>${alert}</li>`)
                            .join('');
                    }
                }
            })
            .catch(error => {
                console.log('Data error:', error);
            });
    }

    // Start updates
    checkHealth();
    setInterval(checkHealth, 5000);
    setInterval(updateDashboard, 500);  // More frequent updates for smoothness
    setInterval(updateStatistics, 2000);  // Update stats every 2s
    setInterval(updateAlerts, 2000);  // Update alerts every 2s
    updateDashboard();
    updateStatistics();
    updateAlerts();
});
