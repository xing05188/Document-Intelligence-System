<script setup>
import { ref, computed } from 'vue'
import { useWorkflowStore } from '../../stores/workflowStore'

const workflowStore = useWorkflowStore()

// Transform-based pan state
const pan = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panStart = ref({ mouseX: 0, mouseY: 0, panX: 0, panY: 0 })

// Canvas style computed from pan transform
const canvasStyle = computed(() => ({
  transform: `translate(${pan.value.x}px, ${pan.value.y}px)`
}))

// Node drag state
const isDraggingNode = ref(false)
const dragNodeId = ref(null)
const dragStart = ref({ mouseX: 0, mouseY: 0, nodeX: 0, nodeY: 0 })

function handleNodeClick(event, nodeId) {
  event.stopPropagation()
  workflowStore.selectNode(nodeId)
}

function handleNodeDelete(event, nodeId) {
  event.stopPropagation()
  workflowStore.deleteNode(nodeId)
}

// Canvas pan
function onCanvasMouseDown(event) {
  if (event.button !== 0) return
  if (event.target.closest('.workflow-node')) return
  isPanning.value = true
  panStart.value = {
    mouseX: event.clientX,
    mouseY: event.clientY,
    panX: pan.value.x,
    panY: pan.value.y
  }
  event.preventDefault()
}

function onCanvasMouseMove(event) {
  if (isPanning.value) {
    const dx = event.clientX - panStart.value.mouseX
    const dy = event.clientY - panStart.value.mouseY
    pan.value = {
      x: panStart.value.panX + dx,
      y: panStart.value.panY + dy
    }
  } else if (isDraggingNode.value && dragNodeId.value) {
    const dx = event.clientX - dragStart.value.mouseX
    const dy = event.clientY - dragStart.value.mouseY
    workflowStore.updateNodePosition(dragNodeId.value, dragStart.value.nodeX + dx, dragStart.value.nodeY + dy)
  }
}

function onCanvasMouseUp() {
  isPanning.value = false
  isDraggingNode.value = false
  dragNodeId.value = null
}

// Node drag
function onNodeMouseDown(event, nodeId) {
  event.stopPropagation()
  event.preventDefault()
  const node = workflowStore.canvasNodes.find(n => n.id === nodeId)
  if (!node) return
  isDraggingNode.value = true
  dragNodeId.value = nodeId
  dragStart.value = {
    mouseX: event.clientX,
    mouseY: event.clientY,
    nodeX: node.x,
    nodeY: node.y
  }
}

function handleCanvasClick(event) {
  if (event.target.classList.contains('canvas-area') || event.target.classList.contains('canvas-inner')) {
    workflowStore.selectNode(null)
  }
}

// 预计算连接线数据
const connPaths = computed(() => {
  const nodes = workflowStore.canvasNodes
  return nodes.slice(0, -1).map((fromNode, i) => {
    const toNode = nodes[i + 1]
    const x1 = fromNode.x + 220
    const x2 = toNode.x
    const y = fromNode.y + 75
    return {
      d: `M ${x1} ${y} Q ${(x1 + x2) / 2} ${y} ${x2} ${y}`,
      key: `conn-${i}`,
      fromId: fromNode.id,
      toId: toNode.id
    }
  })
})

// 当前选中节点在数组中的索引
const selectedIndex = computed(() => {
  if (!workflowStore.selectedNodeId) return -1
  return workflowStore.canvasNodes.findIndex(n => n.id === workflowStore.selectedNodeId)
})
</script>

<template>
  <div class="workflow-canvas">
    <!-- Canvas Area -->
    <div
      class="canvas-area"
      :class="{ 'is-panning': isPanning }"
      @click="handleCanvasClick"
      @mousedown="onCanvasMouseDown"
      @mousemove="onCanvasMouseMove"
      @mouseup="onCanvasMouseUp"
      @mouseleave="onCanvasMouseUp"
    >
      <!-- Step Indicator (outside transform, stays fixed at top) -->
      <div class="canvas-step-bar">
        <template v-for="(node, i) in workflowStore.canvasNodes" :key="'step-' + node.id">
          <div
            class="step-item"
            :class="{
              'step-done': selectedIndex > -1 && i < selectedIndex,
              'step-active': workflowStore.selectedNodeId === node.id
            }"
          >
            <div class="step-num">{{ i + 1 }}</div>
            <div class="step-name">{{ node.title }}</div>
          </div>
          <div v-if="i < workflowStore.canvasNodes.length - 1" class="step-line" :key="'line-' + i"></div>
        </template>
      </div>

      <!-- Inner transformable container (nodes + connections move) -->
      <div class="canvas-inner" :style="canvasStyle">
        <!-- SVG Connections -->
        <svg class="connections-svg">
          <path
            v-for="cp in connPaths"
            :key="cp.key"
            :d="cp.d"
            class="conn-path"
            :class="{
              'conn-selected':
                workflowStore.selectedNodeId === cp.fromId ||
                workflowStore.selectedNodeId === cp.toId
            }"
          />
        </svg>

        <!-- Nodes -->
        <div
          v-for="(node, i) in workflowStore.canvasNodes"
          :key="node.id"
          class="workflow-node"
          :class="{ selected: workflowStore.selectedNodeId === node.id, ['type-' + node.type]: true }"
          :style="{ left: node.x + 'px', top: node.y + 'px' }"
          @click="handleNodeClick($event, node.id)"
          @mousedown="onNodeMouseDown($event, node.id)"
        >
          <div class="node-selected-badge">当前选中</div>
          <div class="node-port input-port"></div>
          <div class="node-header">
            <div class="node-icon" :class="node.type + '-icon'">{{ node.icon }}</div>
            <span class="node-title">{{ node.title }}</span>
            <span class="node-step-tag">Step {{ i + 1 }}</span>
            <button
              class="node-delete-btn"
              title="删除节点"
              @click.stop="handleNodeDelete($event, node.id)"
            >×</button>
          </div>
          <div class="node-body">{{ node.body }}</div>
          <div class="node-port output-port"></div>
        </div>
      </div>
    </div>
  </div>
</template>
