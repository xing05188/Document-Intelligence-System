<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '../../stores/workflowStore'
import WorkflowCanvas from './WorkflowCanvas.vue'
import WorkflowConfig from './WorkflowConfig.vue'

const emit = defineEmits(['openBatchModal'])
const workflowStore = useWorkflowStore()

const rightCollapsed = ref(false)

const toggleTop = ref(0)

function updateToggleTop() {
  const view = document.querySelector('.workflow-view')
  if (view) {
    const rect = view.getBoundingClientRect()
    toggleTop.value = rect.top + rect.height / 2
  }
}

onMounted(() => {
  updateToggleTop()
  window.addEventListener('resize', updateToggleTop)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateToggleTop)
})

function openBatchModal() {
  emit('openBatchModal')
}
</script>

<template>
  <div class="workflow-view" :class="{ 'left-collapsed': leftCollapsed, 'right-collapsed': rightCollapsed }">
    <!-- Canvas (full width) -->
    <WorkflowCanvas @open-batch-modal="openBatchModal" />
    <!-- Right Sidebar -->
    <div class="sidebar-wrapper right-sidebar" :class="{ collapsed: rightCollapsed }">
      <WorkflowConfig v-show="!rightCollapsed" @open-batch-modal="openBatchModal" />
    </div>
  </div>

  <!-- Toggle buttons: fixed, always on top of everything -->
  <button
    class="sidebar-toggle right-toggle"
    :class="{ 'at-edge': rightCollapsed }"
    :style="{ top: toggleTop + 'px' }"
    :title="rightCollapsed ? '展开右侧栏' : '收起右侧栏'"
    @click="rightCollapsed = !rightCollapsed"
  >
    {{ rightCollapsed ? '◀' : '▶' }}
  </button>
</template>
