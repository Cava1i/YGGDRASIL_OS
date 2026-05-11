<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as XLSX from 'xlsx'
import { api, API_BASE, resolveApiUrl } from '../api'

const props = defineProps(['token', 'username', 'competitionId'])
const tasks = ref([])
const loading = ref(true)
let eventSource = null

// Sort and Filter state
const sortKey = ref('created_at')
const sortOrder = ref('asc') // 'asc' or 'desc'
const filterContent = ref('')
const copyStatus = ref({}) // Store copy status for each task

const copyToClipboard = async (text, taskId) => {
  try {
    await navigator.clipboard.writeText(text)
    copyStatus.value[taskId] = true
    setTimeout(() => {
      copyStatus.value[taskId] = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy: ', err)
    alert('复制失败，请手动复制')
  }
}

const getTaskStats = (task) => {
  if (!task.answers || task.answers.length === 0) {
    return { consistency: 0, topAnswer: '-', distribution: [] }
  }
  
  const counts = {}
  task.answers.forEach(a => {
    // Normalize string: trim spaces, make uppercase for single letter options (like 'A', 'B') to be safe, but keep original for display if it's longer
    const val = a.content.trim()
    const key = val.length === 1 ? val.toUpperCase() : val
    counts[key] = (counts[key] || 0) + 1
  })
  
  const total = task.answers.length
  const distribution = Object.entries(counts)
    .map(([ans, count]) => ({ answer: ans, count, percent: Math.round((count / total) * 100) }))
    .sort((a, b) => b.count - a.count)
    
  const topPercent = distribution[0].percent
    const topCandidates = distribution.filter(d => d.percent === topPercent)
    // Randomly select if tie
    const top = topCandidates[Math.floor(Math.random() * topCandidates.length)]
    
    return {
      consistency: top.percent,
      topAnswer: top.answer,
      distribution
    }
}

const fetchTasks = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const url = props.competitionId 
      ? `/api/tasks?competition_id=${props.competitionId}`
      : '/api/tasks'
      
    const res = await api.get(url, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    tasks.value = res.data
  } catch (error) {
    console.error(error)
    if (error.response?.status === 401) {
      alert('登录已过期，请重新登录')
      localStorage.removeItem('token')
      window.location.href = '/'
    }
  } finally {
    if (showLoading) loading.value = false
  }
}

const setupSSE = () => {
  if (eventSource) return;
  eventSource = new EventSource(`${API_BASE}/api/stream`)
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.action === 'refresh') {
      fetchTasks(false) // Fetch silently
    }
  }
}

onMounted(() => {
  fetchTasks()
  setupSSE()
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})

const inputs = ref({})
const fileInputs = ref({})
const editing = ref({ type: '', id: null, content: '' })

const handleFileChange = (taskId, e) => {
  if (e.target.files.length > 0) {
    fileInputs.value[taskId] = e.target.files[0]
  } else {
    fileInputs.value[taskId] = null
  }
}

