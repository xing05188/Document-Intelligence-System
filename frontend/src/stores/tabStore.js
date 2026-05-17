import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTabStore = defineStore('tab', () => {
  const currentTab = ref('library')

  const tabs = [
    { id: 'library', label: '文档库', icon: 'book' },
    { id: 'chat', label: '智能对话', icon: 'chat' },
    { id: 'workflow', label: '工作流编排', icon: 'workflow' }
  ]

  function switchTab(tabId) {
    currentTab.value = tabId
  }

  return {
    currentTab,
    tabs,
    switchTab
  }
})
