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
  const selectedNodeId = ref(null)

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
      { icon: '📕', name: 'PDF 输入', type: 'input', title: 'PDF 输入', body: '导入 PDF 文件', schema: {
        icon: '📕', iconClass: 'input', subtitle: '输入节点',
        fields: [
          { key: 'inputLibrary', label: '输入文档库', type: 'select', options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
          { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' },
          { key: 'skipExisting', label: '跳过已处理文档', type: 'toggle' }
        ]
      }},
      { icon: '📝', name: 'MD 输入', type: 'input', title: 'MD 输入', body: '导入 Markdown 文件', schema: {
        icon: '📝', iconClass: 'input', subtitle: '输入节点',
        fields: [
          { key: 'inputLibrary', label: '输入文档库', type: 'select', options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
          { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' }
        ]
      }},
      { icon: '📊', name: 'XLSX 输入', type: 'input', title: 'XLSX 输入', body: '导入 Excel 表格数据', schema: {
        icon: '📊', iconClass: 'input', subtitle: '输入节点',
        fields: [
          { key: 'inputLibrary', label: '输入文档库', type: 'select', options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
          { key: 'sheetIndex', label: '工作表索引', type: 'input' },
          { key: 'hasHeader', label: '首行为表头', type: 'toggle' }
        ]
      }},
      { icon: '📘', name: 'DOCX 输入', type: 'input', title: 'DOCX 输入', body: '导入 Word 文档', schema: {
        icon: '📘', iconClass: 'input', subtitle: '输入节点',
        fields: [
          { key: 'inputLibrary', label: '输入文档库', type: 'select', options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
          { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' }
        ]
      }}
    ]},
    { section: '处理', items: [
      { icon: '📖', name: '文档解析', type: 'parse', title: '文档解析', body: '提取文本、表格、图表结构化数据', schema: {
        icon: '📖', iconClass: 'parse', subtitle: '处理节点',
        fields: [
          { key: 'parseMode', label: '解析模式', type: 'select', options: ['快速解析（仅文本）', '标准解析（文本+结构）', '深度解析（全量）'] },
          { key: 'extractTables', label: '提取表格', type: 'toggle' },
          { key: 'extractImages', label: '提取图片描述', type: 'toggle' },
          { key: 'extractCharts', label: '提取图表数据', type: 'toggle' }
        ]
      }},
      { icon: '🎯', name: '实体提取', type: 'parse', title: '实体提取', body: '使用 LLM 提取关键实体和关系', schema: {
        icon: '🎯', iconClass: 'parse', subtitle: '处理节点',
        fields: [
          { key: 'model', label: '提取模型', type: 'select', options: ['GPT-4o (推荐)', 'GPT-4o-mini', 'Claude 3.5 Sonnet', 'DeepSeek V3'] },
          { key: 'entityTypes', label: '实体类型', type: 'multiselect', options: ['人物', '组织', '地点', '时间', '金额', '事件', '术语'] },
          { key: 'relationTypes', label: '关系类型', type: 'input' }
        ]
      }},
      { icon: '✂️', name: '数据处理', type: 'parse', title: '数据处理', body: '清洗、转换、聚合数据', schema: {
        icon: '✂️', iconClass: 'parse', subtitle: '处理节点',
        fields: [
          { key: 'processMode', label: '处理模式', type: 'select', options: ['清洗', '转换', '聚合', '过滤', '排序'] },
          { key: 'processFields', label: '处理字段', type: 'input' }
        ]
      }},
      { icon: '🤖', name: 'AI 翻译', type: 'ai', title: 'AI 翻译', body: '使用大模型进行智能翻译处理', schema: {
        icon: '🤖', iconClass: 'ai', subtitle: 'AI 节点',
        fields: [
          { key: 'model', label: 'AI 模型', type: 'select', options: ['GPT-4o (推荐)', 'GPT-4o-mini', 'Claude 3.5 Sonnet', 'DeepSeek V3'] },
          { key: 'prompt', label: '处理提示词', type: 'textarea' }
        ]
      }}
    ]},
    { section: '输出', items: [
      { icon: '💾', name: '保存文件', type: 'output', title: '保存文件', body: '保存处理结果到本地文件', schema: {
        icon: '💾', iconClass: 'output', subtitle: '输出节点',
        fields: [
          { key: 'savePath', label: '保存路径', type: 'input' },
          { key: 'fileFormat', label: '文件格式', type: 'select', options: ['PDF', 'Word (.docx)', 'Excel (.xlsx)', 'Markdown', 'TXT'] }
        ]
      }},
      { icon: '📁', name: '输出到文档库', type: 'output', title: '输出到文档库', body: '保存结果到指定文档库空间', schema: {
        icon: '📁', iconClass: 'output', subtitle: '输出节点',
        fields: [
          { key: 'outputLibrary', label: '输出文档库', type: 'select', options: ['英文版论文', '翻译结果', '分析结果', '新建文档库...'] },
          { key: 'namingRule', label: '文件命名规则', type: 'input' },
          { key: 'metaTag', label: '自动打标签', type: 'input' },
          { key: 'notifyOnComplete', label: '完成通知', type: 'toggle' }
        ]
      }}
    ]}
  ])

  const canvasNodes = ref([])

  // 节点配置 Schema（定义每个节点的参数结构）
  const nodeSchemas = {
    'schema-pdf': {
      icon: '📕', iconClass: 'input',
      title: 'PDF 输入', subtitle: '输入节点',
      fields: [
        { key: 'inputLibrary', label: '输入文档库', type: 'select',
          options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
        { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' },
        { key: 'skipExisting', label: '跳过已处理文档', type: 'toggle' }
      ]
    },
    'schema-md': {
      icon: '📝', iconClass: 'input',
      title: 'MD 输入', subtitle: '输入节点',
      fields: [
        { key: 'inputLibrary', label: '输入文档库', type: 'select',
          options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
        { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' }
      ]
    },
    'schema-xlsx': {
      icon: '📊', iconClass: 'input',
      title: 'XLSX 输入', subtitle: '输入节点',
      fields: [
        { key: 'inputLibrary', label: '输入文档库', type: 'select',
          options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
        { key: 'sheetIndex', label: '工作表索引', type: 'input' },
        { key: 'hasHeader', label: '首行为表头', type: 'toggle' }
      ]
    },
    'schema-docx': {
      icon: '📘', iconClass: 'input',
      title: 'DOCX 输入', subtitle: '输入节点',
      fields: [
        { key: 'inputLibrary', label: '输入文档库', type: 'select',
          options: ['论文翻译', '合同审查', '年报分析', '数据提取', '自定义...'] },
        { key: 'batchSize', label: '批处理大小', type: 'range', min: 1, max: 50, unit: '个文档/批' }
      ]
    },
    'schema-extract': {
      icon: '🎯', iconClass: 'parse',
      title: '实体提取', subtitle: '处理节点',
      fields: [
        { key: 'model', label: '提取模型', type: 'select',
          options: ['GPT-4o (推荐)', 'GPT-4o-mini', 'Claude 3.5 Sonnet', 'DeepSeek V3'] },
        { key: 'entityTypes', label: '实体类型', type: 'multiselect',
          options: ['人物', '组织', '地点', '时间', '金额', '事件', '术语'] },
        { key: 'relationTypes', label: '关系类型', type: 'input' }
      ]
    },
    'schema-process': {
      icon: '✂️', iconClass: 'parse',
      title: '数据处理', subtitle: '处理节点',
      fields: [
        { key: 'processMode', label: '处理模式', type: 'select',
          options: ['清洗', '转换', '聚合', '过滤', '排序'] },
        { key: 'processFields', label: '处理字段', type: 'input' }
      ]
    },
    'schema-ai': {
      icon: '🤖', iconClass: 'ai',
      title: 'AI 翻译', subtitle: 'AI 节点',
      fields: [
        { key: 'model', label: 'AI 模型', type: 'select',
          options: ['GPT-4o (推荐)', 'GPT-4o-mini', 'Claude 3.5 Sonnet', 'DeepSeek V3'] },
        { key: 'prompt', label: '处理提示词', type: 'textarea' }
      ]
    },
    'schema-save': {
      icon: '💾', iconClass: 'output',
      title: '保存文件', subtitle: '输出节点',
      fields: [
        { key: 'savePath', label: '保存路径', type: 'input' },
        { key: 'fileFormat', label: '文件格式', type: 'select',
          options: ['PDF', 'Word (.docx)', 'Excel (.xlsx)', 'Markdown', 'TXT'] }
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
    canvasNodes.value = []
    selectedNodeId.value = null
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

  function addNode(type, icon, title, body, schema) {
    const id = 'n' + Date.now()
    const lastNode = canvasNodes.value[canvasNodes.value.length - 1]
    const x = lastNode ? lastNode.x + 260 : 30
    const y = lastNode ? lastNode.y : 160
    const newNode = {
      id,
      type,
      icon,
      title,
      body,
      x,
      y,
      configValues: {},
      schema: schema || null
    }
    canvasNodes.value.push(newNode)
    selectedNodeId.value = id
    return id
  }

  function deleteNode(nodeId) {
    const idx = canvasNodes.value.findIndex(n => n.id === nodeId)
    if (idx === -1) return
    canvasNodes.value.splice(idx, 1)
    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = canvasNodes.value.length > 0
        ? canvasNodes.value[Math.min(idx, canvasNodes.value.length - 1)].id
        : null
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
    updateNodeConfig,
    addNode,
    deleteNode
  }
})
