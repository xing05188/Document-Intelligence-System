<script setup>
import DocGrid from './DocGrid.vue'
import { useLibraryStore } from '../../stores/libraryStore'
import SvgIcon from '../icons/SvgIcon.vue'

const libraryStore = useLibraryStore()

function onSearch(event) {
  libraryStore.setSearchQuery(event.target.value)
}

function clearSearch() {
  libraryStore.setSearchQuery('')
}
</script>

<template>
  <div class="library-view">
    <!-- Toolbar -->
    <div class="library-toolbar">
      <div class="library-title">
        <SvgIcon name="book" :size="22" />
        <span>文档库管理</span>
      </div>
      <div class="library-actions">
        <!-- 搜索框 -->
        <div class="search-box">
          <span class="search-icon"><SvgIcon name="search" :size="14" /></span>
          <input
            :value="libraryStore.searchQuery"
            class="search-input"
            placeholder="搜索文档..."
            @input="onSearch"
          />
          <button
            v-if="libraryStore.searchQuery"
            class="search-clear"
            type="button"
            @click="clearSearch"
          >
            ×
          </button>
        </div>

      </div>
    </div>

    <!-- Body: Content -->
    <div class="library-body">
      <DocGrid />
    </div>
  </div>
</template>

<style scoped>
.library-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

/* ---- Toolbar ---- */
.library-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 16px;
}

.library-title {
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
  white-space: nowrap;
}

.library-title :deep(.svg-icon) {
  color: var(--accent-primary);
}

.library-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ---- Search Box ---- */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  color: var(--text-muted);
  pointer-events: none;
  display: flex;
}

.search-input {
  padding: 9px 36px 9px 36px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  width: 220px;
  transition: all 0.25s ease;
  font-family: inherit;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-input:focus {
  border-color: var(--accent-primary);
  width: 280px;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
  background: var(--bg-primary);
}

.search-clear {
  position: absolute;
  right: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 18px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  line-height: 1;
}

.search-clear:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* ---- Action Buttons ---- */
.lib-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.lib-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-color-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.lib-btn.primary {
  background: var(--gradient-primary);
  border: none;
  color: white;
}

.lib-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
}

/* ---- Body ---- */
.library-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .library-toolbar {
    padding: 12px 16px;
    flex-wrap: wrap;
  }

  .library-title {
    font-size: 17px;
  }

  .search-input {
    width: 160px;
  }

  .search-input:focus {
    width: 200px;
  }

  .library-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 480px) {
  .library-toolbar {
    padding: 10px 12px;
  }

  .library-title {
    font-size: 15px;
  }

  .search-input {
    width: 140px;
    font-size: 12px;
    padding: 7px 30px 7px 30px;
  }

  .search-input:focus {
    width: 160px;
  }

  .lib-btn {
    padding: 7px 12px;
    font-size: 12px;
  }
}
</style>
