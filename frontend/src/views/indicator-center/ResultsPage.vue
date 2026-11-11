<template>
  <div class="page data-list-page">
    <div class="page-head">
      <div><h1>指标数据查询</h1><div class="desc">从指标树选择多个指标，结果按完整维度组合对齐展示。</div></div>
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
          <template #header><div class="iq-head-bar"><strong>查询条件</strong><span class="muted">共有维度用于筛选，结果展示所有已选指标的维度和度量</span></div></template>
          <div class="iq-shared">
            <div class="iq-shared-label">可筛选维度</div>
            <div v-if="selectedIds.length && commonFields.length" class="iq-shared-list">
              <el-tag v-for="field in commonFields" :key="`${field.kind}-${field.name}`" size="small">{{ field.alias }}</el-tag>
            </div>
            <div v-else class="iq-shared-placeholder">选择指标后，系统将在这里显示适用于所有已选指标的维度</div>
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
              <span class="muted">{{ total ? `共 ${total} 行` : '未执行查询' }}</span>
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
          <el-table v-else :data="tableRows" size="small" class="result-table">
            <el-table-column label="统计期间" width="190" class-name="result-dimension-shared" label-class-name="result-dimension-shared">
              <template #default="{ row }">{{ periodLabel(row) }}</template>
            </el-table-column>
            <el-table-column
              v-for="column in dimensionColumns"
              :key="column"
              :label="column"
              :class-name="dimensionClass(column)"
              :label-class-name="dimensionClass(column)"
              min-width="130"
            >
              <template #header>
                <div class="col-header">
                  <span>{{ column }}</span>
                  <span class="col-owner" :title="dimensionOwnerText(column)">{{ dimensionOwnerText(column) }}</span>
                </div>
              </template>
              <template #default="{ row }">{{ formatValue(row.dimensions[column]) }}</template>
            </el-table-column>
            <el-table-column
              v-for="column in flatMeasureColumns"
              :key="column.key"
              :label="column.alias"
              :class-name="measureClass(column)"
              :label-class-name="measureClass(column)"
              min-width="150"
              align="right"
            >
              <template #header>
                <div class="col-header">
                  <span>{{ column.alias }}</span>
                  <span class="col-owner" :title="`${column.indicatorCode} ${column.indicatorName}`">{{ column.indicatorName }}</span>
                </div>
              </template>
              <template #default="{ row }">{{ formatMeasure(row.values[column.key], column.displayPrecision) }}</template>
            </el-table-column>
          </el-table>
          <div v-if="total" class="iq-pagination">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[20, 50, 100, 200, 500]"
              :disabled="loading"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @current-change="loadResults"
              @size-change="onPageSizeChange"
            />
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="windowQuery" title="指标查询结果" width="960px" append-to-body>
      <div class="muted">已选 {{ selectedIds.length }} 个指标 · {{ tableRows.length }} 行结果</div>
      <el-table :data="tableRows" size="small" max-height="420" class="result-table">
        <el-table-column label="统计期间" width="190" class-name="result-dimension-shared" label-class-name="result-dimension-shared">
          <template #default="{ row }">{{ periodLabel(row) }}</template>
        </el-table-column>
        <el-table-column
          v-for="column in dimensionColumns"
          :key="column"
          :label="column"
          :class-name="dimensionClass(column)"
          :label-class-name="dimensionClass(column)"
          min-width="130"
        >
          <template #header>
            <div class="col-header">
              <span>{{ column }}</span>
              <span class="col-owner" :title="dimensionOwnerText(column)">{{ dimensionOwnerText(column) }}</span>
            </div>
          </template>
          <template #default="{ row }">{{ formatValue(row.dimensions[column]) }}</template>
        </el-table-column>
        <el-table-column
          v-for="column in flatMeasureColumns"
          :key="column.key"
          :label="column.alias"
          :class-name="measureClass(column)"
          :label-class-name="measureClass(column)"
          min-width="150"
          align="right"
        >
          <template #header>
            <div class="col-header">
              <span>{{ column.alias }}</span>
              <span class="col-owner" :title="`${column.indicatorCode} ${column.indicatorName}`">{{ column.indicatorName }}</span>
            </div>
          </template>
          <template #default="{ row }">{{ formatMeasure(row.values[column.key], column.displayPrecision) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { api as apiClient, jsonBody } from '../../api'
