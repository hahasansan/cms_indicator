<template>
  <div class="page data-list-page">
    <div class="page-head">
      <div><h1>指标数据查询</h1><div class="desc">从指标树选择多个指标，系统自动识别共有维度并统一查询。</div></div>
      <div class="actions">
        <span class="muted">{{ visibleIndicators.length }} 个可用指标 · 已选 {{ selectedIds.length }} 个</span>
        <el-button @click="goBack">返回</el-button>
      </div>
    </div>

    <div class="iq-layout data-list-main">
      <el-card shadow="never" class="iq-tree-card">
        <template #header><div class="iq-head-bar"><strong>指标树</strong><el-tag type="info" size="small">{{ selectedIds.length }} 已选</el-tag></div></template>
        <div class="iq-tree-search">
          <el-input v-model="keyword" placeholder="搜索指标名称或编码" clearable @keyup.enter="searchTree" />
          <el-button @click="searchTree">搜索</el-button>
        </div>
        <div class="iq-tree-actions">
          <el-button link type="primary" @click="selectVisible">全选当前</el-button>
          <el-button link @click="clearSelection">取消全选</el-button>
        </div>
        <div class="iq-tree-scroll">
          <IndicatorTreeNode v-for="node in filteredTree" :key="node.id" :node="node" :selected-ids="selectedIds" @select="onSelect" />
          <div v-if="!filteredTree.length" class="iq-tree-empty">暂无匹配指标</div>
        </div>
        <div class="iq-selection-footer">已选择 <b>{{ selectedIds.length }}</b> 个指标</div>
      </el-card>

      <div class="iq-main-panel">
        <el-card shadow="never">
          <template #header><div class="iq-head-bar"><strong>查询条件</strong><span class="muted">共有维度会根据已选指标自动计算</span></div></template>
          <div class="iq-shared">
            <div class="iq-shared-label">共有维度</div>
            <div v-if="selectedIds.length && commonFields.length" class="iq-shared-list">
              <el-tag v-for="field in commonFields" :key="`${field.kind}-${field.name}`" size="small">{{ field.alias }}</el-tag>
            </div>
            <div v-else class="iq-shared-placeholder">选择两个或多个指标后，系统将在这里显示可共同查询的字段</div>
          </div>
          <div class="iq-condition-row">
            <label class="iq-condition-field">
              <span>统计期间起</span>
              <el-input v-model="startDate" type="date" />
            </label>
            <label class="iq-condition-field">
              <span>统计期间止</span>
              <el-input v-model="endDate" type="date" />
            </label>
            <label v-for="field in commonFilterFields" :key="field.name" class="iq-condition-field">
              <span>{{ field.alias }}</span>
              <el-input v-model="dimensionFilters[field.name]" :placeholder="`请输入${field.alias}`" />
            </label>
            <div class="iq-selected-summary">
              <span>当前指标</span>
              <div class="iq-selected-chips">
                <el-tag v-for="indicator in selectedIndicators" :key="indicator.id" closable @close="onSelect(indicator.id, false)">{{ indicator.name }}</el-tag>
                <span v-if="!selectedIndicators.length" class="muted">请从左侧选择</span>
              </div>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="iq-result-card">
          <template #header>
            <div class="iq-head-bar">
              <strong>数据展示</strong>
              <span class="muted">{{ tableRows.length ? `返回 ${tableRows.length} 行` : '未执行查询' }}</span>
              <div class="iq-result-actions">
                <el-button type="primary" :disabled="!selectedIds.length || loading" @click="queryResults">查询</el-button>
                <el-button :disabled="loading" @click="resetQuery">重置</el-button>
                <el-button :disabled="!tableRows.length" @click="exportCsv">导出 Excel</el-button>
                <el-button :disabled="!selectedIds.length" @click="addToFavorites">加入收藏</el-button>
                <el-button :disabled="!tableRows.length" @click="windowQuery = true">窗口查询</el-button>
              </div>
            </div>
          </template>
          <div v-if="loading" class="iq-result-empty"><span class="iq-loading-mark">…</span><b>正在查询指标数据</b></div>
          <div v-else-if="!tableRows.length" class="iq-result-empty"><b>{{ selectedIds.length ? '暂无查询结果' : '请先选择指标' }}</b><span>{{ selectedIds.length ? '调整日期或查询条件后重试' : '从左侧指标树勾选一个或多个指标' }}</span></div>
          <el-table v-else :data="tableRows" size="small">
            <el-table-column label="统计期间" width="190"><template #default="{ row }">{{ periodLabel(row) }}</template></el-table-column>
            <el-table-column label="指标名称" min-width="180"><template #default="{ row }"><b>{{ row.indicatorName }}</b><small class="muted">{{ row.indicatorCode }}</small></template></el-table-column>
            <el-table-column v-for="column in dimensionColumns" :key="column" :label="column" min-width="130"><template #default="{ row }">{{ formatValue(row.dimensions[column]) }}</template></el-table-column>
            <el-table-column v-for="column in resultColumns" :key="column" :label="column" min-width="130" align="right"><template #default="{ row }">{{ formatValue(row.values[column]) }}</template></el-table-column>
          </el-table>
          <div v-if="tableRows.length" class="iq-pagination">
            <span class="muted">第 {{ page }} 页</span>
            <el-button size="small" :disabled="loading || page <= 1" @click="changePage(page - 1)">上一页</el-button>
            <el-button size="small" :disabled="loading || !hasMore" @click="changePage(page + 1)">下一页</el-button>
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="windowQuery" title="指标查询结果" width="960px" append-to-body>
      <div class="muted">已选 {{ selectedIds.length }} 个指标 · {{ tableRows.length }} 行结果</div>
      <el-table :data="tableRows" size="small" max-height="420">
        <el-table-column label="统计期间" width="190"><template #default="{ row }">{{ periodLabel(row) }}</template></el-table-column>
        <el-table-column label="指标名称" min-width="180"><template #default="{ row }"><b>{{ row.indicatorName }}</b></template></el-table-column>
        <el-table-column v-for="column in dimensionColumns" :key="column" :label="column" min-width="130"><template #default="{ row }">{{ formatValue(row.dimensions[column]) }}</template></el-table-column>
        <el-table-column v-for="column in resultColumns" :key="column" :label="column" min-width="130" align="right"><template #default="{ row }">{{ formatValue(row.values[column]) }}</template></el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { api as apiClient, jsonBody } from '../../api'