const handleAdd = async (taskId, type) => {
  const content = inputs.value[`${taskId}_${type}`]
  const file = type === 'wp' ? fileInputs.value[taskId] : null
  
  if (!content && !file) return

  try {
    let res;
    if (type === 'wp' && file) {
      const formData = new FormData()
      formData.append('content', content || '')
      formData.append('file', file)
      res = await api.post(`/api/tasks/${taskId}/${type}`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${props.token}` 
        }
      })
    } else {
      res = await api.post(`/api/tasks/${taskId}/${type}`, { content }, {
        headers: { Authorization: `Bearer ${props.token}` }
      })
    }
    
    // Refresh locally without fetching whole table
    const task = tasks.value.find(t => t.id === taskId)
    if (type === 'answer') {
      if (res.data.is_new) {
        task.answers.push({ id: res.data.id, user: res.data.user, content })
      } else {
        const existing = task.answers.find(a => a.user === res.data.user)
        if (existing) existing.content = content
      }
    }
    if (type === 'wp') {
      task.wps.push({ 
        id: res.data.id, 
        user: res.data.user, 
        content,
        file_url: res.data.file_url,
        file_type: res.data.file_type,
        original_filename: res.data.original_filename
      })
      // Clear file input
      fileInputs.value[taskId] = null
      const fileInputEl = document.getElementById(`file_${taskId}`)
      if (fileInputEl) fileInputEl.value = ''
    }
    if (type === 'note') task.notes.push({ id: res.data.id, user: res.data.user, content })
    
    inputs.value[`${taskId}_${type}`] = ''
  } catch (error) {
    alert(error.response?.data?.error || '添加失败')
  }
}

const startEdit = (type, item) => {
  editing.value = { type, id: item.id, content: item.content }
}

const cancelEdit = () => {
  editing.value = { type: '', id: null, content: '' }
}

const saveEdit = async (taskId) => {
  const { type, id, content } = editing.value
  if (!content.trim()) return

  try {
    await api.put(`/api/items/${type}/${id}`, { content }, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    
    const task = tasks.value.find(t => t.id === taskId)
    let list = []
    if (type === 'answer') list = task.answers
    else if (type === 'wp') list = task.wps
    else if (type === 'note') list = task.notes
    
    const item = list.find(i => i.id === id)
    if (item) item.content = content
    
    cancelEdit()
  } catch (error) {
    alert(error.response?.data?.error || '修改失败')
  }
}

const handleDelete = async (taskId, type, id) => {
  if (!confirm('确定要删除这条内容吗？如果是WP，附带的文件也会被删除。')) return

  try {
    await api.delete(`/api/items/${type}/${id}`, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    
    const task = tasks.value.find(t => t.id === taskId)
    if (type === 'answer') {
      task.answers = task.answers.filter(a => a.id !== id)
    } else if (type === 'wp') {
      task.wps = task.wps.filter(w => w.id !== id)
    } else if (type === 'note') {
      task.notes = task.notes.filter(n => n.id !== id)
    }
  } catch (error) {
    alert(error.response?.data?.error || '删除失败')
  }
}

const editingTask = ref({ id: null, content: '', displayId: '' })

const startEditTask = (task) => {
  const displayId = task.id.includes('_') ? task.id.split('_').slice(1).join('_') : task.id
  editingTask.value = { id: task.id, content: task.content, displayId: displayId }
}

const cancelEditTask = () => {
  editingTask.value = { id: null, content: '', displayId: '' }
}

const saveEditTask = async () => {
  const { id, content, displayId } = editingTask.value
  if (!content.trim() || !displayId.trim()) return

  try {
    const res = await api.put(`/api/tasks/${id}`, { content, displayId }, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    
    const task = tasks.value.find(t => t.id === id)
    if (task) {
      task.content = content
      if (res.data.new_id) {
        task.id = res.data.new_id
      }
    }
    
    cancelEditTask()
  } catch (error) {
    alert(error.response?.data?.error || '修改题目失败')
  }
}

const deleteTask = async (taskId) => {
  if (!confirm('确定要删除这道题目吗？该题目下的所有解答和WP都将被永久删除！')) return

  try {
    await api.delete(`/api/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    
    tasks.value = tasks.value.filter(t => t.id !== taskId)
  } catch (error) {
    alert(error.response?.data?.error || '删除题目失败')
  }
}

const togglePin = async (taskId) => {
  try {
    await api.post(`/api/tasks/${taskId}/pin`, {}, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    // No need to manually update task array if setupSSE handles refresh,
    // but we can optionally do it for instant UI feedback
  } catch (error) {
    alert(error.response?.data?.error || '置顶操作失败')
  }
}

const toggleLike = async (taskId, type, id) => {
  try {
    const res = await api.post(`/api/items/${type}/${id}/like`, {}, {
      headers: { Authorization: `Bearer ${props.token}` }
    })
    // Update local state for instant feedback
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      const list = type === 'wp' ? task.wps : task.notes
      const item = list.find(i => i.id === id)
      if (item) {
        if (res.data.liked) {
          item.likes = (item.likes || 0) + 1
          item.liked_by_me = true
        } else {
          item.likes = Math.max(0, (item.likes || 1) - 1)
          item.liked_by_me = false
        }
      }
    }
  } catch (error) {
    console.error('点赞失败', error)
  }
}

const sortedAndFilteredTasks = computed(() => {
  let result = [...tasks.value]
  
  if (filterContent.value) {
    const keyword = filterContent.value.toLowerCase()
    result = result.filter(t => t.content.toLowerCase().includes(keyword))
  }
  
  result.sort((a, b) => {
    // Handle pinning logic first
    if (a.pinned_at || b.pinned_at) {
      if (a.pinned_at && !b.pinned_at) return -1
      if (!a.pinned_at && b.pinned_at) return 1
      if (a.pinned_at && b.pinned_at) {
        // Both pinned, sort by pinned_at desc (newest pinned first)
        const timeA = new Date(a.pinned_at).getTime()
        const timeB = new Date(b.pinned_at).getTime()
        return timeB - timeA
      }
    }

    if (sortKey.value === 'created_at') {
      const valA = new Date(a.created_at || 0).getTime()
      const valB = new Date(b.created_at || 0).getTime()
      if (valA < valB) return sortOrder.value === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder.value === 'asc' ? 1 : -1
      return 0
    } else if (sortKey.value === 'id') {
      // Strip prefix for sorting
      const idA = a.id.includes('_') ? a.id.split('_').slice(1).join('_') : String(a.id)
      const idB = b.id.includes('_') ? b.id.split('_').slice(1).join('_') : String(b.id)

      // UUID check: 36 chars long with 4 hyphens usually, or simply contains a hyphen and is long
      const isUuidA = typeof idA === 'string' && idA.length > 20 && idA.includes('-')
      const isUuidB = typeof idB === 'string' && idB.length > 20 && idB.includes('-')

      if (isUuidA && !isUuidB) return sortOrder.value === 'asc' ? 1 : -1
      if (!isUuidA && isUuidB) return sortOrder.value === 'asc' ? -1 : 1

      // If both are numbers (or numeric strings)
      if (!isUuidA && !isUuidB) {
        const numA = Number(idA)
        const numB = Number(idB)
        if (!isNaN(numA) && !isNaN(numB)) {
          return sortOrder.value === 'asc' ? numA - numB : numB - numA
        }
      }

      // Fallback to string comparison
      const strA = String(idA)
      const strB = String(idB)
      if (strA < strB) return sortOrder.value === 'asc' ? -1 : 1
      if (strA > strB) return sortOrder.value === 'asc' ? 1 : -1
      return 0
    } else if (sortKey.value === 'consistency') {
      const valA = getTaskStats(a).consistency
      const valB = getTaskStats(b).consistency
      if (valA < valB) return sortOrder.value === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder.value === 'asc' ? 1 : -1
      return 0
    }
    return 0
  })
  
  return result
})

const handleSort = (key) => {
  if (sortKey.value === key) {
    if (sortOrder.value === 'asc') {
      sortOrder.value = 'desc'
    } else {
      // 3rd click: Reset to default sorting (created_at desc)
      sortKey.value = 'created_at'
      sortOrder.value = 'desc'
    }
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

const exportToExcel = () => {
  if (sortedAndFilteredTasks.value.length === 0) {
    alert('表格为空，无法导出')
    return
  }

  // Map the tasks to a flat format for Excel
  const exportData = sortedAndFilteredTasks.value.map(task => {
    const stats = getTaskStats(task)
    
    // Combine answers into a single readable string
    const answersText = task.answers.map(a => `${a.user}: ${a.content}`).join('\n')
    
    // Combine WPs into a single readable string
    const wpsText = task.wps.map(w => {
      let text = `${w.user}: ${w.content || ''}`
      if (w.original_filename && w.file_url) {
        text += `\n  [附件: ${w.original_filename}]\n  [下载地址: ${resolveApiUrl(w.file_url)}]`
      } else if (w.file_url) {
        text += `\n  [附件下载地址: ${resolveApiUrl(w.file_url)}]`
      }
      return text
    }).join('\n\n')
    
    // Combine Notes into a single readable string
    const notesText = task.notes.map(n => `${n.user}: ${n.content}`).join('\n')

    // Handle ID prefix stripping for export
    const displayId = task.id.includes('_') ? task.id.split('_').slice(1).join('_') : task.id

    return {
      '题目ID': displayId,
      '提交时间': new Date(task.created_at).toLocaleString(),
      '题目内容': task.content,
      '答案记录': answersText,
      'Writeup记录': wpsText,
      '备注记录': notesText,
      '一致率': stats.consistency ? `${stats.consistency}%` : '-',
      '系统判定最终答案': stats.topAnswer || '-'
    }
  })

  // Create workbook and worksheet
  const worksheet = XLSX.utils.json_to_sheet(exportData)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '题目协作表')

  // Set column widths for better readability
  const colWidths = [
    { wch: 15 }, // 题目ID
    { wch: 20 }, // 提交时间
    { wch: 50 }, // 题目内容
    { wch: 40 }, // 答案记录
    { wch: 40 }, // Writeup记录
    { wch: 30 }, // 备注记录
    { wch: 10 }, // 一致率
    { wch: 20 }  // 最终答案
  ]
  worksheet['!cols'] = colWidths

  // Generate file name with current date
  const dateStr = new Date().toISOString().slice(0, 10)
  const fileName = `题目协作表导出_${dateStr}.xlsx`

  // Download
  XLSX.writeFile(workbook, fileName)
}

const downloadTemplate = () => {
  if (sortedAndFilteredTasks.value.length === 0) {
    alert('当前题目组为空，无法生成模板')
    return
  }

  const templateData = sortedAndFilteredTasks.value.map(task => {
    const displayId = task.id.includes('_') ? task.id.split('_').slice(1).join('_') : task.id
    return {
      '题目ID': displayId,
      '题目内容': task.content,
      '答案': '',
      'WP (Writeup)': '',
      '备注': ''
    }
  })

  const worksheet = XLSX.utils.json_to_sheet(templateData)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '提交模板')

  const colWidths = [
    { wch: 15 }, // 题目ID
    { wch: 50 }, // 题目内容
    { wch: 20 }, // 答案
    { wch: 30 }, // WP
    { wch: 30 }  // 备注
  ]
  worksheet['!cols'] = colWidths

  const dateStr = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(workbook, `题目提交模板_${dateStr}.xlsx`)
}

const batchUploadInput = ref(null)
const showWpColumn = ref(true)
const showNoteColumn = ref(true)

const triggerBatchUpload = () => {
  if (batchUploadInput.value) {
    batchUploadInput.value.click()
  }
}

const handleBatchUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  if (!confirm(`确认要根据上传的 Excel 批量更新您在当前题目的答案、WP和备注吗？\n注意：留空的列将被忽略，已有内容将被覆盖。`)) {
    event.target.value = ''
    return
  }

  const formData = new FormData()
  formData.append('file', file)
  if (props.competitionId) {
    formData.append('competition_id', props.competitionId)
  }

  try {
    const res = await api.post('/api/tasks/batch-update', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${props.token}`
      }
    })
    alert(res.data.message || '批量更新成功！')
    fetchTasks()
  } catch (error) {
    alert(error.response?.data?.error || '批量更新失败，请检查文件格式。')
  } finally {
    event.target.value = ''
  }
}

</script>

<template>
  <div class="task-board-container">
    <div class="board-header">
      <h2 class="board-title">答题协作大表</h2>
      <div class="header-actions" v-if="!loading && tasks.length > 0">
        <button @click="downloadTemplate" class="btn-action btn-template">
          下载提交模板
        </button>
        <button @click="triggerBatchUpload" class="btn-action btn-upload">
          批量上传更新
        </button>
        <input type="file" accept=".xlsx, .xls, .csv" ref="batchUploadInput" @change="handleBatchUpload" style="display: none;" />
        <button @click="exportToExcel" class="btn-action btn-export">
          导出数据矩阵
        </button>
      </div>
    </div>
    
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载数据中...</p>
    </div>
    <div v-else-if="tasks.length === 0" class="empty-state">
      <div class="empty-icon">NO DATA</div>
      <p>暂无题目，请先上传 Excel 导入题目。</p>
    </div>
    <div class="table-wrapper" v-else>
      <table class="cyber-table">
        <thead>
          <tr>
            <th style="width: 8%">
              <div class="th-content">
                <span class="th-title">题目ID</span>
                <span @click="handleSort('id')" class="sort-badge">
                  ID排序 <span v-if="sortKey === 'id'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </span>
              </div>
            </th>
            <th style="width: 20%">
              <span class="th-title">题目内容</span>
              <input type="text" v-model="filterContent" placeholder="输入关键字筛选..." class="filter-input" />
            </th>
            <th style="width: 20%">
              <div class="th-content">
                <span class="th-title">答案</span>
                <span @click="handleSort('consistency')" class="sort-badge">
                  一致率排序 <span v-if="sortKey === 'consistency'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </span>
              </div>
            </th>
            <th :style="{ width: showWpColumn ? '20%' : '8%', transition: 'width 0.3s' }">
              <div class="th-content" style="justify-content: center; gap: 8px;">
                <span class="th-title" v-show="showWpColumn">WP (Writeup)</span>
                <span @click="showWpColumn = !showWpColumn" class="sort-badge" style="padding: 2px 6px; font-size: 1.1em;" :title="showWpColumn ? '隐藏WP列' : '显示WP列'">
                  {{ showWpColumn ? '收起' : '展开' }}
                </span>
              </div>
            </th>
            <th :style="{ width: showNoteColumn ? '15%' : '8%', transition: 'width 0.3s' }">
              <div class="th-content" style="justify-content: center; gap: 8px;">
                <span class="th-title" v-show="showNoteColumn">备注</span>
                <span @click="showNoteColumn = !showNoteColumn" class="sort-badge" style="padding: 2px 6px; font-size: 1.1em;" :title="showNoteColumn ? '隐藏备注列' : '显示备注列'">
                  {{ showNoteColumn ? '收起' : '展开' }}
                </span>
              </div>
            </th>
            <th style="width: 17%"><span class="th-title">最终答案</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in sortedAndFilteredTasks" :key="task.id" class="item-row" :class="{ 'pinned-row': task.pinned_at }">
            <td>
              <div style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap; word-break: break-all;">
                <span v-if="task.pinned_at" title="已置顶" class="pin-mark">PIN</span>
                <span>{{ task.id.includes('_') ? task.id.split('_').slice(1).join('_') : task.id }}</span>
                <button v-if="props.username === 'admin'" @click="togglePin(task.id)" class="pin-btn" :title="task.pinned_at ? '取消置顶' : '置顶此题'" style="margin-left: 4px;">
                  {{ task.pinned_at ? '取消置顶' : '置顶' }}
                </button>
              </div>
              <div style="font-size: 0.8em; color: var(--text-muted); margin-top: 4px;">{{ new Date(task.created_at).toLocaleString() }}</div>
            </td>
            <td style="word-wrap: break-word; position: relative;">
              <div v-if="editingTask.id === task.id" style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; flex-direction: column; gap: 4px;">
                  <label style="font-size: 0.85em; color: var(--accent-cyan); font-weight: bold;">题目ID:</label>
                  <input type="text" v-model="editingTask.displayId" style="width: 100%; box-sizing: border-box; padding: 6px; border: 1px solid var(--accent-cyan); border-radius: 4px; background: var(--bg-main); color: var(--text-main); font-family: var(--font-mono);" />
                </div>
                <div style="display: flex; flex-direction: column; gap: 4px;">
                  <label style="font-size: 0.85em; color: var(--accent-cyan); font-weight: bold;">题目内容:</label>
                  <textarea v-model="editingTask.content" style="width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid var(--accent-cyan); border-radius: 6px; background: var(--bg-main); color: var(--text-main); font-family: var(--font-sans);" rows="3"></textarea>
                </div>
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                  <button @click="cancelEditTask" style="background: transparent; color: var(--text-muted); padding: 4px 12px; font-size: 0.85em; border: 1px solid var(--border-subtle); box-shadow: none;">取消</button>
                  <button @click="saveEditTask" style="background: rgba(0, 229, 255, 0.1); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); padding: 4px 12px; font-size: 0.85em; box-shadow: none;">保存</button>
                </div>
              </div>
              <div v-else>
                {{ task.content }}
                <div v-if="props.username === 'admin'" style="margin-top: 12px; display: flex; gap: 8px; justify-content: flex-end;">
                  <button @click="startEditTask(task)" style="background: none; border: none; color: var(--accent-cyan); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">编辑题目</button>
                  <button @click="deleteTask(task.id)" style="background: none; border: none; color: var(--accent-danger); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">删除整题</button>
                </div>
              </div>
            </td>
            
            <!-- Answers Column -->
            <td style="max-width: 300px; word-wrap: break-word;">
              <!-- Statistics Panel -->
              <div v-if="task.answers && task.answers.length > 0" style="margin-bottom: 12px; padding: 12px; background-color: var(--stats-panel-bg); border-radius: 6px; border: 1px solid var(--stats-panel-border);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px dashed var(--border-subtle); padding-bottom: 6px;">
                  <span style="font-weight: bold; color: var(--text-main); font-family: var(--font-mono); font-size: 0.85em; letter-spacing: 1px;">数据统计</span>
                  <span :style="{ color: getTaskStats(task).consistency >= 80 ? 'var(--accent-green)' : (getTaskStats(task).consistency >= 50 ? 'var(--accent-purple)' : 'var(--accent-danger)'), fontWeight: 'bold', fontSize: '0.9em', fontFamily: 'var(--font-mono)' }">
                    一致率: {{ getTaskStats(task).consistency }}%
                  </span>
                </div>
                <div style="font-size: 0.85em; color: var(--stats-panel-text); display: flex; flex-direction: column; gap: 6px;">
                  <div v-for="(stat, idx) in getTaskStats(task).distribution" :key="idx" style="display: flex; justify-content: space-between; font-family: var(--font-mono);">
                    <span class="text-neon-cyan" style="font-weight: bold; max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="stat.answer">{{ stat.answer }}</span>
                    <span>{{ stat.count }}人 ({{ stat.percent }}%)</span>
                  </div>
                </div>
              </div>

              <div v-for="item in task.answers" :key="item.id" style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed var(--border-subtle);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                  <span style="font-weight: bold; color: var(--accent-cyan);">{{ item.user }}: </span>
                  <div v-if="(item.user === props.username || props.username === 'admin') && editing.id !== item.id" style="display: flex; gap: 4px;">
                    <button @click="startEdit('answer', item)" style="background: none; border: none; color: var(--text-muted); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">修改</button>
                    <button @click="handleDelete(task.id, 'answer', item.id)" style="background: none; border: none; color: var(--accent-danger); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">删除</button>
                  </div>
                </div>
                
                <div v-if="editing.type === 'answer' && editing.id === item.id" style="margin-top: 8px; display: flex; flex-direction: column; gap: 8px;">
                  <textarea v-model="editing.content" style="width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid var(--accent-cyan); border-radius: 6px; background: var(--bg-main); color: var(--text-main); font-family: var(--font-sans);" rows="2"></textarea>
                  <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button @click="cancelEdit" style="background: transparent; color: var(--text-muted); padding: 4px 12px; font-size: 0.85em; border: 1px solid var(--border-subtle); box-shadow: none;">取消</button>
                    <button @click="saveEdit(task.id)" style="background: rgba(0, 229, 255, 0.1); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); padding: 4px 12px; font-size: 0.85em; box-shadow: none;">保存</button>
                  </div>
                </div>
                <span v-else style="white-space: pre-wrap; display: block; margin-top: 4px;">{{ item.content }}</span>
              </div>
              <div v-if="!task.answers.some(a => a.user === props.username)" style="display: flex; gap: 4px; margin-top: 8px;">
                <input type="text" v-model="inputs[`${task.id}_answer`]" :placeholder="`${props.username}: 输入答案...`" style="flex: 1; padding: 4px; font-size: 0.9em; background: var(--bg-main); color: var(--text-main); border: 1px solid var(--border-subtle); min-width: 0;" @keyup.enter="handleAdd(task.id, 'answer')" />
                <button @click="handleAdd(task.id, 'answer')" style="padding: 4px 8px; font-size: 0.9em; background: rgba(0, 229, 255, 0.1); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); flex-shrink: 0;">+</button>
              </div>
            </td>
            
            <!-- WP Column -->
            <td :style="{ maxWidth: '300px', wordWrap: 'break-word', padding: showWpColumn ? '16px' : '16px 8px' }">
              <div v-show="showWpColumn">
                <div v-for="item in task.wps" :key="item.id" style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed var(--border-subtle);">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                    <span style="font-weight: bold; color: var(--accent-green); word-break: break-all;">{{ item.user }}: </span>
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end;">
                      <button @click="toggleLike(task.id, 'wp', item.id)" class="like-btn" :class="{ 'liked': item.liked_by_me }">
                        赞 {{ item.likes || 0 }}
                      </button>
                      <div v-if="(item.user === props.username || props.username === 'admin') && editing.id !== item.id" style="display: flex; gap: 4px; flex-shrink: 0;">
                        <button @click="startEdit('wp', item)" style="background: none; border: none; color: var(--text-muted); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">修改</button>
                        <button @click="handleDelete(task.id, 'wp', item.id)" style="background: none; border: none; color: var(--accent-danger); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">删除</button>
                      </div>
                    </div>
                  </div>
                  
                  <div v-if="editing.type === 'wp' && editing.id === item.id" style="margin-top: 8px; display: flex; flex-direction: column; gap: 8px;">
                    <textarea v-model="editing.content" style="width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid var(--accent-green); border-radius: 6px; background: var(--bg-main); color: var(--text-main); font-family: var(--font-sans);" rows="3"></textarea>
                    <div style="display: flex; gap: 8px; justify-content: flex-end;">
                      <button @click="cancelEdit" style="background: transparent; color: var(--text-muted); padding: 4px 12px; font-size: 0.85em; border: 1px solid var(--border-subtle); box-shadow: none;">取消</button>
                      <button @click="saveEdit(task.id)" style="background: rgba(0, 230, 118, 0.1); color: var(--accent-green); border: 1px solid var(--accent-green); padding: 4px 12px; font-size: 0.85em; box-shadow: none;">保存</button>
                    </div>
                  </div>
                  <span v-else style="white-space: pre-wrap; display: block; margin-top: 4px;">{{ item.content }}</span>
                  
                  <div v-if="item.file_url" style="margin-top: 8px;">
                    <div v-if="item.original_filename" style="font-size: 0.85em; color: var(--text-muted); margin-bottom: 4px;">文件：{{ item.original_filename }}</div>
                    <img v-if="item.file_type === 'image'" :src="resolveApiUrl(item.file_url)" style="max-width: 100%; border: 1px solid var(--border-subtle); border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
                    <a :href="resolveApiUrl(item.file_url)" target="_blank" download class="download-link">下载附件</a>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 8px;">
                  <input type="text" v-model="inputs[`${task.id}_wp`]" :placeholder="`${props.username}: 输入WP...`" style="padding: 4px; font-size: 0.9em; background: var(--bg-main); color: var(--text-main); border: 1px solid var(--border-subtle); min-width: 0;" @keyup.enter="handleAdd(task.id, 'wp')" />
                  <div style="display: flex; gap: 4px; align-items: center; max-width: 100%; overflow: hidden;">
                    <input type="file" :id="`file_${task.id}`" @change="(e) => handleFileChange(task.id, e)" style="flex: 1; font-size: 0.8em; min-width: 0; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" />
                    <button @click="handleAdd(task.id, 'wp')" style="padding: 4px 8px; font-size: 0.9em; background: rgba(0, 230, 118, 0.1); color: var(--accent-green); border: 1px solid var(--accent-green); flex-shrink: 0;">+</button>
                  </div>
                </div>
              </div>
              <div v-show="!showWpColumn" style="color: var(--text-muted); text-align: center; opacity: 0.5; font-size: 1.5em; cursor: pointer;" @click="showWpColumn = true" title="点击展开">
                已收起
              </div>
            </td>

            <!-- Notes Column -->
            <td :style="{ maxWidth: '300px', wordWrap: 'break-word', padding: showNoteColumn ? '16px' : '16px 8px' }">
              <div v-show="showNoteColumn">
                <div v-for="item in task.notes" :key="item.id" style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed var(--border-subtle);">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                    <span style="font-weight: bold; color: var(--accent-purple); word-break: break-all;">{{ item.user }}: </span>
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end;">
                      <button @click="toggleLike(task.id, 'note', item.id)" class="like-btn" :class="{ 'liked-note': item.liked_by_me }">
                        赞 {{ item.likes || 0 }}
                      </button>
                      <div v-if="(item.user === props.username || props.username === 'admin') && editing.id !== item.id" style="display: flex; gap: 4px; flex-shrink: 0;">
                        <button @click="startEdit('note', item)" style="background: none; border: none; color: var(--text-muted); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">修改</button>
                        <button @click="handleDelete(task.id, 'note', item.id)" style="background: none; border: none; color: var(--accent-danger); padding: 0; font-size: 0.8em; text-decoration: underline; cursor: pointer; box-shadow: none;">删除</button>
                      </div>
                    </div>
                  </div>

                  <div v-if="editing.type === 'note' && editing.id === item.id" style="margin-top: 8px; display: flex; flex-direction: column; gap: 8px;">
                    <textarea v-model="editing.content" style="width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid var(--accent-purple); border-radius: 6px; background: var(--bg-main); color: var(--text-main); font-family: var(--font-sans);" rows="2"></textarea>
                    <div style="display: flex; gap: 8px; justify-content: flex-end;">
                      <button @click="cancelEdit" style="background: transparent; color: var(--text-muted); padding: 4px 12px; font-size: 0.85em; border: 1px solid var(--border-subtle); box-shadow: none;">取消</button>
                      <button @click="saveEdit(task.id)" style="background: rgba(179, 136, 255, 0.1); color: var(--accent-purple); border: 1px solid var(--accent-purple); padding: 4px 12px; font-size: 0.85em; box-shadow: none;">保存</button>
                    </div>
                  </div>
                  <span v-else style="white-space: pre-wrap; display: block; margin-top: 4px;">{{ item.content }}</span>
                </div>
                <div style="display: flex; gap: 4px; margin-top: 8px;">
                  <input type="text" v-model="inputs[`${task.id}_note`]" :placeholder="`${props.username}: 输入备注...`" style="flex: 1; padding: 4px; font-size: 0.9em; background: var(--bg-main); color: var(--text-main); border: 1px solid var(--border-subtle); min-width: 0;" @keyup.enter="handleAdd(task.id, 'note')" />
                  <button @click="handleAdd(task.id, 'note')" style="padding: 4px 8px; font-size: 0.9em; background: rgba(179, 136, 255, 0.1); color: var(--accent-purple); border: 1px solid var(--accent-purple); flex-shrink: 0;">+</button>
                </div>
              </div>
              <div v-show="!showNoteColumn" style="color: var(--text-muted); text-align: center; opacity: 0.5; font-size: 1.5em; cursor: pointer;" @click="showNoteColumn = true" title="点击展开">
                已收起
              </div>
            </td>

            <!-- Final Answer Column -->
            <td>
              <div v-if="task.answers && task.answers.length > 0" 
                   :style="{
                     background: getTaskStats(task).consistency >= 80 ? 'rgba(0, 230, 118, 0.05)' : (getTaskStats(task).consistency >= 50 ? 'rgba(179, 136, 255, 0.05)' : 'rgba(255, 82, 82, 0.05)'),
                     border: `1px solid ${getTaskStats(task).consistency >= 80 ? 'rgba(0, 230, 118, 0.3)' : (getTaskStats(task).consistency >= 50 ? 'rgba(179, 136, 255, 0.3)' : 'rgba(255, 82, 82, 0.3)')}`,
                     borderRadius: '8px', 
                     padding: '1rem', 
                     textAlign: 'center', 
                     height: '100%', 
                     boxSizing: 'border-box', 
                     display: 'flex', 
                     flexDirection: 'column', 
                     justifyContent: 'center', 
                     position: 'relative',
                     transition: 'all 0.3s ease'
                   }">
                <button 
                  @click="copyToClipboard(getTaskStats(task).topAnswer, task.id)" 
                  :style="{
                    position: 'absolute', 
                    top: '8px', 
                    right: '8px', 
                    background: getTaskStats(task).consistency >= 80 ? 'rgba(0, 230, 118, 0.1)' : (getTaskStats(task).consistency >= 50 ? 'rgba(179, 136, 255, 0.1)' : 'rgba(255, 82, 82, 0.1)'), 
                    border: `1px solid ${getTaskStats(task).consistency >= 80 ? 'var(--accent-green)' : (getTaskStats(task).consistency >= 50 ? 'var(--accent-purple)' : 'var(--accent-danger)')}`, 
                    cursor: 'pointer', 
                    padding: '4px 8px', 
                    borderRadius: '4px', 
                    transition: 'all 0.2s', 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '4px'
                  }"
                  :title="copyStatus[task.id] ? '已复制！' : '复制答案'"
                  :onmouseover="`this.style.boxShadow='0 0 10px ${getTaskStats(task).consistency >= 80 ? 'var(--accent-green)' : (getTaskStats(task).consistency >= 50 ? 'var(--accent-purple)' : 'var(--accent-danger)')}'`"
                  onmouseout="this.style.boxShadow='none'"
                >
                  <span v-if="copyStatus[task.id]" :style="{ color: getTaskStats(task).consistency >= 80 ? 'var(--accent-green)' : (getTaskStats(task).consistency >= 50 ? 'var(--accent-purple)' : 'var(--accent-danger)'), fontSize: '1.1em', display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'var(--font-mono)' }">✓ <span style="font-size: 0.85em;">已复制</span></span>
                  <span v-else :style="{ color: getTaskStats(task).consistency >= 80 ? 'var(--accent-green)' : (getTaskStats(task).consistency >= 50 ? 'var(--accent-purple)' : 'var(--accent-danger)'), fontSize: '1.1em', display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'var(--font-mono)' }">复制</span>
                </button>
                <div style="font-size: 0.85em; color: var(--final-answer-text); margin-bottom: 0.8rem; font-weight: bold; padding-right: 60px; font-family: var(--font-mono); letter-spacing: 1px;">最终结果</div>
                <div :style="{
                  fontSize: '1.8em', 
                  fontWeight: '900', 
                  wordBreak: 'break-all', 
                  fontFamily: 'var(--font-mono)', 
                  color: getTaskStats(task).consistency >= 80 ? 'var(--accent-green)' : (getTaskStats(task).consistency >= 50 ? 'var(--accent-purple)' : 'var(--accent-danger)'),
                  textShadow: getTaskStats(task).consistency >= 80 ? '0 0 15px rgba(0, 230, 118, 0.2)' : (getTaskStats(task).consistency >= 50 ? '0 0 15px rgba(179, 136, 255, 0.2)' : '0 0 15px rgba(255, 82, 82, 0.2)')
                }">
                  {{ getTaskStats(task).topAnswer }}
                </div>
                <div style="font-size: 0.8em; color: var(--stats-panel-text); margin-top: 0.8rem; font-family: var(--font-mono); opacity: 0.8;">
                  (一致率: {{ getTaskStats(task).consistency }}%)
                </div>
              </div>
              <div v-else style="color: var(--text-muted); text-align: center; margin-top: 1rem; font-size: 0.9em; font-family: var(--font-mono);">
                暂无答案数据
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.task-board-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.board-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
  padding: 1rem 1.1rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.16);
}

.board-title {
  margin: 0;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
  font-size: 1.45rem;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.btn-action {
  font-family: var(--font-mono);
  padding: 8px 16px;
  font-size: 0.9em;
  border-radius: 6px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: none;
}

.btn-template {
  background: rgba(241, 189, 97, 0.1);
  color: var(--accent-amber);
  border: 1px solid var(--accent-amber);
}

.btn-template:hover {
  background: rgba(241, 189, 97, 0.18);
  box-shadow: 0 4px 15px rgba(241, 189, 97, 0.2);
  transform: translateY(-2px);
}

.btn-upload {
  background: rgba(123, 216, 137, 0.1);
  color: var(--accent-green);
  border: 1px solid var(--accent-green);
}

.btn-upload:hover {
  background: rgba(123, 216, 137, 0.18);
  box-shadow: 0 4px 15px rgba(123, 216, 137, 0.24);
  transform: translateY(-2px);
}

.btn-export {
  background: rgba(74, 200, 206, 0.1);
  color: var(--accent-cyan);
  border: 1px solid var(--accent-cyan);
}

.btn-export:hover {
  background: rgba(74, 200, 206, 0.18);
  box-shadow: 0 4px 15px var(--accent-cyan-glow);
  transform: translateY(-2px);
}

.table-wrapper {
  overflow-x: auto;
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  box-shadow: 0 16px 44px rgba(0,0,0,0.18);
}

.cyber-table {
  width: 100%;
  min-width: 1200px;
  table-layout: fixed;
  border-collapse: collapse;
}

.cyber-table th, .cyber-table td {
  border: 1px solid var(--border-subtle);
  padding: 16px;
}

.pinned-row {
  background-color: rgba(241, 189, 97, 0.05) !important;
}

.pin-mark {
  display: inline-flex;
  align-items: center;
  height: 20px;
  border: 1px solid rgba(241, 189, 97, 0.45);
  border-radius: 4px;
  padding: 0 5px;
  color: var(--accent-amber);
  background: rgba(241, 189, 97, 0.1);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 900;
}

.pin-btn {
  background: rgba(241, 189, 97, 0.1);
  border: 1px solid var(--accent-amber);
  color: var(--accent-amber);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.75em;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: none;
}

.pin-btn:hover {
  background: rgba(241, 189, 97, 0.18);
  box-shadow: 0 0 5px rgba(241, 189, 97, 0.24);
}

.cyber-table th {
  background: var(--table-th-bg);
  position: relative;
}

.th-title {
  color: var(--text-main);
  text-shadow: none;
}

.th-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sort-badge {
  cursor: pointer;
  font-size: 0.85em;
  color: var(--accent-cyan);
  background: rgba(74, 200, 206, 0.1);
  border: 1px solid var(--accent-cyan);
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.sort-badge:hover {
  background: rgba(74, 200, 206, 0.18);
  box-shadow: 0 0 8px var(--accent-cyan-glow);
}

.filter-input {
  width: 100%;
  box-sizing: border-box;
  margin-top: 8px;
  padding: 6px 8px;
  font-weight: normal;
  background: var(--bg-main);
  color: var(--text-main);
  border: 1px dashed var(--border-subtle);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.9em;
}

.filter-input:focus {
  border-color: var(--accent-cyan);
}

.loading-state, .empty-state {
  text-align: center;
  padding: 4rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
  background: var(--bg-card);
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 229, 255, 0.1);
  border-top-color: var(--accent-cyan);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: var(--accent-amber);
  font-weight: 900;
  letter-spacing: 0.16em;
}

.like-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.75em;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.like-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.like-btn.liked {
  background: rgba(123, 216, 137, 0.15);
  border-color: var(--accent-green);
  color: var(--accent-green);
  box-shadow: 0 0 8px rgba(123, 216, 137, 0.24);
}

.like-btn.liked-note {
  background: rgba(241, 189, 97, 0.15);
  border-color: var(--accent-amber);
  color: var(--accent-amber);
  box-shadow: 0 0 8px rgba(241, 189, 97, 0.24);
}

.download-link {
  margin-top: 6px;
  padding: 4px 8px;
  font-size: 0.86em;
}

@media (max-width: 920px) {
  .board-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
