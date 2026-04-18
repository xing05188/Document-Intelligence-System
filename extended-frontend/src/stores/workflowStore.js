import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWorkflowStore = defineStore('workflow', () => {
  const currentWorkflowId = ref('wf1')
  const searchQuery = ref('')
  const workflowName = ref('论文翻译工作流')
  const inputLibrary = ref('论文翻译')
  const outputLibrary = ref('英文版论文')
  const targetLanguage = ref('英文')

  // 当前选中的节点 ID
  const selectedNodeId = ref('n1')

  // 每个节点的配置值（key: nodeId, value: { paramKey: paramValue })
  const nodeConfigs = ref({})

  const workflows = ref({
    'wf1': {
      id: 'wf1',
      name: '论文翻译工作流',
      icon: '🌍',
      time: '刚刚编辑',
      type: 'custom'
    },
    'wf2': {
      id: 'wf2',
      name: '合同审查工作流',
      icon: '⚖️',
      time: '昨天',
      type: 'custom'
    },
    'wf3': {
      id: 'wf3',
      name: '数据提取工作流',
      icon: '📊',
      time: '3天前',
      type: 'custom'
    },
    'tpl1': {
      id: 'tpl1',
      name: '文档分析模板',
      icon: '📄',
      time: '系统预设',
      type: 'template'
    },
    'tpl2': {
      id: 'tpl2',
      name: '批量摘要模板',
      icon: '📝',
      time: '系统预设',
      type: 'template'
    }
  })

  const selectedDocs = ref([
    { id: 1, name: '深度学习综述.pdf', size: '2.4MB' },
    { id: 2, name: '注意力机制研究.pdf', size: '1.8MB' },
    { id: 3, name: 'Transformer架构.pdf', size: '3.2MB' },
    { id: 4, name: 'GAN生成对抗网络.pdf', size: '2.1MB' }
  ])

  const toolboxItems = ref([
    { section: '输入', items: [
      { icon: '📕', name: 'PDF 输入' },
      { icon: '📝', name: 'MD 输入' },
      { icon: '📊', name: 'XLSX 输入' },
      { icon: '📘', name: 'DOCX 输入' }
    ]},
    { section: '处理', items: [
      { icon: '📖', name: '文档解析' },
      { icon: '🎯', name: '实体提取' },
      { icon: '✂️', name: '数据处理' }
    ]},
    { section: '输出', items: [
      { icon: '💾', name: '保存文件' },
      { icon: '📁', name: '输出到文档库' },
    ]}
  ])

  const canvasNodes = ref([
    {
      id: 'n1', type: 'input', icon: '📄', title: '文档输入',
      body: '从文档库选择多个文档',
      x: 30, y: 160,
      configValues: {
        inputLibrary: '论文翻译',
        fileTypes: ['PDF', 'Word (.docx)'],
        batchSize: 10,
        skipExisting: true
      }
    },
    {
      id: 'n2', type: 'parse', icon: '📖', title: '文档解析',
      body: '提取文本、表格、图表结构化数据',
      x: 330, y: 160,
      configValues: {
        parseMode: '标准解析（文本+结构）',
        extractTables: true,
        extractImages: true,
        extractCharts: false,
        ocrLang: '自动检测'
      }
    },
    {
      id: 'n3', type: 'ai', icon: '🤖', title: 'LLM 翻译',
      body: '使用大模型进行文档翻译',
      x: 590, y: 160,
      configValues: {
        targetLang: '英文',
        model: 'GPT-4o (推荐)',
        style: '学术论文',
        preserveFormat: true,
        systemPrompt: '你是一位专业的学术翻译。请将以下文档翻译为英文，保持学术论文的风格和格式，特别注意专业术语的一致性。'
      }
    },
    {
      id: 'n4', type: 'output', icon: '📁', title: '输出到文档库',
      body: '保存翻译结果到指定文档库空间',
      x: 850, y: 160,
      configValues: {
        outputLibrary: '英文版论文',
        namingRule: '{原名}_翻译',
        metaTag: 'AI翻译,2026',
        notifyOnComplete: true
      }
    }
  ])

  // 节点配置 Schema（定义每个节点的参数结构）
  const nodeSchemas = {
    n1: {
      icon: '📄', iconClass: 'input',
      title: '文档输入', subtitle: 'Step 1 of 4 · 输入节点',
      fields: [
        { key: 'inputLibrary', label: '输入文档库', type: 'select',
          options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
        { key: 'fileTypes', label: '文件类型', type: 'multiselect',
          options: ['PDF', 'Word (.docx)', 'Excel (.xlsx)', 'PPT', 'TXT', 'Markdown'] },
        { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' },
        { key: 'skipExisting', label: '跳过已处理文档', type: 'toggle' }
      ]
    },
    n2: {
      icon: '📖', iconClass: 'parse',
      title: '文档解析', subtitle: 'Step 2 of 4 · 处理节点',
      fields: [
        { key: 'parseMode', label: '解析模式', type: 'select',
          options: ['快速解析（仅文本）', '标准解析（文本+结构）', '深度解析（全量）'] },
        { key: 'extractTables', label: '提取表格', type: 'toggle' },
        { key: 'extractImages', label: '提取图片描述', type: 'toggle' },
        { key: 'extractCharts', label: '提取图表数据', type: 'toggle' },
        { key: 'ocrLang', label: 'OCR 语言', type: 'select',
          options: ['自动检测', '简体中文', '英文', '日文', '韩文', '多语言'] }
      ]
    },
    n3: {
      icon: '🤖', iconClass: 'ai',
      title: 'LLM 翻译', subtitle: 'Step 3 of 4 · AI 节点',
      fields: [
        { key: 'targetLang', label: '目标语言', type: 'select',
          options: ['英文', '中文', '日文', '韩文', '法文', '德文', '西班牙文'] },
        { key: 'model', label: '翻译模型', type: 'select',
          options: ['GPT-4o (推荐)', 'GPT-4o-mini', 'Claude 3.5 Sonnet', 'DeepSeek V3'] },
        { key: 'style', label: '翻译风格', type: 'select',
          options: ['学术论文', '商务正式', '通俗易懂', '保留原文风格'] },
        { key: 'preserveFormat', label: '保留原文格式', type: 'toggle' },
        { key: 'systemPrompt', label: '系统提示词', type: 'textarea' }
      ]
    },
    n4: {
      icon: '📁', iconClass: 'output',
      title: '输出到文档库', subtitle: 'Step 4 of 4 · 输出节点',
      fields: [
        { key: 'outputLibrary', label: '输出文档库', type: 'select',
          options: ['英文版论文', '翻译结果', '分析结果', '新建文档库...'] },
        { key: 'namingRule', label: '文件命名规则', type: 'input' },
        { key: 'metaTag', label: '自动打标签', type: 'input' },
        { key: 'notifyOnComplete', label: '完成通知', type: 'toggle' }
      ]
    }
  }

  const currentWorkflow = computed(() => workflows.value[currentWorkflowId.value])

  const customWorkflows = computed(() =>
    Object.values(workflows.value).filter(w => w.type === 'custom')
  )

  const templateWorkflows = computed(() =>
    Object.values(workflows.value).filter(w => w.type === 'template')
  )

  function selectWorkflow(workflowId) {
    currentWorkflowId.value = workflowId
    const wf = workflows.value[workflowId]
    if (wf) {
      workflowName.value = wf.name
    }
  }

  function createNewWorkflow() {
    const id = 'wf' + Date.now()
    workflows.value[id] = {
      id,
      name: '新建工作流',
      icon: '🔧',
      time: '刚刚',
      type: 'custom'
    }
    currentWorkflowId.value = id
    workflowName.value = '新建工作流'
  }

  function setSearchQuery(query) {
    searchQuery.value = query
  }

  function updateWorkflowName(name) {
    workflowName.value = name
    const wf = workflows.value[currentWorkflowId.value]
    if (wf) {
      wf.name = name
    }
  }

  function selectNode(nodeId) {
    selectedNodeId.value = nodeId
  }

  function updateNodePosition(nodeId, x, y) {
    const node = canvasNodes.value.find(n => n.id === nodeId)
    if (node) {
      node.x = x
      node.y = y
    }
  }

  function updateNodeConfig(nodeId, key, value) {
    const node = canvasNodes.value.find(n => n.id === nodeId)
    if (node) {
      if (!node.configValues) node.configValues = {}
      node.configValues[key] = value
    }
  }

  const selectedNode = computed(() =>
    canvasNodes.value.find(n => n.id === selectedNodeId.value)
  )

  return {
    currentWorkflowId,
    searchQuery,
    workflowName,
    inputLibrary,
    outputLibrary,
    targetLanguage,
    selectedNodeId,
    selectedNode,
    nodeConfigs,
    nodeSchemas,
    workflows,
    selectedDocs,
    toolboxItems,
    canvasNodes,
    currentWorkflow,
    customWorkflows,
    templateWorkflows,
    selectWorkflow,
    createNewWorkflow,
    setSearchQuery,
    updateWorkflowName,
    selectNode,
    updateNodePosition,
    updateNodeConfig
  }
})