import IndicatorTreeNode from '../../components/IndicatorTreeNode.vue'
import type { BootstrapData, Indicator as IndicatorT, IndicatorOption as IndicatorOptionT, IndicatorTreeNode as TreeNode } from '../../types'

type ResultRow = Record<string, any> & { id: string; indicator_id: string; indicator_name: string; indicator_code: string; data_date: string; result_kind: 'detail' | 'summary'; period_type: 'point' | 'period'; period_start: string; period_end: string; metric_name: string; metric_value: number | null; dimensions: Record<string, unknown>; created_at?: string }
type QueryField = { name: string; alias: string; kind: 'dimension' | 'measure' }
type TableRow = { key: string; dataDate: string; resultKind: 'detail' | 'summary'; periodType: 'point' | 'period'; periodStart: string; periodEnd: string; dimensions: Record<string, unknown>; indicatorName: string; indicatorCode: string; values: Record<string, unknown> }

const props = defineProps<{ data: BootstrapData; indicatorId?: string }>()
const notify = inject<(message: string) => void>('notify', () => undefined)
const keyword = ref('')
const startDate = ref('')
const endDate = ref('')
const page = ref(1)
const pageSize = 100
const hasMore = ref(false)
const dimensionFilters = ref<Record<string, string>>({})
const selectedIds = ref<string[]>(props.indicatorId ? [props.indicatorId] : [])
const rows = ref<ResultRow[]>([])
const loading = ref(false)
const windowQuery = ref(false)
const indicatorDetails = ref<Record<string, IndicatorT>>({})

const visibleIndicators = computed(() => props.data.indicators)
const tree = computed(() => buildTree(visibleIndicators.value))
const filteredTree = computed(() => keyword.value.trim() ? filterTree(tree.value, keyword.value.trim().toLowerCase()) : tree.value)
const selectedIndicators = computed(() => selectedIds.value.map((id) => indicatorDetails.value[id]).filter((item): item is IndicatorT => Boolean(item)))

const commonFields = computed<QueryField[]>(() => {
  if (!selectedIndicators.value.length) return []
  const first = fieldList(selectedIndicators.value[0])
  return first.filter((field) => selectedIndicators.value.every((indicator) => fieldList(indicator).some((candidate) => candidate.name === field.name && candidate.kind === field.kind)))
})
const commonFilterFields = computed(() => commonFields.value.filter((field) => field.kind === 'dimension' && field.name !== 'DATA_DATE'))
const dimensionColumns = computed(() => {
  const commonDimensions = commonFields.value.filter((field) => field.kind === 'dimension' && field.name !== 'DATA_DATE').map((field) => field.alias)
  const rowDimensions = rows.value.flatMap((row) => Object.keys(row.dimensions || {}))
  return Array.from(new Set([...commonDimensions, ...rowDimensions]))
})
const resultColumns = computed(() => {
  const aliases = Array.from(new Set(rows.value.map((row) => row.metric_name).filter(Boolean)))
  const commonMeasures = commonFields.value.filter((field) => field.kind === 'measure').map((field) => field.alias)
  return commonMeasures.length ? Array.from(new Set([...commonMeasures, ...aliases])) : aliases
})
const tableRows = computed<TableRow[]>(() => {
  const grouped = new Map<string, TableRow>()
  for (const row of rows.value) {
    const dimensions = row.dimensions || {}
    const key = `${row.result_kind}|${row.period_type}|${row.period_start}|${row.period_end}|${row.indicator_code}|${JSON.stringify(dimensions)}`
    const current = grouped.get(key) || { key, dataDate: row.data_date, resultKind: row.result_kind, periodType: row.period_type, periodStart: row.period_start, periodEnd: row.period_end, dimensions, indicatorName: row.indicator_name, indicatorCode: row.indicator_code, values: {} }
    current.values[row.metric_name] = row.metric_value
    grouped.set(key, current)
  }
  return [...grouped.values()]
})

