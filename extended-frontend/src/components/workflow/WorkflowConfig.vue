<script setup>
import { ref, computed } from 'vue'
import { useWorkflowStore } from '../../stores/workflowStore'

const emit = defineEmits(['openBatchModal'])
const workflowStore = useWorkflowStore()

const activeTab = ref('node') // 'node' | 'wf'

function openBatchModal() {
  emit('openBatchModal')
}

function switchTab(tab) {
  activeTab.value = tab
}

function updateConfig(key, value) {
  const nodeId = workflowStore.selectedNodeId
  if (nodeId) {
    workflowStore.updateNodeConfig(nodeId, key, value)
  }
}

function toggleMulti(key, option, checked) {
  const nodeId = workflowStore.selectedNodeId
  if (!nodeId) return
  const cfg = workflowStore.selectedNode?.configValues
  if (!cfg) return
  const current = Array.isArray(cfg[key]) ? [...cfg[key]] : []
  if (checked) {
    if (!current.includes(option)) current.push(option)
  } else {
    const idx = current.indexOf(option)
    if (idx > -1) current.splice(idx, 1)
  }
  updateConfig(key, current)
}

// 根据 field type 渲染对应控件的当前值
function getFieldValue(field, node) {
  if (!node || !node.configValues) return null
  return node.configValues[field.key] ?? null
}

// 获取节点配置 Schema：优先用节点自带的 schema，否则从 nodeSchemas 按 id 查找
function getNodeSchema(node) {
  if (!node) return null
  return node.schema || workflowStore.nodeSchemas[node.id] || null
}
</script>

