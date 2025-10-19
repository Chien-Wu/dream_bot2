// Admin Dashboard JavaScript

let allUsers = [];
let lastUpdateTime = null;

// Load users on page load
document.addEventListener('DOMContentLoaded', function() {
    loadUsers();
    // Auto-refresh every 10 seconds
    setInterval(refreshUsers, 10000);
});

/**
 * Load all users from API
 */
async function loadUsers() {
    try {
        const response = await fetch('/flask/admin/api/users');
        const data = await response.json();

        if (data.success) {
            allUsers = data.users;
            updateStats(data.stats);
            renderUsers(allUsers);
            updateLastUpdateTime();
        } else {
            showError('載入用戶列表失敗: ' + data.message);
        }
    } catch (error) {
        console.error('Failed to load users:', error);
        showError('網絡錯誤，請重試');
    }
}

/**
 * Refresh users (called by refresh button and auto-refresh)
 */
async function refreshUsers() {
    const btn = document.getElementById('refresh-btn');
    btn.disabled = true;
    btn.innerHTML = '⏳ 更新中...';

    await loadUsers();

    btn.disabled = false;
    btn.innerHTML = '🔄 重新整理';
}

/**
 * Update statistics cards
 */
function updateStats(stats) {
    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-active').textContent = stats.active;
    document.getElementById('stat-blocked').textContent = stats.blocked;
}

/**
 * Render users table
 */
function renderUsers(users) {
    const tbody = document.getElementById('user-table-body');
    const emptyState = document.getElementById('empty-state');

    if (users.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    tbody.innerHTML = users.map(user => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${escapeHtml(user.organization_name)}</div>
                ${user.is_new ? '<span class="text-xs text-green-600">新用戶</span>' : ''}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500 font-mono">${truncateUserId(user.user_id)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500">${formatDateTime(user.last_activity)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center">
                <label class="toggle-switch">
                    <input
                        type="checkbox"
                        ${user.is_blocked ? '' : 'checked'}
                        data-user-id="${user.user_id}"
                        onchange="toggleAI(this)"
                    >
                    <span class="toggle-slider"></span>
                </label>
                <div class="text-xs text-gray-600 mt-1">
                    ${user.is_blocked ? 'OFF' : 'ON'}
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Toggle AI status for user
 */
async function toggleAI(checkbox) {
    const userId = checkbox.dataset.userId;
    const newState = checkbox.checked;  // true = ON (not blocked), false = OFF (blocked)

    // Disable checkbox during API call
    checkbox.disabled = true;

    try {
        // Determine endpoint based on new state
        const endpoint = newState
            ? `/flask/admin/api/user/${userId}/unblock`  // Toggle ON = unblock
            : `/flask/admin/api/user/${userId}/block`;   // Toggle OFF = block

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (!result.success) {
            // Revert toggle if failed
            checkbox.checked = !newState;
            showError('操作失敗: ' + result.message);
        } else {
            // Update label
            const label = checkbox.closest('td').querySelector('.text-xs');
            label.textContent = checkbox.checked ? 'ON' : 'OFF';

            // Refresh stats
            await loadUsers();
        }

    } catch (error) {
        console.error('Failed to toggle AI:', error);
        // Revert toggle if error
        checkbox.checked = !newState;
        showError('網絡錯誤，請稍後再試');
    } finally {
        // Re-enable checkbox
        checkbox.disabled = false;
    }
}

/**
 * Filter users by search input
 */
function filterUsers() {
    const searchInput = document.getElementById('search').value.toLowerCase();

    if (!searchInput) {
        renderUsers(allUsers);
        return;
    }

    const filtered = allUsers.filter(user => {
        const orgName = user.organization_name.toLowerCase();
        const userId = user.user_id.toLowerCase();
        return orgName.includes(searchInput) || userId.includes(searchInput);
    });

    renderUsers(filtered);
}

/**
 * Update last update time display
 */
function updateLastUpdateTime() {
    lastUpdateTime = new Date();
    updateLastUpdateDisplay();

    // Update display every second
    setInterval(updateLastUpdateDisplay, 1000);
}

function updateLastUpdateDisplay() {
    if (!lastUpdateTime) return;

    const now = new Date();
    const diffSeconds = Math.floor((now - lastUpdateTime) / 1000);

    let text;
    if (diffSeconds < 60) {
        text = `${diffSeconds} 秒前更新`;
    } else if (diffSeconds < 3600) {
        const minutes = Math.floor(diffSeconds / 60);
        text = `${minutes} 分鐘前更新`;
    } else {
        const hours = Math.floor(diffSeconds / 3600);
        text = `${hours} 小時前更新`;
    }

    document.getElementById('last-update').textContent = text;
}

/**
 * Utility Functions
 */

function truncateUserId(userId) {
    if (userId.length <= 12) return userId;
    return userId.substring(0, 8) + '...';
}

function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '-';

    const date = new Date(dateTimeStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return '剛剛';
    if (diffMins < 60) return `${diffMins} 分鐘前`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} 小時前`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} 天前`;

    // Return formatted date
    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    // Simple alert for now, can be improved with toast notifications
    alert(message);
}