watch(() => props.indicatorId, (id) => { if (id && !selectedIds.value.includes(id)) selectedIds.value.push(id) })
watch(() => props.data.indicators, () => { selectedIds.value = selectedIds.value.filter((id) => props.data.indicators.some((item) => item.id === id)) })
watch(selectedIds, loadIndicatorDetails, { immediate: true })

function fieldList(indicator: IndicatorT): QueryField[] {
  const dimensions = (indicator.config.dimensions || []).map((field) => {
    const alias = field.alias || field.fieldName
    return { name: alias, alias, kind: 'dimension' as const }
  })
  const measures = (indicator.config.measures || (indicator.config.measure ? [indicator.config.measure] : [])).map((field) => {
    const alias = field.alias || field.fieldName
    return { name: alias, alias, kind: 'measure' as const }
  })
  return [...dimensions, ...measures]
}

function buildTree(indicators: IndicatorOptionT[]): TreeNode[] {
  const categoryNodes = new Map(props.data.indicatorCategories.filter((category) => category.enabled && category.id !== 'root').map((category) => [category.id, { id: `category-${category.id}`, label: category.name, kind: 'folder' as const, children: [] as TreeNode[] }]))
  const indicatorNodes = new Map(indicators.map((indicator) => [indicator.id, { id: `indicator-${indicator.id}`, label: indicator.name, code: indicator.code, categoryName: props.data.indicatorCategories.find((category) => category.id === indicator.categoryId)?.name, kind: 'indicator' as const, indicatorId: indicator.id, children: [] as TreeNode[] }]))
  const roots: TreeNode[] = []
  for (const category of props.data.indicatorCategories.filter((item) => item.enabled && item.id !== 'root')) {
    const node = categoryNodes.get(category.id)!
    const parent = category.parentId ? categoryNodes.get(category.parentId) : undefined
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  for (const indicator of indicators) {
    const node = indicatorNodes.get(indicator.id)!
    if (categoryNodes.has(indicator.categoryId)) categoryNodes.get(indicator.categoryId)!.children.push(node)
    else roots.push(node)
  }
  return [{ id: 'indicator-model-root', label: '指标模型', kind: 'folder', children: roots }]
}

function filterTree(nodes: TreeNode[], term: string): TreeNode[] {
  return nodes.map((node) => { const children = filterTree(node.children, term); const matched = node.label.toLowerCase().includes(term) || (node.code || '').toLowerCase().includes(term); return matched || children.length ? { ...node, children } : null }).filter((node): node is TreeNode => Boolean(node))
}
function searchTree() { keyword.value = keyword.value.trim() }
function onSelect(id: string, checked: boolean) { const next = new Set(selectedIds.value); checked ? next.add(id) : next.delete(id); selectedIds.value = [...next] }
function selectVisible() { const ids = flattenTree(filteredTree.value).filter((node) => node.indicatorId).map((node) => node.indicatorId!); selectedIds.value = [...new Set([...selectedIds.value, ...ids])] }
function clearSelection() { selectedIds.value = [] }
function flattenTree(nodes: TreeNode[]): TreeNode[] { return nodes.flatMap((node) => [node, ...flattenTree(node.children)]) }
function resetQuery() { startDate.value = ''; endDate.value = ''; dimensionFilters.value = {}; page.value = 1; hasMore.value = false; rows.value = [] }
function goBack() { window.history.back() }
function formatValue(value: unknown) { return value === null || value === undefined || value === '' ? '-' : String(value) }
function periodLabel(row: TableRow) { return row.periodType === 'period' ? `${row.periodStart} 至 ${row.periodEnd}` : row.periodStart || row.dataDate }

async function loadIndicatorDetails() {
  const missing = selectedIds.value.filter((id) => !indicatorDetails.value[id])
  if (!missing.length) return
  try {
    const results = await Promise.all(missing.map((id) => apiClient<IndicatorT>('/api/indicators/' + id)))
    for (const ind of results) {
      indicatorDetails.value[ind.id] = ind
    }
  } catch (error) { notify(error instanceof Error ? error.message : String(error)) }
}

async function queryResults() {
  if (!selectedIds.value.length) return
  if (startDate.value && endDate.value && startDate.value > endDate.value) {
    notify('统计期间起始日不能晚于结束日')
    return
  }
  page.value = 1
  await loadResults()
}
async function loadResults() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('indicatorIds', selectedIds.value.join(','))
    if (startDate.value) params.set('periodStart', startDate.value)
    if (endDate.value) params.set('periodEnd', endDate.value)
    if (Object.keys(dimensionFilters.value).length) params.set('dimensionFilters', JSON.stringify(dimensionFilters.value))
    params.set('page', String(page.value))
    params.set('pageSize', String(pageSize))
    const result = await apiClient<{ rows: ResultRow[]; hasMore: boolean }>(`/api/indicator-results?${params.toString()}`)
    rows.value = result.rows
    hasMore.value = result.hasMore
  } catch (error) { notify(error instanceof Error ? error.message : String(error)) } finally { loading.value = false }
}
async function changePage(nextPage: number) {
  page.value = nextPage
  await loadResults()
}
async function addToFavorites() {
  try {
    await Promise.all(selectedIds.value.map((id) => apiClient(`/api/indicators/${id}/favorite`, { method: 'PUT', body: jsonBody({ favorite: true }) })))
    notify(`已收藏 ${selectedIds.value.length} 个指标`)
  } catch (error) { notify(error instanceof Error ? error.message : String(error)) }
}
function exportCsv() {
  if (!tableRows.value.length) return
  const header = ['统计期间', '指标名称', ...dimensionColumns.value, ...resultColumns.value]
  const body = tableRows.value.map((row) => [periodLabel(row), row.indicatorName, ...dimensionColumns.value.map((column) => formatValue(row.dimensions[column])), ...resultColumns.value.map((column) => formatValue(row.values[column]))])
  const csv = [header, ...body].map((line) => line.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n')
  const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `指标查询_${new Date().toISOString().slice(0, 10)}.csv`; link.click(); URL.revokeObjectURL(url)
}
</script>

<style scoped>
.iq-layout { display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 12px; align-items: start; }
.iq-main-panel { display: grid; gap: 12px; min-width: 0; }
.iq-tree-card :deep(.el-card__body) { padding: 8px; }
.iq-head-bar { display: flex; align-items: center; gap: 10px; }
.iq-head-bar strong { color: var(--ink); }
.iq-tree-field { display: grid; grid-template-columns: 84px minmax(0, 1fr); align-items: center; gap: 8px; margin-bottom: 8px; }
.iq-tree-field-label { color: var(--text); font-size: 12px; font-weight: 700; }
.iq-tree-search { display: flex; gap: 6px; margin-bottom: 6px; }
.iq-tree-search :deep(.el-input) { flex: 1; }
.iq-tree-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 2px 0 6px; border-bottom: 1px solid var(--line-soft); }
.iq-tree-scroll { max-height: 480px; overflow: auto; padding: 6px 0; }
.iq-tree-empty { padding: 24px 8px; color: var(--muted); text-align: center; font-size: 12px; }
.iq-selection-footer { display: flex; align-items: center; gap: 5px; min-height: 34px; padding: 0 2px; border-top: 1px solid var(--line-soft); color: var(--muted); font-size: 12px; }
.iq-selection-footer b { color: var(--brand); font-size: 15px; }
.iq-shared { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 10px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--line-soft); }
.iq-shared-label { color: var(--text); font-weight: 700; font-size: 12px; }
.iq-shared-list { display: flex; flex-wrap: wrap; gap: 6px; }
.iq-shared-placeholder { color: var(--muted); font-size: 12px; }
.iq-condition-row { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px; padding: 10px 0 2px; }
.iq-condition-field { display: grid; gap: 3px; min-width: 150px; }
.iq-condition-field span { color: var(--muted); font-size: 12px; font-weight: 700; }
.iq-date-hint { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; margin-left: 2px; border-radius: 50%; border: 1px solid var(--muted); color: var(--muted); font-size: 10px; cursor: help; }
.iq-selected-summary { flex: 1 1 220px; min-width: 0; display: grid; gap: 3px; }
.iq-selected-summary > span { color: var(--muted); font-size: 12px; font-weight: 700; }
.iq-selected-chips { display: flex; flex-wrap: wrap; gap: 5px; min-height: 28px; align-items: center; }
.iq-result-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-left: auto; }
.iq-result-empty { min-height: 320px; display: grid; place-items: center; align-content: center; gap: 8px; color: var(--muted); font-size: 12px; }
.iq-result-empty b { color: var(--ink); }
.iq-loading-mark { color: var(--muted); font-size: 20px; letter-spacing: 3px; }
.iq-pagination { display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding-top: 10px; }
</style>