<template>
  <div class="workflow-config-panel">

    <!-- Tab Bar -->
    <div class="config-tabs">
      <button
        class="config-tab"
        :class="{ active: activeTab === 'node' }"
        @click="switchTab('node')"
      >
        <span>📋</span> 节点配置
      </button>
      <button
        class="config-tab"
        :class="{ active: activeTab === 'wf' }"
        @click="switchTab('wf')"
      >
        <span>⚙️</span> 全局设置
      </button>
    </div>

    <!-- Panel Content -->
    <div class="config-content">

      <!-- ======== 全局设置 ======== -->
      <div v-if="activeTab === 'wf'" class="config-section">
        <div class="node-config-header">
          <div class="node-config-icon-wrap input-icon">🌍</div>
          <div>
            <div class="node-config-title">{{ workflowStore.workflowName }}</div>
            <div class="node-config-subtitle">全局配置 · {{ workflowStore.canvasNodes.length }} 个节点</div>
          </div>
        </div>

        <div class="config-group">
          <div class="config-group-label">基础信息</div>
          <div class="field-row">
            <div class="field">
              <label class="field-label">工作流名称</label>
              <input
                class="config-input"
                :value="workflowStore.workflowName"
                @input="$emit('update:workflowName', $event.target.value)"
              />
            </div>
          </div>
          <div class="field-row">
            <div class="field">
              <label class="field-label">输入文档库</label>
              <select class="config-select" v-model="workflowStore.inputLibrary">
                <option>论文翻译</option>
                <option>合同审查</option>
                <option>年报分析</option>
                <option>数据提取</option>
                <option>自定义...</option>
              </select>
            </div>
            <div class="field">
              <label class="field-label">输出文档库</label>
              <select class="config-select" v-model="workflowStore.outputLibrary">
                <option>英文版论文</option>
                <option>翻译结果</option>
                <option>分析结果</option>
                <option>新建文档库...</option>
              </select>
            </div>
          </div>
        </div>

        <div class="config-group">
          <div class="config-group-label">运行设置</div>
          <div class="field">
            <label class="field-label">并发数量</label>
            <div class="range-row">
              <input type="range" min="1" max="10" value="3" class="range-input" />
              <span class="range-val">3</span>
            </div>
          </div>
          <div class="field field-toggle-row">
            <label class="field-label">出错时继续</label>
            <div class="toggle-switch on" onclick="this.classList.toggle('on')"></div>
          </div>
          <div class="field field-toggle-row">
            <label class="field-label">出错通知</label>
            <div class="toggle-switch on" onclick="this.classList.toggle('on')"></div>
          </div>
        </div>
      </div>

      <!-- ======== 节点配置 ======== -->
      <div v-else-if="activeTab === 'node' && workflowStore.selectedNode" class="config-section node-config-anim">

        <!-- Step Indicator -->
        <div class="step-indicator">
          <div
            v-for="(node, i) in workflowStore.canvasNodes"
            :key="node.id"
            class="step-dot-wrap"
          >
            <div
              class="step-dot"
              :class="{
                'step-done': i < workflowStore.canvasNodes.findIndex(n => n.id === workflowStore.selectedNodeId),
                'step-active': workflowStore.selectedNodeId === node.id
              }"
            ></div>
            <div v-if="i < workflowStore.canvasNodes.length - 1" class="step-connector"></div>
          </div>
        </div>

        <!-- Node Header -->
        <div class="node-config-header">
          <div class="node-config-icon-wrap" :class="workflowStore.selectedNode.type + '-icon'">
            {{ workflowStore.selectedNode.icon }}
          </div>
          <div>
            <div class="node-config-title">{{ workflowStore.selectedNode.title }}</div>
            <div class="node-config-subtitle">{{ getNodeSchema(workflowStore.selectedNode)?.subtitle }}</div>
          </div>
        </div>

        <!-- Fields -->
        <div class="config-group">
          <div class="config-group-label">参数配置</div>

          <template v-for="field in getNodeSchema(workflowStore.selectedNode)?.fields" :key="field.key">

            <!-- Select -->
            <div v-if="field.type === 'select'" class="field">
              <label class="field-label">{{ field.label }}</label>
              <select
                class="config-select"
                :value="getFieldValue(field, workflowStore.selectedNode)"
                @change="updateConfig(field.key, $event.target.value)"
              >
                <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </div>

            <!-- Input -->
            <div v-else-if="field.type === 'input'" class="field">
              <label class="field-label">{{ field.label }}</label>
              <input
                class="config-input"
                type="text"
                :value="getFieldValue(field, workflowStore.selectedNode)"
                @input="updateConfig(field.key, $event.target.value)"
              />
            </div>

            <!-- Textarea -->
            <div v-else-if="field.type === 'textarea'" class="field">
              <label class="field-label">{{ field.label }}</label>
              <textarea
                class="config-textarea"
                :value="getFieldValue(field, workflowStore.selectedNode)"
                @input="updateConfig(field.key, $event.target.value)"
              ></textarea>
            </div>

            <!-- Range -->
            <div v-else-if="field.type === 'range'" class="field">
              <label class="field-label">{{ field.label }}</label>
              <div class="range-row">
                <input
                  type="range"
                  class="range-input"
                  :min="field.min"
                  :max="field.max"
                  :value="getFieldValue(field, workflowStore.selectedNode)"
                  @input="updateConfig(field.key, Number($event.target.value)); $nextTick(() => $event.target.nextElementSibling.textContent = $event.target.value + ' ' + field.unit)"
                />
                <span class="range-val">{{ getFieldValue(field, workflowStore.selectedNode) }} {{ field.unit }}</span>
              </div>
            </div>

            <!-- Toggle -->
            <div v-else-if="field.type === 'toggle'" class="field field-toggle-row">
              <label class="field-label">{{ field.label }}</label>
              <div
                class="toggle-switch"
                :class="{ on: getFieldValue(field, workflowStore.selectedNode) }"
                @click="updateConfig(field.key, !getFieldValue(field, workflowStore.selectedNode)); $event.target.classList.toggle('on')"
              ></div>
            </div>

            <!-- Multi-select tags -->
            <div v-else-if="field.type === 'multiselect'" class="field">
              <label class="field-label">{{ field.label }}</label>
              <div class="tag-grid">
                <div
                  v-for="opt in field.options"
                  :key="opt"
                  class="tag-chip"
                  :class="{ active: (getFieldValue(field, workflowStore.selectedNode) || []).includes(opt) }"
                  @click="toggleMulti(field.key, opt, !(getFieldValue(field, workflowStore.selectedNode) || []).includes(opt))"
                >{{ opt }}</div>
              </div>
            </div>

          </template>
        </div>

        <!-- Selected Docs Summary -->
        <div class="config-group">
          <div class="config-group-label">
            待处理文档 <span id="docCount">({{ workflowStore.selectedDocs.length }})</span>
          </div>
          <div class="selected-docs-list">
            <div
              v-for="doc in workflowStore.selectedDocs"
              :key="doc.id"
              class="selected-doc-item"
            >
              <span class="selected-doc-icon">📕</span>
              <span class="selected-doc-name">{{ doc.name }}</span>
              <span class="selected-doc-size">{{ doc.size }}</span>
            </div>
          </div>
        </div>

        <!-- Action Button -->
        <button class="config-btn" @click="openBatchModal">
          <span>▶</span>
          <span>开始批量处理</span>
        </button>
      </div>

      <!-- ======== 无选中节点 — 空状态 ======== -->
      <div v-else class="config-empty-state">
        <div class="empty-icon">⬡</div>
        <div class="empty-title">点击节点以配置</div>
        <div class="empty-desc">在画布上点击任意节点<br/>右侧将切换显示该节点的专属配置</div>
        <div class="empty-nodes-hint">
          <div class="empty-nodes-title">工作流节点</div>
          <div
            v-for="(node, i) in workflowStore.canvasNodes"
            :key="node.id"
            class="empty-node-item"
            :class="{ done: workflowStore.selectedNodeId && i < workflowStore.canvasNodes.findIndex(n => n.id === workflowStore.selectedNodeId) }"
          >
            <span class="empty-node-icon">{{ node.icon }}</span>
            <span>{{ node.title }}</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
