<script setup>
import { ref, computed } from 'vue'
import { useTabStore } from '../stores/tabStore'
import { useAuthStore } from '../stores/authStore'
import { useSessionStore } from '../stores/sessionStore'
import SvgIcon from './icons/SvgIcon.vue'

import LibrarySidebar from './library/LibrarySidebar.vue'
import ChatSidebar from './chat/ChatSidebar.vue'
import WorkflowSidebar from './workflow/WorkflowSidebar.vue'

const tabStore = useTabStore()
const authStore = useAuthStore()
const sessionStore = useSessionStore()

const isCollapsed = ref(false)

const navItems = [
  { id: 'chat', label: '智能对话', icon: 'chat' },
  { id: 'library', label: '文档库', icon: 'book' },
  { id: 'workflow', label: '工作流编排', icon: 'workflow' }
]

const isActive = computed(
  () => (tabId) => tabStore.currentTab === tabId
)

const currentTab = computed(() => tabStore.currentTab)

function handleTabClick(tabId) {
  tabStore.switchTab(tabId)
}

async function handleLogout() {
  await sessionStore.disconnectWebSocket()
  await authStore.logout()
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <!-- 顶部：应用图标 + 收缩按钮 -->
    <div class="sidebar-header">
      <div class="app-brand">
        <div class="app-icon"><SvgIcon name="document" :size="24" /></div>
        <div v-if="!isCollapsed" class="app-title">文档智能系统</div>
      </div>
      <button 
        class="collapse-btn" 
        :title="isCollapsed ? '展开' : '收缩'"
        @click="toggleCollapse"
      >
        <span class="collapse-symbol">{{ isCollapsed ? '›' : '‹' }}</span>
      </button>
    </div>

    <!-- 功能导航 -->
    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.id"
        class="nav-item"
        :class="{ active: isActive(item.id) }"
        :title="item.label"
        @click="handleTabClick(item.id)"
      >
        <span class="nav-icon"><SvgIcon :name="item.icon" :size="20" /></span>
        <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <!-- 视图专用侧边栏（渲染到侧边栏中间的空白区） -->
    <div v-if="!isCollapsed" class="sidebar-secondary">
      <component v-if="currentTab === 'chat'" :is="ChatSidebar" />
      <component v-else-if="currentTab === 'library'" :is="LibrarySidebar" />
      <component v-else-if="currentTab === 'workflow'" :is="WorkflowSidebar" />
    </div>

    <!-- 底部：用户区域 -->
    <div class="sidebar-footer">
      <div class="user-section">
        <div 
          class="user-avatar-small" 
          :title="authStore.userDisplayName"
        >
          {{ authStore.userAvatar }}
        </div>
        <div v-if="!isCollapsed" class="user-info-small">
          <div class="user-name-small">{{ authStore.userDisplayName }}</div>
        </div>
      </div>

      <button 
        class="logout-btn-small" 
        title="退出登录"
        @click="handleLogout"
      >
        <span class="logout-symbol">↪</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 300px;
  height: 100vh;
  background: var(--bg-secondary, #f8f9fa);
  border-right: 1px solid var(--border-color, #e5e5e5);
  display: flex;
  flex-direction: column;
  padding: 12px 8px;
  transition: width 0.3s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 80px;
}

/* 顶部头部 */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  gap: 8px;
  margin-bottom: 14px;
}

.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 12px 4px;
}

.app-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.app-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.app-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1a1a1a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border-color, #d0d0d0);
  background: var(--bg-primary, #fff);
  color: var(--text-secondary, #595959);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: auto;
}

.collapse-symbol {
  font-size: 18px;
  line-height: 1;
  font-weight: 300;
}

.collapse-btn:hover {
  background: var(--bg-tertiary, #f0f1f5);
  color: var(--text-primary, #1a1a1a);
}

.sidebar.collapsed .collapse-btn {
  width: 32px;
  height: 32px;
  margin-left: 0;
}

/* 导航菜单 */
    .sidebar-nav {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.sidebar.collapsed .sidebar-nav {
  align-items: center;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 8px;
  width: 44px;
  height: 44px;
}

/* 中间的视图专用侧边栏区域，会填充导航和底部之间的空白 */
.sidebar-secondary {
  flex: 1;
  overflow: auto;
  padding: 8px 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  min-height: 34px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary, #595959);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: var(--bg-tertiary, #f0f1f5);
  color: var(--text-primary, #1a1a1a);
}

.nav-item.active {
  background: rgba(102, 126, 234, 0.12);
  color: #667eea;
  border-color: rgba(102, 126, 234, 0.2);
}

.nav-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar.collapsed .nav-label {
  display: none;
}

/* 底部用户区域 */
.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--border-color, #e5e5e5);
  padding-top: 16px;
  margin-top: auto;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.user-avatar-small {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-info-small {
  flex: 1;
  min-width: 0;
}

.user-name-small {
  font-size: 12px;
  color: var(--text-secondary, #595959);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn-small {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border-color, #d0d0d0);
  background: transparent;
  color: var(--text-secondary, #595959);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logout-symbol {
  font-size: 16px;
  line-height: 1;
}

.logout-btn-small:hover {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.sidebar.collapsed .sidebar-footer {
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
}

.sidebar.collapsed .user-section {
  justify-content: center;
  width: 100%;
}

.sidebar.collapsed .user-info-small {
  display: none;
}

.sidebar.collapsed .logout-btn-small {
  width: 32px;
  height: 32px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }

  .sidebar.collapsed {
    width: 76px;
  }

  .sidebar-header {
    padding: 10px;
  }

  .nav-item {
    padding: 6px 8px;
    gap: 8px;
    min-height: 30px;
  }

  .nav-icon {
    font-size: 14px;
  }
}

@media (max-width: 640px) {
  .sidebar {
    width: 100%;
    height: auto;
    flex-direction: row;
    border-right: none;
    border-bottom: 1px solid var(--border-color, #e5e5e5);
    padding: 8px 12px;
  }

  .sidebar.collapsed {
    width: 100%;
  }

  .sidebar-header {
    order: 1;
    padding: 0;
    gap: 12px;
    margin-bottom: 0;
  }

  .app-icon {
    display: none;
  }

  .app-title {
    display: none;
  }

  .sidebar-nav {
    order: 2;
    flex-direction: row;
    flex: 1;
    gap: 4px;
    margin-bottom: 0;
    margin-left: 12px;
  }

  .nav-label {
    display: none !important;
  }

  .sidebar-footer {
    order: 3;
    border-top: none;
    border-left: 1px solid var(--border-color, #e5e5e5);
    padding-left: 12px;
    margin-left: 12px;
    padding-top: 0;
    flex-direction: row;
  }

  .nav-item {
    padding: 5px 7px;
    min-height: 28px;
  }

  .nav-icon {
    font-size: 16px;
  }
}
</style>