import IndicatorTreeNode from '../../components/IndicatorTreeNode.vue'
import type { BootstrapData, Indicator as IndicatorT, IndicatorOption as IndicatorOptionT, IndicatorTreeNode as TreeNode } from '../../types'

type BusinessParameter = { indicator_id: string; indicator_name: string; values: Record<string, string> }
type ResultRow = { id: string; data_date: string; business_time?: string | null; period_type: 'point' | 'period'; period_start: string; period_end: string; business_params: BusinessParameter[]; dimensions: Record<string, unknown>; values: Record<string, unknown> }
type QueryField = { name: string; alias: string; kind: 'dimension' | 'measure' }
type MeasureColumn = { key: string; indicatorId: string; alias: string; indicatorName: string; indicatorCode: string; displayPrecision?: number | null }
type MeasureGroup = { key: string; label: string; dimensions: string[]; columns: MeasureColumn[] }
type DimensionOwner = { indicatorId: string; indicatorName: string }

const props = defineProps<{ data: BootstrapData; indicatorId?: string }>()
const notify = inject<(message: string) => void>('notify', () => undefined)
const keyword = ref('')
const startDate = ref('')
const endDate = ref('')
const page = ref(1)
const pageSize = ref(100)
const total = ref(0)
const dimensionFilters = ref<Record<string, string>>({})
const selectedIds = ref<string[]>(props.indicatorId ? [props.indicatorId] : [])
const rows = ref<ResultRow[]>([])
const dimensionColumns = ref<string[]>([])
const dimensionOwners = ref<Record<string, DimensionOwner[]>>({})
const measureGroups = ref<MeasureGroup[]>([])
const loading = ref(false)
const windowQuery = ref(false)
const indicatorDetails = ref<Record<string, IndicatorT>>({})

const visibleIndicators = computed(() => props.data.indicators)
const tree = computed(() => buildTree(visibleIndicators.value))
const filteredTree = computed(() => keyword.value.trim() ? filterTree(tree.value, keyword.value.trim().toLowerCase()) : tree.value)
const selectedIndicators = computed(() => selectedIds.value.map((id) => indicatorDetails.value[id]).filter((item): item is IndicatorT => Boolean(item)))

