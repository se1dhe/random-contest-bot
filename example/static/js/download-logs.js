/**
 * JavaScript для страницы логов скачиваний
 */

let currentOffset = 0;
const limit = 50;
let hasMore = true;

async function loadStats() {
    try {
        const response = await fetch('/api/download-logs/stats');
        const data = await response.json();
        
        const statTotal = document.getElementById('statTotal');
        const statToday = document.getElementById('statToday');
        const statWeek = document.getElementById('statWeek');
        const statSuspicious = document.getElementById('statSuspicious');
        
        if (statTotal) statTotal.textContent = data.total_downloads || 0;
        if (statToday) statToday.textContent = data.downloads_today || 0;
        if (statWeek) statWeek.textContent = data.downloads_week || 0;
        if (statSuspicious) statSuspicious.textContent = data.suspicious_downloads?.length || 0;
        
        const topBotsDiv = document.getElementById('topBots');
        if (topBotsDiv) {
            if (data.top_bots && data.top_bots.length > 0) {
                topBotsDiv.innerHTML = data.top_bots.map((bot, index) => `
                    <div class="card">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <span class="text-2xl text-secondary">${index + 1}</span>
                                <div>
                                    <p class="font-semibold text-primary">${bot.bot_name}</p>
                                    <p class="text-sm text-secondary">ID: ${bot.bot_id}</p>
                                </div>
                            </div>
                            <div class="text-right">
                                <p class="text-xl font-bold text-accent-primary">${bot.download_count}</p>
                                <p class="text-xs text-secondary">скачиваний</p>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                topBotsDiv.innerHTML = '<p class="text-secondary">Нет данных</p>';
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

async function loadLogs(reset = false) {
    if (reset) {
        currentOffset = 0;
        hasMore = true;
        const logsTable = document.getElementById('logsTable');
        if (logsTable) {
            logsTable.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-secondary">Загрузка...</td></tr>';
        }
    }
    
    if (!hasMore) return;
    
    try {
        const userIdInput = document.getElementById('filterUserId');
        const botIdInput = document.getElementById('filterBotId');
        const userId = userIdInput ? userIdInput.value : '';
        const botId = botIdInput ? botIdInput.value : '';
        
        let url = `/api/download-logs?limit=${limit}&offset=${currentOffset}`;
        if (userId) url += `&user_id=${userId}`;
        if (botId) url += `&bot_id=${botId}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        const logsTable = document.getElementById('logsTable');
        if (!logsTable) return;
        
        if (reset) {
            logsTable.innerHTML = '';
        }
        
        if (data.logs && data.logs.length > 0) {
            data.logs.forEach(log => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${log.id}</td>
                    <td>
                        <div>
                            <p class="font-semibold text-primary">${log.user_username || 'N/A'}</p>
                            <p class="text-xs text-secondary">ID: ${log.user_id}</p>
                        </div>
                    </td>
                    <td>
                        <div>
                            <p class="font-semibold text-primary">${log.bot_name || 'N/A'}</p>
                            <p class="text-xs text-secondary">ID: ${log.bot_id}</p>
                        </div>
                    </td>
                    <td>
                        <span class="badge badge-primary">
                            v${log.version_number || 'N/A'}
                        </span>
                    </td>
                    <td>
                        <code class="text-sm">${log.ip_address}</code>
                    </td>
                    <td>
                        <p class="text-sm text-secondary truncate max-w-xs" title="${log.user_agent || 'N/A'}">
                            ${log.user_agent ? (log.user_agent.length > 50 ? log.user_agent.substring(0, 50) + '...' : log.user_agent) : 'N/A'}
                        </p>
                    </td>
                    <td>
                        <p class="text-sm text-secondary">${log.downloaded_at ? Utils.formatDateTime(log.downloaded_at) : 'N/A'}</p>
                    </td>
                `;
                logsTable.appendChild(row);
            });
            
            currentOffset += data.logs.length;
            hasMore = data.logs.length === limit;
            
            const logsCount = document.getElementById('logsCount');
            const loadMoreBtn = document.getElementById('loadMoreBtn');
            
            if (logsCount) logsCount.textContent = `Загружено: ${currentOffset}`;
            if (loadMoreBtn) loadMoreBtn.style.display = hasMore ? 'block' : 'none';
        } else {
            if (reset) {
                logsTable.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-secondary">Нет данных</td></tr>';
            }
            hasMore = false;
            const loadMoreBtn = document.getElementById('loadMoreBtn');
            if (loadMoreBtn) loadMoreBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Ошибка загрузки логов:', error);
        const logsTable = document.getElementById('logsTable');
        if (logsTable) {
            logsTable.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-error">Ошибка загрузки данных</td></tr>';
        }
    }
}

function loadMore() {
    loadLogs(false);
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadLogs(true);
});

