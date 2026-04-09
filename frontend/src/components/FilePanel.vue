<script setup>
import { computed, ref } from 'vue'
import { NUpload, NButton, NTag, NAlert, NScrollbar, useMessage } from 'naive-ui'
import { useSessionStore } from '../stores/sessionStore'

const message = useMessage()
const sessionStore = useSessionStore()
const isUploading = ref(false)

// 根据当前模式判断是否需要显示模板
const showTemplateTab = computed(() => {
  const config = sessionStore.currentModeConfig
  // 只要模式需要模板（必需或可选），就显示模板Tab
  return config.requiresTemplate !== false
})

// 判断是否有未上传必需模板
const templateRequired = computed(() => {
  return sessionStore.currentModeConfig.requiresTemplate === true
})

const templateOptional = computed(() => {
  return sessionStore.currentModeConfig.requiresTemplate === null
})

const hasTemplateWarning = computed(() => {
  if (templateRequired.value && sessionStore.selectedTemplateFiles.length === 0) {
    return 'warning'
  }
  return null
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getFileTypeTag(type) {
  const ext = type.split('.').pop().toLowerCase()
  const map = {
    pdf: 'error',
    doc: 'warning',
    docx: 'warning',
    xls: 'info',
    xlsx: 'info',
    txt: 'default',
  }
  return map[ext] || 'default'
}

async function handleUpload(file, fileType) {
  if (!sessionStore.currentSessionId) {
    message.warning('请先选择一个会话')
    return
  }
  isUploading.value = true
  try {
    await sessionStore.uploadFile(file.file, fileType)
    message.success('上传成功')
  } catch (e) {
    message.error('上传失败: ' + e.message)
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div>
    <!-- 警告提示 -->
    <n-alert
      v-if="hasTemplateWarning"
      type="warning"
      :title="templateRequired ? '请上传模板文件' : '提示'"
      class="mb-3"
      :bordered="false"
    >
      {{ templateRequired ? '当前模式需要模板文件才能正常工作' : '如需指定输出格式，请上传模板文件' }}
    </n-alert>

    <!-- 数据文件 -->
    <div class="mb-3">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-gray-700">
          数据文件
          <span class="text-gray-400 text-xs">({{ sessionStore.dataFiles.length }})</span>
        </span>
        <n-upload
          :custom-request="(options) => handleUpload(options.file, 'data')"
          :show-file-list="false"
          :disabled="isUploading"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.md"
        >
          <n-button size="small" :loading="isUploading">+ 上传数据</n-button>
        </n-upload>
      </div>

      <n-scrollbar x-scrollable v-if="sessionStore.dataFiles.length > 0">
        <div class="flex gap-2 pb-1">
          <div
            v-for="file in sessionStore.dataFiles"
            :key="file.id"
            :class="[
              'flex items-center gap-2 px-3 py-1.5 rounded border text-sm',
              file.is_selected ? 'bg-green-50 border-green-300' : 'bg-white border-gray-200'
            ]"
          >
            <input
              type="checkbox"
              :checked="file.is_selected"
              @change="sessionStore.toggleFileSelection(file.id, 'data', $event.target.checked)"
              class="w-4 h-4 text-green-600 rounded focus:ring-green-500"
            />
            <span class="truncate max-w-32">{{ file.file_name }}</span>
            <n-tag :type="getFileTypeTag(file.file_name)" size="tiny">{{ file.file_name.split('.').pop().toUpperCase() }}</n-tag>
            <span class="text-xs text-gray-400">{{ formatSize(file.file_size) }}</span>
            <button
              @click="sessionStore.deleteFile(file.id, 'data')"
              class="text-gray-400 hover:text-red-500"
            >
              ×
            </button>
          </div>
        </div>
      </n-scrollbar>
      <div v-else class="text-gray-400 text-sm">暂无数据文件</div>
    </div>

    <!-- 模板文件（条件显示） -->
    <div v-if="showTemplateTab">
      <div class="border-t pt-3">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-gray-700">
            模板文件
            <span class="text-gray-400 text-xs">({{ sessionStore.templateFiles.length }})</span>
          </span>
          <n-upload
            :custom-request="(options) => handleUpload(options.file, 'template')"
            :show-file-list="false"
            :disabled="isUploading"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.md"
          >
            <n-button size="small" :loading="isUploading">+ 上传模板</n-button>
          </n-upload>
        </div>

        <n-scrollbar x-scrollable v-if="sessionStore.templateFiles.length > 0">
          <div class="flex gap-2 pb-1">
            <div
              v-for="file in sessionStore.templateFiles"
              :key="file.id"
              :class="[
                'flex items-center gap-2 px-3 py-1.5 rounded border text-sm',
                file.is_selected ? 'bg-green-50 border-green-300' : 'bg-white border-gray-200'
              ]"
            >
              <input
                type="checkbox"
                :checked="file.is_selected"
                @change="sessionStore.toggleFileSelection(file.id, 'template', $event.target.checked)"
                class="w-4 h-4 text-green-600 rounded focus:ring-green-500"
              />
              <span class="truncate max-w-32">{{ file.file_name }}</span>
              <n-tag :type="getFileTypeTag(file.file_name)" size="tiny">{{ file.file_name.split('.').pop().toUpperCase() }}</n-tag>
              <span class="text-xs text-gray-400">{{ formatSize(file.file_size) }}</span>
              <button
                @click="sessionStore.deleteFile(file.id, 'template')"
                class="text-gray-400 hover:text-red-500"
              >
                ×
              </button>
            </div>
          </div>
        </n-scrollbar>
        <div v-else class="text-gray-400 text-sm">暂无模板文件</div>
      </div>
    </div>
  </div>
</template>
