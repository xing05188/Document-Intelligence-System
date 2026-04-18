<script setup>
import { ref } from 'vue'
import { useWorkflowStore } from '../../stores/workflowStore'

const workflowStore = useWorkflowStore()

const toolboxSearch = ref('')
const activeSection = ref('workflow') // 'workflow' | 'toolbox'

function handleWorkflowClick(workflowId) {
  workflowStore.selectWorkflow(workflowId)
}

function handleNewWorkflow() {
  workflowStore.createNewWorkflow()
}

function handleSearch(e) {
  workflowStore.setSearchQuery(e.target.value)
}
</script>

<template>
  <aside class="workflow-sidebar">

    <!-- Section Switcher -->
    <div class="sidebar-switcher">
      <button
        class="switcher-btn"
        :class="{ active: activeSection === 'workflow' }"
        @click="activeSection = 'workflow'"
      >
        <span>📋</span> 工作流
      </button>
      <button
        class="switcher-btn"
        :class="{ active: activeSection === 'toolbox' }"
        @click="activeSection = 'toolbox'"
      >
        <span>🧩</span> 组件库
      </button>
    </div>

    <!-- ===================== 工作流面板 ===================== -->
    <template v-if="activeSection === 'workflow'">
      <!-- New Workflow -->
      <div class="sidebar-section">
        <button class="new-workflow-btn" @click="handleNewWorkflow">
          <span>+</span>
          <span>新建工作流</span>
        </button>
      </div>

      <!-- Search -->
      <div class="sidebar-section sidebar-search">
        <input
          type="text"
          placeholder="搜索工作流..."
          :value="workflowStore.searchQuery"
          @input="handleSearch"
        />
      </div>

      <!-- Workflow List -->
      <div class="sidebar-scroll">
        <div class="workflow-group">
          <div class="workflow-group-title">我的工作流</div>
          <div
            v-for="wf in workflowStore.customWorkflows"
            :key="wf.id"
            class="workflow-item"
            :class="{ active: workflowStore.currentWorkflowId === wf.id }"
            @click="handleWorkflowClick(wf.id)"
          >
            <span class="workflow-icon">{{ wf.icon }}</span>
            <div class="workflow-info">
              <span class="workflow-name">{{ wf.name }}</span>
              <span class="workflow-time">{{ wf.time }}</span>
            </div>
          </div>
        </div>

        <div class="workflow-group">
          <div class="workflow-group-title">预设模板</div>
          <div
            v-for="wf in workflowStore.templateWorkflows"
            :key="wf.id"
            class="workflow-item"
            :class="{ active: workflowStore.currentWorkflowId === wf.id }"
            @click="handleWorkflowClick(wf.id)"
          >
            <span class="workflow-icon">{{ wf.icon }}</span>
            <div class="workflow-info">
              <span class="workflow-name">{{ wf.name }}</span>
              <span class="workflow-time">{{ wf.time }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ===================== 组件库面板 ===================== -->
    <template v-else>
      <!-- Search -->
      <div class="sidebar-section sidebar-search">
        <input
          type="text"
          v-model="toolboxSearch"
          placeholder="搜索组件..."
        />
      </div>

      <!-- Toolbox -->
      <div class="sidebar-scroll">
        <div
          v-for="section in workflowStore.toolboxItems"
          :key="section.section"
          class="toolbox-section"
        >
          <div class="toolbox-section-title">{{ section.section }}</div>
          <div
            v-for="item in section.items"
            :key="item.name"
            class="toolbox-item"
          >
            <div class="toolbox-item-icon">{{ item.icon }}</div>
            <span class="toolbox-item-name">{{ item.name }}</span>
          </div>
        </div>
      </div>
    </template>

  </aside>
</template>