const commonFields = computed<QueryField[]>(() => {
  if (!selectedIndicators.value.length) return []
  const first = fieldList(selectedIndicators.value[0]).filter((field) => field.kind === 'dimension')
  return first.filter((field) => selectedIndicators.value.every((indicator) => fieldList(indicator).some((candidate) => candidate.name === field.name && candidate.kind === 'dimension')))
})
const commonFilterFields = computed(() => commonFields.value.filter((field) => field.kind === 'dimension' && field.name !== 'DATA_DATE'))
const tableRows = computed(() => rows.value)
const flatMeasureColumns = computed(() => measureGroups.value.flatMap((group) => group.columns))

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
function resetQuery() { startDate.value = ''; endDate.value = ''; dimensionFilters.value = {}; page.value = 1; total.value = 0; rows.value = []; dimensionColumns.value = []; dimensionOwners.value = {}; measureGroups.value = [] }
function goBack() { window.history.back() }
function formatValue(value: unknown) { return value === null || value === undefined || value === '' ? '' : String(value) }
function formatMeasure(value: unknown, precision?: number | null) {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  if (precision === undefined || precision === null) return String(value)
  return num.toFixed(precision)
}
function periodLabel(row: ResultRow) {
  if (row.business_time) return row.business_time
  return row.period_type === 'period' ? `${row.period_start} 至 ${row.period_end}` : row.period_start || row.data_date
}
function indicatorColorClass(indicatorId: string, kind: 'dimension' | 'measure') {
  const index = selectedIds.value.indexOf(indicatorId)
  return index < 0 ? `result-${kind}-shared` : `result-${kind}-owner-${index % 8}`
}
function dimensionClass(alias: string) {
  const owners = dimensionOwners.value[alias] || []
  return owners.length === 1 ? indicatorColorClass(owners[0].indicatorId, 'dimension') : 'result-dimension-shared'
}
function dimensionOwnerText(alias: string) {
  const owners = dimensionOwners.value[alias] || []
  if (!owners.length) return ''
  if (owners.length > 1 && owners.length === selectedIds.value.length) return '全部指标共有'
  return owners.map((owner) => owner.indicatorName).join('、')
}
function measureClass(column: MeasureColumn) { return indicatorColorClass(column.indicatorId, 'measure') }
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
    if (startDate.value) params.set('startDate', startDate.value)
    if (endDate.value) params.set('endDate', endDate.value)
    if (Object.keys(dimensionFilters.value).length) params.set('dimensionFilters', JSON.stringify(dimensionFilters.value))
    params.set('page', String(page.value))
    params.set('pageSize', String(pageSize.value))
    const result = await apiClient<{ rows: ResultRow[]; dimensionColumns: string[]; dimensionOwners: Record<string, DimensionOwner[]>; measureGroups: MeasureGroup[]; total: number }>(`/api/indicator-results?${params.toString()}`)
    rows.value = result.rows
    dimensionColumns.value = result.dimensionColumns
    dimensionOwners.value = result.dimensionOwners
    measureGroups.value = result.measureGroups
    total.value = result.total
  } catch (error) { notify(error instanceof Error ? error.message : String(error)) } finally { loading.value = false }
}
async function onPageSizeChange() {
  page.value = 1
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
  const measureColumns = measureGroups.value.flatMap((group) => group.columns)
  const header = ['统计期间', ...dimensionColumns.value, ...measureColumns.map((column) => `${column.indicatorName} · ${column.alias}`)]
  const body = tableRows.value.map((row) => [
    periodLabel(row),
    ...dimensionColumns.value.map((column) => formatValue(row.dimensions[column])),
    ...measureColumns.map((column) => formatMeasure(row.values[column.key], column.displayPrecision)),
  ])
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
.result-table :deep(.col-header) { display: grid; gap: 1px; line-height: 1.25; }
.result-table :deep(.col-owner) { font-size: 11px; color: #8a8f99; font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.result-table :deep(.result-dimension-shared) { background-color: #f1f3f5; }
.result-table :deep(.result-dimension-owner-0) { background-color: #eaf2ff; }
.result-table :deep(.result-measure-owner-0) { background-color: #d7e6ff; }
.result-table :deep(.result-dimension-owner-1) { background-color: #eaf7ef; }
.result-table :deep(.result-measure-owner-1) { background-color: #d7f0e0; }
.result-table :deep(.result-dimension-owner-2) { background-color: #fff4e5; }
.result-table :deep(.result-measure-owner-2) { background-color: #ffe7c2; }
.result-table :deep(.result-dimension-owner-3) { background-color: #f4edff; }
.result-table :deep(.result-measure-owner-3) { background-color: #e7d9ff; }
.result-table :deep(.result-dimension-owner-4) { background-color: #e5f7f7; }
.result-table :deep(.result-measure-owner-4) { background-color: #cceeed; }
.result-table :deep(.result-dimension-owner-5) { background-color: #fff0f0; }
.result-table :deep(.result-measure-owner-5) { background-color: #ffdcdc; }
.result-table :deep(.result-dimension-owner-6) { background-color: #f4f6e8; }
.result-table :deep(.result-measure-owner-6) { background-color: #e8eccb; }
.result-table :deep(.result-dimension-owner-7) { background-color: #eaf0f4; }
.result-table :deep(.result-measure-owner-7) { background-color: #d6e2eb; }
</style>
