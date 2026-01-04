/**
 * NERD SPACE V5.0 - AI FIRST EDITION
 * Frontend JavaScript
 */

// ═══════════════════════════════════════════════════════════════════════
// REQUEST QUEUE SYSTEM (Anti-Travamento)
// ═══════════════════════════════════════════════════════════════════════

class RequestQueue {
    constructor(maxConcurrent = 3) {
        this.queue = [];
        this.running = 0;
        this.maxConcurrent = maxConcurrent;
        this.cache = new Map();
    }

    async add(key, requestFn, ttl = 30000) {
        // Check cache first
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < ttl) {
            return cached.data;
        }

        // Wait if at max concurrent
        if (this.running >= this.maxConcurrent) {
            await new Promise(resolve => this.queue.push(resolve));
        }

        this.running++;
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 5000);

            const result = await requestFn(controller.signal);
            clearTimeout(timeout);

            // Cache result
            this.cache.set(key, { data: result, timestamp: Date.now() });
            return result;
        } finally {
            this.running--;
            if (this.queue.length > 0) {
                this.queue.shift()();
            }
        }
    }

    clearCache(key = null) {
        if (key) {
            this.cache.delete(key);
        } else {
            this.cache.clear();
        }
    }
}

const requestQueue = new RequestQueue(3);

// ═══════════════════════════════════════════════════════════════════════
// DEBOUNCE UTILITY
// ═══════════════════════════════════════════════════════════════════════

function debounce(func, wait = 300) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ═══════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════

async function fetchAPI(endpoint, options = {}) {
    const key = `${endpoint}-${JSON.stringify(options)}`;
    const ttl = options.ttl || 30000;

    return requestQueue.add(key, async (signal) => {
        const response = await fetch(`/api${endpoint}`, {
            ...options,
            signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        return response.json();
    }, ttl);
}

// ═══════════════════════════════════════════════════════════════════════
// NERD SPACE DATA LOADERS
// ═══════════════════════════════════════════════════════════════════════

async function loadNerdSpace() {
    try {
        showSkeleton('nerdspace-content');
        const data = await fetchAPI('/nerdspace', { ttl: 60000 });
        renderNerdSpace(data);
    } catch (error) {
        console.error('NerdSpace load error:', error);
        showError('nerdspace-content', 'Erro ao carregar NERD SPACE');
    }
}

async function loadClaudeUsage() {
    try {
        showSkeleton('claude-usage');
        const data = await fetchAPI('/claude-usage', { ttl: 30000 });
        renderClaudeUsage(data);
    } catch (error) {
        console.error('Claude usage error:', error);
    }
}

async function loadSpeedTest() {
    try {
        showSkeleton('speedtest-results');
        const data = await fetchAPI('/speedtest/last', { ttl: 60000 });
        renderSpeedTest(data);
    } catch (error) {
        console.error('Speed test error:', error);
    }
}

async function runSpeedTest() {
    const btn = document.getElementById('speedtest-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="animate-spin">⟳</span> Testando...';
    }

    try {
        const data = await fetchAPI('/speedtest', {
            method: 'POST',
            ttl: 0 // No cache for new tests
        });
        renderSpeedTest(data);
        showToast('Speed test concluído!', 'success');
    } catch (error) {
        showToast('Erro no speed test', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '▶ Testar Velocidade';
        }
    }
}

async function loadMonitors() {
    try {
        const data = await fetchAPI('/monitors', { ttl: 300000 }); // 5 min cache
        renderMonitors(data);
    } catch (error) {
        console.error('Monitors error:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════
// RENDER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════

function renderNerdSpace(data) {
    const container = document.getElementById('nerdspace-content');
    if (!container) return;

    const { greeting, weather, power } = data;

    container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Greeting -->
            <div class="card">
                <div class="flex items-center gap-3">
                    <span class="text-3xl">${greeting.emoji}</span>
                    <div>
                        <div class="text-lg font-semibold">${greeting.greeting}</div>
                        <div class="text-sm text-muted">${greeting.day_name}, ${greeting.date_sp} • ${greeting.time_sp}</div>
                    </div>
                </div>
            </div>

            <!-- Weather -->
            <div class="card">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-3xl font-bold">${weather.temperature}°C</div>
                        <div class="text-sm text-muted">${weather.description}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm">💧 ${weather.humidity}%</div>
                        <div class="text-sm">💨 ${weather.wind_speed} km/h</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderClaudeUsage(data) {
    const container = document.getElementById('claude-usage');
    if (!container) return;

    const { plan, usage, costs, status, tips } = data;
    const pct5h = usage.window_5h.percent;
    const statusClass = status.level;

    container.innerHTML = `
        <div class="claude-module">
            <div class="claude-header">
                <div class="claude-logo">🤖</div>
                <div>
                    <div class="claude-title">${plan.name}</div>
                    <div class="claude-subtitle">R$ ${plan.price_brl.toLocaleString('pt-BR')}/mês</div>
                </div>
            </div>

            <div class="claude-stats">
                <div class="claude-stat">
                    <div class="claude-stat-label">Janela 5h</div>
                    <div class="claude-stat-value">${usage.window_5h.messages}</div>
                    <div class="claude-stat-sub">de ${usage.window_5h.limit} msgs</div>
                    <div class="progress-bar">
                        <div class="progress-fill ${statusClass}" style="width: ${Math.min(pct5h, 100)}%"></div>
                    </div>
                    <div class="text-xs text-muted mt-1">Reset: ${usage.window_5h.next_reset_formatted}</div>
                </div>

                <div class="claude-stat">
                    <div class="claude-stat-label">Janela 7d</div>
                    <div class="claude-stat-value">${usage.window_7d.messages.toLocaleString()}</div>
                    <div class="claude-stat-sub">de ${(usage.window_7d.limit / 1000).toFixed(0)}K msgs</div>
                    <div class="progress-bar">
                        <div class="progress-fill healthy" style="width: ${Math.min(usage.window_7d.percent, 100)}%"></div>
                    </div>
                </div>
            </div>

            ${tips.length > 0 ? `
                <div class="mt-4 p-3 bg-black/20 rounded-lg">
                    <div class="text-xs font-medium text-orange-400 mb-1">💡 Dica</div>
                    <div class="text-sm text-secondary">${tips[0].message}</div>
                </div>
            ` : ''}
        </div>
    `;
}

function renderSpeedTest(data) {
    const container = document.getElementById('speedtest-results');
    if (!container) return;

    if (!data || data.status === 'error') {
        container.innerHTML = `
            <div class="text-center text-muted py-8">
                <div class="text-4xl mb-2">📡</div>
                <div>Nenhum teste realizado</div>
            </div>
        `;
        return;
    }

    const provider = data.provider?.provider_name || 'Unknown';

    container.innerHTML = `
        <div class="speedtest-container">
            <div class="speedtest-metric">
                <div class="speedtest-value text-green">${data.download_mbps}</div>
                <div class="speedtest-unit">Mbps</div>
                <div class="speedtest-label">⬇️ Download</div>
            </div>
            <div class="speedtest-metric">
                <div class="speedtest-value text-blue">${data.upload_mbps}</div>
                <div class="speedtest-unit">Mbps</div>
                <div class="speedtest-label">⬆️ Upload</div>
            </div>
            <div class="speedtest-metric">
                <div class="speedtest-value text-orange">${data.latency_ms}</div>
                <div class="speedtest-unit">ms</div>
                <div class="speedtest-label">📍 Latência</div>
            </div>
        </div>
        <div class="text-center mt-4 text-sm text-muted">
            ${provider} • ${data.provider?.city || ''}, ${data.provider?.country || 'BR'}
        </div>
    `;
}

function renderMonitors(monitors) {
    const container = document.getElementById('monitors-visual');
    if (!container || !monitors.length) return;

    // Calculate scale based on max resolution
    const maxWidth = Math.max(...monitors.map(m => m.resolution.width));
    const scale = 200 / maxWidth; // 200px max width

    const monitorsHtml = monitors.map(m => {
        const width = m.resolution.width * scale;
        const height = m.resolution.height * scale;

        return `
            <div class="monitor ${m.is_main ? 'main' : ''}" style="width: ${width}px">
                ${m.is_main ? '<span class="monitor-badge">★</span>' : ''}
                <div class="monitor-screen" style="width: ${width - 16}px; height: ${height - 16}px">
                    ${m.resolution.width}x${m.resolution.height}
                </div>
                <div class="monitor-stand"></div>
                <div class="monitor-label">
                    ${m.name}<br>
                    <span class="text-muted">${m.refresh_rate}Hz</span>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="monitors-container">
            ${monitorsHtml}
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════
// QUICK LINKS
// ═══════════════════════════════════════════════════════════════════════

async function openQuickLink(action) {
    try {
        await fetchAPI('/open-app', {
            method: 'POST',
            body: JSON.stringify({ action }),
            ttl: 0
        });
        showToast('Abrindo...', 'info');
    } catch (error) {
        showToast('Erro ao abrir', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════════════
// UI UTILITIES
// ═══════════════════════════════════════════════════════════════════════

function showSkeleton(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="space-y-3">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-block"></div>
            </div>
        `;
    }
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center text-red py-8">
                <div class="text-4xl mb-2">⚠️</div>
                <div>${message}</div>
            </div>
        `;
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${getToastIcon(type)}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toast-in 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function getToastIcon(type) {
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    return icons[type] || icons.info;
}

// ═══════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════

const switchTab = debounce(function(tabId) {
    // Update active tab
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });

    // Update content sections
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('hidden', content.id !== `${tabId}-content`);
    });

    // Load data for the tab
    loadTabData(tabId);
}, 300);

function loadTabData(tabId) {
    switch(tabId) {
        case 'nerdspace':
            loadNerdSpace();
            loadClaudeUsage();
            loadSpeedTest();
            loadMonitors();
            break;
        case 'hardware':
            loadHardware();
            break;
        case 'storage':
            loadStorage();
            break;
        case 'processes':
            loadProcesses();
            break;
        case 'network':
            loadNetwork();
            break;
        case 'battery':
            loadBattery();
            break;
    }
}

// Legacy loaders (keep for compatibility)
async function loadHardware() {
    const data = await fetchAPI('/hardware', { ttl: 300000 });
    // Render hardware...
}

async function loadStorage() {
    const data = await fetchAPI('/storage', { ttl: 60000 });
    // Render storage...
}

async function loadProcesses() {
    const data = await fetchAPI('/processes', { ttl: 10000 });
    // Render processes...
}

async function loadNetwork() {
    const data = await fetchAPI('/network', { ttl: 15000 });
    // Render network...
}

async function loadBattery() {
    const data = await fetchAPI('/battery', { ttl: 30000 });
    // Render battery...
}

// ═══════════════════════════════════════════════════════════════════════
// WEBSOCKET FOR REAL-TIME UPDATES
// ═══════════════════════════════════════════════════════════════════════

let ws = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateRealTimeMetrics(data);
    };

    ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function updateRealTimeMetrics(data) {
    // Update CPU
    const cpuEl = document.getElementById('cpu-percent');
    if (cpuEl) cpuEl.textContent = `${data.cpu.percent}%`;

    // Update RAM
    const ramEl = document.getElementById('ram-percent');
    if (ramEl) ramEl.textContent = `${data.memory.percent}%`;

    // Update Disk
    const diskEl = document.getElementById('disk-percent');
    if (diskEl) diskEl.textContent = `${data.disk.percent}%`;
}

// ═══════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Initialize tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Load initial tab (NERD SPACE)
    switchTab('nerdspace');

    // Connect WebSocket
    connectWebSocket();

    console.log('🚀 NERD SPACE V5.0 - AI FIRST Edition initialized');
});
