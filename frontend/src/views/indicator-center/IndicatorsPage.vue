<template>
    <div class="page data-list-page">
      <div class="page-head"><div><h1>指标管理</h1><div class="desc">左侧按分类管理指标归属（可新建/删除分类），右侧集中查询和维护指标定义，创建入口及全部管理动作均在指标列表操作列中。</div></div><div class="actions"><el-button type="primary" @click="openBatchRun">批量运行</el-button><el-button :loading="exportLoading" :disabled="!batchSelectedIds.length" :title="batchSelectedIds.length ? '' : '请先勾选要导出的指标'" @click="exportJson">导出JSON</el-button><el-button @click="openImportDialog">导入JSON</el-button></div></div>
      <div class="indicator-main-layout data-list-main">
        <el-card shadow="never" class="indicator-category-panel">
          <template #header><div class="head-bar"><strong>指标分类</strong></div></template>
          <el-tree :data="categoryTree" node-key="id" default-expand-all :expand-on-click-node="false" :highlight-current="true" :current-node-key="selectedCategoryId" class="category-tree" @node-click="onCategoryClick">
            <template #default="{ data }">
              <span class="category-node-row">
                <span class="category-node-text"><span>{{ data.label }}</span><span class="muted">（{{ categoryCount(data.id) }}）</span></span>
                <span class="category-actions">
                  <el-button link type="primary" size="small" :title="data.id==='all' ? '新建顶级分类' : '新建子分类'" @click.stop="createCategory(data)">＋</el-button>
                  <el-button v-if="data.id !== 'all'" link type="danger" size="small" title="删除分类" @click.stop="deleteCategory(data)">×</el-button>
                </span>
              </span>
            </template>
          </el-tree>
        </el-card>

        <div class="indicator-main-panel data-list-panel">
          <div class="filterbar indicator-filter">
            <div class="filter-item indicator-keyword"><span>指标检索</span><el-input v-model="searchText" placeholder="指标名称、编码或业务口径" clearable @keyup.enter="query" /></div>
            <div class="filter-item"><span>所属模型</span><el-select v-model="modelFilter" style="width:100%"><el-option value="all" label="全部模型" /><el-option v-for="m in data.models" :key="m.id" :value="m.id" :label="m.name" /></el-select></div>
            <div class="filter-item"><span>指标状态</span><el-select v-model="statusFilter" style="width:100%"><el-option value="all" label="全部状态" /><el-option value="enabled" label="已启用" /><el-option value="draft" label="草稿" /><el-option value="disabled" label="已停用" /><el-option value="offline" label="已下线" /></el-select></div>
            <div class="indicator-filter-actions"><el-button type="primary" @click="query">查询</el-button><el-button @click="resetFilters">重置</el-button><el-button type="primary" class="new-indicator-btn" @click="emit('go','builder')">新增</el-button></div>
          </div>

          <div class="panel-head indicator-panel-head"><div><strong>指标列表</strong><span>共 {{ total }} 个</span></div><div class="indicator-status-summary"><span>已启用 {{ data.indicators.filter(i=>i.status==='enabled').length }}</span><span>草稿 {{ data.indicators.filter(i=>i.status==='draft').length }}</span><span>已停用 {{ data.indicators.filter(i=>['disabled','offline'].includes(i.status)).length }}</span></div></div>

          <el-table :data="indicatorList" v-loading="loading" size="small" :max-height="tableMaxHeight" @selection-change="onSelectionChange">
            <el-table-column type="selection" width="40" />
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="indicator-more-actions">
                  <span>更多操作</span>
                  <el-button link type="primary" @click="emit('go','versions',row.id)">版本记录</el-button>
                  <el-button link @click="toggleFavorite(row)">{{ row.favorite ? '取消收藏' : '加入收藏' }}</el-button>
                  <el-button link @click="updateStatus(row, row.status==='enabled' ? 'disabled' : 'enabled')">{{ row.status==='enabled' ? '停用指标' : '启用指标' }}</el-button>
                  <el-button link @click="showSql(row)">查看 SQL</el-button>
                  <el-button link @click="copy(row.id)">复制指标</el-button>
                  <el-button link type="danger" @click="remove(row.id)">删除指标</el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="指标信息" min-width="220">
              <template #default="{ row }">
                <div class="indicator-name"><span v-if="row.favorite" title="已收藏">★</span><b>{{ row.name }}</b></div>
                <div class="indicator-code">{{ row.code }}</div>
                <div class="muted caliber-cell" :title="getBizCaliber(row)">{{ getBizCaliber(row) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="类型 / 分类" min-width="140">
              <template #default="{ row }"><b class="indicator-type">{{ typeName(row) }}</b><div class="muted">{{ categoryName(row.categoryId) }}</div></template>
            </el-table-column>
            <el-table-column label="所属模型" min-width="150">
              <template #default="{ row }"><b>{{ modelDisplayName(data.models, row.modelId) }}</b></template>
            </el-table-column>
            <el-table-column label="运行配置" min-width="130">
              <template #default="{ row }"><span>{{ row.config.schedule?.frequency || '日' }}频</span><div class="muted result-table-name">{{ getResultTable(row) }}</div></template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="row.status==='enabled' ? 'success' : (row.status==='draft' ? 'info' : 'danger')">{{ statusName(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="更新时间" width="150"><template #default="{ row }">{{ row.updatedAt || row.createdAt }}</template></el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="emit('edit', row.id)">编辑</el-button>
                <el-button link @click="run(row.id)">运行</el-button>
                <el-button link @click="emit('go','results',row.id)">数据</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <div class="indicator-empty"><b>没有找到匹配的指标</b><span>请调整检索条件或重置筛选。</span><el-button @click="resetFilters">重置筛选</el-button></div>
            </template>
          </el-table>

          <div v-if="total" class="indicator-pagination">
            <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background @current-change="loadIndicators" @size-change="loadIndicators" />
          </div>
        </div>
      </div>

      <el-dialog v-model="sqlDialogOpen" title="指标 SQL" width="720px" append-to-body>
        <div v-if="sqlIndicator">
          <div class="muted sql-dialog-meta">{{ sqlIndicator.code }} · {{ modelDisplayName(data.models, sqlIndicator.modelId) }}</div>
          <div class="confirm-panel">
            <div><span>指标类型</span><b>{{ typeName(sqlIndicator) }}</b></div>
            <div><span>结果表</span><b>{{ getResultTable(sqlIndicator) }}</b></div>
            <div><span>统计频率</span><b>{{ sqlIndicator.config.schedule?.frequency || '日' }}频</b></div>
            <div><span>当前状态</span><b>{{ statusName(sqlIndicator.status) }}</b></div>
          </div>
          <pre class="sql indicator-sql-preview">{{ sqlIndicator.sqlText }}</pre>
        </div>
        <template #footer><el-button type="primary" @click="sqlIndicator=null">关闭</el-button></template>
      </el-dialog>

      <!-- ...existing run/batch dialogs... -->

      <el-dialog v-model="createDialogOpen" title="新建指标分类" width="420px" append-to-body>
        <el-form label-width="90px" @submit.prevent>
          <el-form-item label="分类名称" required>
            <el-input v-model="newCategoryName" placeholder="请输入分类名称" @keyup.enter="confirmCreateCategory" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createDialogOpen=false">取消</el-button>
          <el-button type="primary" @click="confirmCreateCategory">确定</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="runDialogOpen" :title="runTarget ? `运行指标：${runTarget.name}` : '运行指标'" width="620px" append-to-body>
        <div v-if="runTarget">
          <div class="muted run-dialog-meta">{{ runTarget.code }} · {{ runTarget.name }}</div>
          <el-form label-width="90px">
            <template v-if="runTargetBiz === 'period'">
              <el-form-item label="开始日期" required><el-input v-model="dateStartSpecific" type="date" /></el-form-item>
              <el-form-item label="结束日期" required><el-input v-model="dateEndSpecific" type="date" /></el-form-item>
            </template>
            <template v-else-if="runTargetBiz === 'balance'">
              <el-form-item label="业务日期" required><el-input v-model="dateSingleSpecific" type="date" /></el-form-item>
            </template>
            <el-form-item v-else label="运行日期" required>
              <el-input v-model="runDate" type="date" />
            </el-form-item>
          </el-form>
          <div v-if="runResult" class="run-feedback">
            <el-alert type="success" :closable="false" show-icon :title="`运行成功，写入 ${runResult.rowCount} 行结果`" />
            <div class="section-title-line run-sql-title"><h3>SQL 预览</h3></div>
            <pre class="sql">{{ runResult.sqlText }}</pre>
          </div>
          <div v-if="runError" class="notice run-error">{{ runError }}</div>
        </div>
        <template #footer>
          <el-button @click="runDialogOpen=false">关闭</el-button>
          <el-button v-if="!runResult" type="primary" :loading="runLoading" @click="doRun">运行</el-button>
          <el-button v-else type="primary" @click="goToResults">查看结果</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="batchOpen" title="批量运行指标" width="620px" append-to-body>
        <el-form label-width="90px">
          <el-form-item label="运行范围">
            <el-select v-model="batchScope" style="width:100%">
              <el-option value="all" label="全部指标" />
              <el-option value="category" label="按分类" />
              <el-option value="selected" label="当前勾选" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="batchScope==='category'" label="分类" required>
            <el-select v-model="batchCategoryId" style="width:100%"><el-option v-for="c in data.indicatorCategories.filter(x=>x.id!=='root')" :key="c.id" :value="c.id" :label="c.name" /></el-select>
          </el-form-item>
          <el-form-item v-if="batchScope==='selected'" label="已选"><span class="muted">{{ batchSelectedIds.length }} 个指标</span></el-form-item>
          <el-form-item label="业务类型">
            <el-select v-model="batchDateType" style="width:100%"><el-option value="balance" label="余额类（单日）" /><el-option value="period" label="时段类（区间）" /></el-select>
          </el-form-item>
          <template v-if="batchDateType==='period'">
            <el-form-item label="开始日期" required>
              <el-select v-model="batchStartOption" style="width:100%"><el-option value="month_start" label="本月初" /><el-option value="year_start" label="年初" /><el-option value="month" label="月份" /><el-option value="specific" label="具体日期" /></el-select>
            </el-form-item>
            <el-form-item v-if="batchStartOption==='month'" label="月份" required><el-input v-model="batchStartMonth" type="month" /></el-form-item>
            <el-form-item v-if="batchStartOption==='specific'" label="日期" required><el-input v-model="batchStartSpecific" type="date" /></el-form-item>
            <el-form-item label="结束日期" required>
              <el-select v-model="batchEndOption" style="width:100%"><el-option value="today" label="今天" /><el-option value="t1" label="T-1" /><el-option value="last_workday" label="最近工作日" /><el-option value="specific" label="具体日期" /></el-select>
            </el-form-item>
            <el-form-item v-if="batchEndOption==='specific'" label="日期" required><el-input v-model="batchEndSpecific" type="date" /></el-form-item>
          </template>
          <template v-else>
            <el-form-item label="业务日期" required>
              <el-select v-model="batchSingleOption" style="width:100%"><el-option value="today" label="今天" /><el-option value="t1" label="T-1" /><el-option value="last_workday" label="最近工作日" /><el-option value="specific" label="具体日期" /></el-select>
            </el-form-item>
            <el-form-item v-if="batchSingleOption==='specific'" label="日期" required><el-input v-model="batchSingleSpecific" type="date" /></el-form-item>
          </template>
        </el-form>
        <div v-if="batchResult" class="notice batch-result">共 {{ batchResult.total }} 个，成功 {{ batchResult.success }}，失败 {{ batchResult.failed }}</div>
        <template #footer>
          <el-button @click="batchOpen=false">关闭</el-button>
          <el-button type="primary" :loading="batchLoading" @click="doBatchRun">开始运行</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="importDialogOpen" title="导入指标（JSON 迁移）" width="780px" append-to-body>
        <div class="import-file-row">
          <input ref="fileInput" type="file" accept=".json,application/json" style="display:none" @change="onImportFileChange" />
          <el-button type="primary" plain @click="fileInput?.click()">选择 JSON 文件</el-button>
          <span class="muted">{{ importFileName || '请选择系统导出的指标 JSON 文件' }}</span>
        </div>
        <template v-if="importReport">
          <el-alert v-if="importReport.summary.error" type="error" :closable="false" show-icon class="import-alert"
            :title="`校验未通过：共 ${importReport.summary.total} 个，可导入 ${importReport.summary.ok}，错误 ${importReport.summary.error}，跳过 ${importReport.summary.skip}`"
            description="存在错误的指标，本次导入已全部停止。请按下表修正后重新导入。" />
          <el-alert v-else type="success" :closable="false" show-icon class="import-alert"
            :title="`校验通过：共 ${importReport.summary.total} 个，可导入 ${importReport.summary.ok}，跳过 ${importReport.summary.skip}`" />
          <el-alert v-if="importReport.summary.skip" type="warning" :closable="false" show-icon class="import-alert"
            :title="`文件中含 ${importReport.summary.skip} 个衍生指标，暂不支持自动迁移，导入时将跳过`" />
          <el-alert v-if="importReport.missingModels.length" type="error" :closable="false" show-icon class="import-alert"
            :title="`目标库缺少 ${importReport.missingModels.length} 个模型（按模型编码匹配），请先同步模型`"
            :description="importReport.missingModels.join('、')" />
          <el-alert v-if="importReport.missingCategories.length" type="warning" :closable="false" show-icon class="import-alert"
            :title="`目标库缺少 ${importReport.missingCategories.length} 个分类（按分类名称匹配）`"
            :description="importReport.missingCategories.join('、')" />
          <el-table :data="importReport.items" size="small" max-height="320">
            <el-table-column label="状态" width="86">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status==='ok' ? 'success' : (row.status==='skip' ? 'info' : 'danger')">{{ row.status==='ok' ? '可导入' : (row.status==='skip' ? '跳过' : '错误') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="指标名称" min-width="140" show-overflow-tooltip />
            <el-table-column prop="code" label="源编码" width="96" />
            <el-table-column prop="modelCode" label="模型编码" min-width="130" show-overflow-tooltip />
            <el-table-column label="分类" min-width="100">
              <template #default="{ row }">{{ row.categoryName || '未分类' }}</template>
            </el-table-column>
            <el-table-column label="问题明细" min-width="200">
              <template #default="{ row }"><span class="import-errors">{{ row.errors.join('；') || '-' }}</span></template>
            </el-table-column>
          </el-table>
        </template>
        <el-alert v-if="importDone" type="success" :closable="false" show-icon class="import-alert" :title="importDoneMessage" />
        <template #footer>
          <el-button @click="importDialogOpen=false">关闭</el-button>
          <el-button type="primary" :loading="importLoading" :disabled="!importReport || importReport.summary.error > 0 || importReport.summary.ok === 0 || importDone" @click="doImport">确认导入</el-button>
        </template>
      </el-dialog>
    </div>

</template>

<script lang="ts">
import { defineComponent, inject, ref, ref as vueRef, computed as vueComputed, watch as vueWatch } from 'vue'
import { api as requestApi, jsonBody as toJsonBody, apiDownload } from '../../api'
import type { BootstrapData as BootstrapDataT, Indicator as IndicatorT, IndicatorOption as IndicatorOptionT, ModelOption as ModelOptionT, PageResult as PageResultT } from '../../types'

const ToastInject = 'notify'

function useNotify() {
  return inject<(message: string) => void>(ToastInject, () => undefined)
}

function getMeasures(indicator: IndicatorT): Array<{ fieldName: string; alias: string; aggFunc: string }> {
  return indicator.config.measures ?? (indicator.config.measure ? [indicator.config.measure] : [])
}

function getBizCaliber(indicator: IndicatorT) {
  return indicator.config.basic?.bizCaliber || '业务口径待完善'
}

function getResultTable(indicator: IndicatorT) {
  return indicator.config.schedule?.resultTable || 'T_IND_RESULT_D'
}

function modelDisplayName(models: ModelOptionT[], modelId: string) {
  return models.find((m) => m.id === modelId)?.name ?? '-'
}

type CategoryNode = { id: string; label: string; children: CategoryNode[] }

// ---------- 指标 JSON 导入导出 ----------
type TransferPreviewItem = { index: number; code: string; name: string; modelCode: string; categoryName: string; status: 'ok' | 'error' | 'skip'; errors: string[] }
type TransferReport = {
  summary: { total: number; ok: number; error: number; skip: number }
  items: TransferPreviewItem[]
  missingModels: string[]
  missingCategories: string[]
}

const IndicatorsPage = defineComponent({
  props: { data: { type: Object as () => BootstrapDataT, required: true } },
  emits: ['go', 'edit', 'reload'],
  setup(props, { emit }) {
    const notify = useNotify()
    const selectedCategoryId = vueRef('all')
    const createDialogOpen = vueRef(false)
    const newCategoryName = vueRef('')
    const newCategoryParent = vueRef<CategoryNode>({ id: 'all', label: '全部指标', children: [] })
    const searchText = vueRef('')
    const keyword = vueRef('')
    const statusFilter = vueRef('all')
    const modelFilter = vueRef('all')
    const sqlIndicator = vueRef<IndicatorT | null>(null)
    const runDialogOpen = vueRef(false)
    const runTarget = vueRef<{ id: string; code: string; name: string; modelId: string; bizDateType?: 'balance' | 'period' | '' } | null>(null)
    const runDate = vueRef('2026-07-10')
    const runLoading = vueRef(false)
    const runResult = vueRef<{ rowCount: number; sqlText: string } | null>(null)
    const runError = vueRef('')
    // 业务日期：运行界面按指标自身的业务时间类型，由用户直接指定具体日期
    const dateSingleSpecific = vueRef('')
    const dateStartSpecific = vueRef('')
    const dateEndSpecific = vueRef('')
    const runTargetBiz = vueComputed(() => {
      if (runTarget.value?.bizDateType) return runTarget.value.bizDateType
      const model = props.data.models.find((m) => m.id === runTarget.value?.modelId)
      return model?.bizDateType || ''
    })
    // 批量运行
    const batchOpen = vueRef(false)
    const batchScope = vueRef('all')
    const batchCategoryId = vueRef('')
    const batchSelectedIds = vueRef<string[]>([])
    const batchDateType = vueRef('balance')
    const batchSingleOption = vueRef('today')
    const batchSingleSpecific = vueRef('')
    const batchStartOption = vueRef('month_start')
    const batchStartMonth = vueRef('')
    const batchStartSpecific = vueRef('')
    const batchEndOption = vueRef('today')
    const batchEndSpecific = vueRef('')
    const batchLoading = vueRef(false)
    const batchResult = vueRef<{ total: number; success: number; failed: number } | null>(null)
    const pageSize = vueRef(10)
    const currentPage = vueRef(1)
    const tableMaxHeight = 'calc(100vh - 330px)'
    const loading = vueRef(false)
    const total = vueRef(0)
    const indicatorList = vueRef<IndicatorT[]>([])
    const categoryTree = vueComputed<CategoryNode[]>(() => {
      const cats = props.data.indicatorCategories.filter((c) => c.id !== 'root')
      const nodes = new Map<string, CategoryNode>()
      cats.forEach((c) => nodes.set(c.id, { id: c.id, label: c.name, children: [] }))
      const order = (a: string, b: string) => ((cats.find((c) => c.id === a)?.sortOrder ?? 0) - (cats.find((c) => c.id === b)?.sortOrder ?? 0))
      const sortRec = (arr: CategoryNode[]) => { arr.sort((x, y) => order(x.id, y.id)); arr.forEach((n) => sortRec(n.children)) }
      const roots: CategoryNode[] = []
      cats.forEach((c) => {
        const node = nodes.get(c.id)!
        const parent = c.parentId && c.parentId !== 'root' ? nodes.get(c.parentId) : undefined
        if (parent) parent.children.push(node)
        else roots.push(node)
      })
      sortRec(roots)
      return [{ id: 'all', label: '全部指标', children: roots }]
    })
    const sqlDialogOpen = vueComputed({
      get: () => !!sqlIndicator.value,
      set: (v: boolean) => { if (!v) sqlIndicator.value = null },
    })

    async function loadIndicators() {
      loading.value = true
      try {
        const params = new URLSearchParams()
        params.set('page', String(currentPage.value))
        params.set('pageSize', String(pageSize.value))
        if (keyword.value) params.set('keyword', keyword.value)
        if (statusFilter.value !== 'all') params.set('status', statusFilter.value)
        if (modelFilter.value !== 'all') params.set('modelId', modelFilter.value)
        if (selectedCategoryId.value !== 'all') params.set('categoryId', selectedCategoryId.value)
        const result = await requestApi<PageResultT<IndicatorT>>(`/api/indicators?${params.toString()}`)
        indicatorList.value = result.items
        total.value = result.total
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        loading.value = false
      }
    }
    loadIndicators()
    function categoryCount(id: string) {
      return id === 'all' ? props.data.indicators.length : props.data.indicators.filter((i) => i.categoryId === id).length
    }
    function onCategoryClick(data: CategoryNode) {
      selectedCategoryId.value = data.id
      currentPage.value = 1
      loadIndicators()
    }
    function createCategory(data: CategoryNode) {
      newCategoryParent.value = data
      newCategoryName.value = ''
      createDialogOpen.value = true
    }
    async function confirmCreateCategory() {
      const name = newCategoryName.value.trim()
      if (!name) { notify('请输入分类名称'); return }
      const parentId = newCategoryParent.value.id === 'all' ? 'root' : newCategoryParent.value.id
      const exists = props.data.indicatorCategories.some((c) => c.parentId === parentId && c.name === name)
      if (exists) { notify('同级分类名称已存在'); return }
      await requestApi('/api/indicator-categories', { method: 'POST', body: toJsonBody({ name, parentId, sortOrder: 10, enabled: true }) })
      notify('分类已新建')
      createDialogOpen.value = false
      emit('reload')
    }
    async function deleteCategory(data: CategoryNode) {
      if (data.id === 'all') return
      const hasChildren = props.data.indicatorCategories.some((c) => c.parentId === data.id)
      const hasIndicators = props.data.indicators.some((i) => i.categoryId === data.id)
      if (!window.confirm(hasChildren || hasIndicators ? '该分类下还有子分类或指标，删除将被系统拦截。仍要尝试删除吗？' : '确认删除该分类？')) return
      try {
        await requestApi(`/api/indicator-categories/${data.id}`, { method: 'DELETE' })
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
        return
      }
      notify('分类已删除')
      if (selectedCategoryId.value === data.id) selectedCategoryId.value = 'all'
      emit('reload')
    }
    function categoryName(id: string) {
      return props.data.indicatorCategories.find((item) => item.id === id)?.name ?? '未分类'
    }
    function typeName(indicator: IndicatorT) {
      return ({ basic: '基础指标', derived: '衍生指标' } as Record<string, string>)[indicator.config.indicatorType ?? 'basic'] ?? '基础指标'
    }
    function statusName(status: string) {
      return ({ enabled: '已启用', draft: '草稿', disabled: '已停用', offline: '已下线' } as Record<string, string>)[status] ?? status
    }
    async function query() {
      keyword.value = searchText.value.trim()
      currentPage.value = 1
      await loadIndicators()
    }
    function run(id: string) {
      const target = indicatorList.value.find((i) => i.id === id) || props.data.indicators.find((i) => i.id === id)
      if (!target) return
      runTarget.value = target
      runDate.value = '2026-07-10'
      dateSingleSpecific.value = ''
      dateStartSpecific.value = ''
      dateEndSpecific.value = ''
      runResult.value = null
      runError.value = ''
      runDialogOpen.value = true
    }
    function buildDateOption() {
      if (runTargetBiz.value === 'period') {
        return {
          type: 'period',
          start: { option: 'specific', value: dateStartSpecific.value },
          end: { option: 'specific', value: dateEndSpecific.value },
        }
      }
      if (runTargetBiz.value === 'balance') {
        return { type: 'balance', single: { option: 'specific', value: dateSingleSpecific.value } }
      }
      return null
    }
    async function doRun() {
      if (!runTarget.value) return
      if (runTargetBiz.value === 'balance' && !dateSingleSpecific.value) {
        runError.value = '请选择业务日期'
        return
      }
      if (runTargetBiz.value === 'period') {
        if (!dateStartSpecific.value || !dateEndSpecific.value) {
          runError.value = '请选择开始日期和结束日期'
          return
        }
        if (dateStartSpecific.value > dateEndSpecific.value) {
          runError.value = '开始日期不能晚于结束日期'
          return
        }
      }
      runLoading.value = true
      runError.value = ''
      runResult.value = null
      try {
        const payload: Record<string, unknown> = { runDate: runDate.value }
        const dateOption = buildDateOption()
        if (dateOption) payload.dateOption = dateOption
        const result = await requestApi<{ rowCount: number; sqlText: string }>(`/api/indicators/${runTarget.value.id}/runs`, { method: 'POST', body: toJsonBody(payload) })
        runResult.value = result
        emit('reload')
      } catch (error) {
        runError.value = error instanceof Error ? error.message : String(error)
      } finally {
        runLoading.value = false
      }
    }
    function goToResults() {
      if (!runTarget.value) return
      const id = runTarget.value.id
      runDialogOpen.value = false
      emit('go', 'results', id)
    }
    function onSelectionChange(rows: IndicatorT[]) {
      batchSelectedIds.value = rows.map((r) => r.id)
    }
    function openBatchRun() {
      batchScope.value = 'all'
      batchCategoryId.value = ''
      batchDateType.value = 'balance'
      batchSingleOption.value = 'today'; batchSingleSpecific.value = ''
      batchStartOption.value = 'month_start'; batchStartMonth.value = ''; batchStartSpecific.value = ''
      batchEndOption.value = 'today'; batchEndSpecific.value = ''
      batchResult.value = null
      batchOpen.value = true
    }
    function buildBatchDateOption() {
      if (batchDateType.value === 'period') {
        return {
          type: 'period',
          start: { option: batchStartOption.value, value: batchStartOption.value === 'month' ? batchStartMonth.value : (batchStartOption.value === 'specific' ? batchStartSpecific.value : '') },
          end: { option: batchEndOption.value, value: batchEndOption.value === 'specific' ? batchEndSpecific.value : '' },
        }
      }
      return { type: 'balance', single: { option: batchSingleOption.value, value: batchSingleOption.value === 'specific' ? batchSingleSpecific.value : '' } }
    }
    async function doBatchRun() {
      batchLoading.value = true
      batchResult.value = null
      try {
        batchResult.value = await requestApi(`/api/batch-runs`, {
          method: 'POST',
          body: toJsonBody({ scope: batchScope.value, categoryId: batchCategoryId.value, indicatorIds: batchSelectedIds.value, dateOption: buildBatchDateOption() }),
        })
        emit('reload')
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        batchLoading.value = false
      }
    }
    async function copy(id: string) {
      await requestApi(`/api/indicators/${id}/copies`, { method: 'POST', body: toJsonBody({}) })
      notify('指标已复制')
      emit('reload')
    }
    // ---------- 指标 JSON 导入导出 ----------
    const exportLoading = vueRef(false)
    const importDialogOpen = vueRef(false)
    const fileInput = vueRef<HTMLInputElement | null>(null)
    const importFileName = vueRef('')
    const importFileData = vueRef<Record<string, unknown> | null>(null)
    const importReport = vueRef<TransferReport | null>(null)
    const importLoading = vueRef(false)
    const importDone = vueRef(false)
    const importDoneMessage = vueRef('')

    async function exportJson() {
      exportLoading.value = true
      try {
        // 仅导出勾选的指标（按钮在无勾选时禁用）
        await apiDownload('/api/indicators/export', { method: 'POST', body: toJsonBody({ ids: batchSelectedIds.value }) })
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        exportLoading.value = false
      }
    }
    function openImportDialog() {
      importFileName.value = ''
      importFileData.value = null
      importReport.value = null
      importLoading.value = false
      importDone.value = false
      importDoneMessage.value = ''
      importDialogOpen.value = true
    }
    function onImportFileChange(event: Event) {
      const input = event.target as HTMLInputElement
      const file = input.files?.[0]
      input.value = ''
      if (!file) return
      importFileName.value = file.name
      importReport.value = null
      importDone.value = false
      importDoneMessage.value = ''
      const reader = new FileReader()
      reader.onload = async () => {
        try {
          const data = JSON.parse(String(reader.result || '{}')) as Record<string, unknown>
          importFileData.value = data
          importReport.value = await requestApi<TransferReport>('/api/indicators/import/preview', { method: 'POST', body: toJsonBody(data) })
        } catch (error) {
          importFileData.value = null
          notify(error instanceof Error ? error.message : String(error))
        }
      }
      reader.readAsText(file, 'utf-8')
    }
    async function doImport() {
      if (!importFileData.value || !importReport.value) return
      importLoading.value = true
      try {
        const result = await requestApi<{ blocked: boolean; created?: Array<{ code: string; name: string }>; skipped?: number } & Partial<TransferReport>>(
          '/api/indicators/import', { method: 'POST', body: toJsonBody(importFileData.value) })
        if (result.blocked) {
          importReport.value = result as TransferReport
          notify('校验未通过，已全部停止导入，请查看问题清单')
        } else {
          importDone.value = true
          importDoneMessage.value = `导入完成：成功创建 ${result.created?.length ?? 0} 个指标，跳过 ${result.skipped ?? 0} 个衍生指标`
          emit('reload')
        }
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        importLoading.value = false
      }
    }
    async function updateStatus(ind: IndicatorT, status: string) {
      await requestApi(`/api/indicators/${ind.id}`, { method: 'PUT', body: toJsonBody({ name: ind.name, modelId: ind.modelId, categoryId: ind.categoryId, status, config: ind.config }) })
      notify(`指标状态已更新：${status}`)
      emit('reload')
    }
    async function toggleFavorite(ind: IndicatorT) {
      await requestApi(`/api/indicators/${ind.id}/favorite`, { method: 'PUT', body: toJsonBody({ favorite: !ind.favorite }) })
      notify(ind.favorite ? '已取消收藏' : '已加入收藏')
      emit('reload')
    }
    async function remove(id: string) {
      if (!window.confirm('确认删除指标？')) return
      await requestApi(`/api/indicators/${id}`, { method: 'DELETE' })
      notify('指标已删除')
      emit('reload')
    }
    function showSql(ind: IndicatorT) {
      sqlIndicator.value = ind
    }
    function resetFilters() {
      searchText.value = ''
      keyword.value = ''
      statusFilter.value = 'all'
      modelFilter.value = 'all'
      selectedCategoryId.value = 'all'
      currentPage.value = 1
      loadIndicators()
    }
    return { selectedCategoryId, categoryTree, categoryCount, onCategoryClick, createCategory, confirmCreateCategory, deleteCategory, createDialogOpen, newCategoryName, searchText, keyword, statusFilter, modelFilter, sqlIndicator, sqlDialogOpen, runDialogOpen, runTarget, runTargetBiz, runDate, dateSingleSpecific, dateStartSpecific, dateEndSpecific, runLoading, runResult, runError, doRun, goToResults, onSelectionChange, openBatchRun, doBatchRun, batchOpen, batchScope, batchCategoryId, batchSelectedIds, batchDateType, batchSingleOption, batchSingleSpecific, batchStartOption, batchStartMonth, batchStartSpecific, batchEndOption, batchEndSpecific, batchLoading, batchResult, pageSize, currentPage, tableMaxHeight, total, indicatorList, loading, categoryName, typeName, statusName, query, resetFilters, emit, run, copy, updateStatus, toggleFavorite, remove, showSql, getBizCaliber, getResultTable, modelDisplayName, loadIndicators, exportLoading, exportJson, importDialogOpen, fileInput, importFileName, importReport, importLoading, importDone, importDoneMessage, openImportDialog, onImportFileChange, doImport }
  },

})

export default IndicatorsPage
</script>

<style scoped>
.indicator-main-layout { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 12px; align-items: start; }
.indicator-category-panel :deep(.el-card__body) { padding: 6px; }
.indicator-main-panel { min-width: 0; }
.indicator-main-panel .indicator-filter { grid-template-columns: minmax(230px, 1.5fr) repeat(2, minmax(140px, 1fr)) minmax(214px, auto); }
.panel-head {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 14px;
  border-bottom: 1px solid var(--line-soft);
  font-weight: 700;
  color: var(--ink);
}
.indicator-filter .filter-item input,
.indicator-filter .filter-item select {
  min-height: 38px;
}
.indicator-filter-actions {
  display: flex;
  align-items: end;
  gap: 8px;
  min-height: 62px;
}
.new-indicator-btn {
  margin-left: auto;
}
.indicator-panel-head {
  min-height: 54px;
}
.indicator-panel-head>div:first-child {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.indicator-panel-head>div:first-child span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
}
.indicator-status-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  color: #526177;
  font-size: 12px;
  font-weight: 400;
}
.indicator-status-summary span+span {
  position: relative;
}
.indicator-status-summary span+span::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 3px;
  width: 1px;
  height: 12px;
  background: var(--line);
}
.indicator-name {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--ink);
}
.indicator-name>span {
  color: #b98212;
}
.indicator-code {
  margin-top: 3px;
  color: #52708a;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}
.indicator-type {
  display: block;
  margin-bottom: 4px;
  color: #334155;
}
.caliber-cell {
  max-width: 320px;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.result-table-name {
  max-width: 180px;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}
.indicator-empty {
  display: grid;
  justify-items: center;
  gap: 7px;
}
.indicator-empty b {
  color: var(--ink);
}
.indicator-empty span {
  color: var(--muted);
}
.indicator-pagination {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  border-top: 1px solid var(--line-soft);
  color: var(--muted);
  font-size: 12px;
}
.indicator-pagination>div,
.indicator-pagination label {
  display: flex;
  align-items: center;
  gap: 7px;
}
.indicator-pagination select {
  width: 66px;
  padding: 5px 7px;
}
.indicator-sql-preview {
  max-height: 480px;
  margin-top: 14px;
}
.head-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.head-bar strong { color: var(--ink); }
.category-tree :deep(.el-tree-node__content) { height: 32px; }
.category-node-row { flex: 1 1 auto; display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; padding-right: 4px; }
.category-node-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.category-actions { visibility: hidden; display: inline-flex; align-items: center; gap: 2px; }
.category-tree :deep(.el-tree-node__content:hover) .category-actions { visibility: visible; }
.indicator-pagination { justify-content: flex-end; }
.indicator-more-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; padding: 4px 12px; }
.indicator-more-actions > span { margin-right: auto; color: var(--muted); font-size: 12px; }
.sql-dialog-meta { margin-bottom: 12px; }
.run-dialog-meta { margin-bottom: 12px; }
.run-sql-title { margin-top: 12px; }
.run-error { margin-top: 10px; }
.import-file-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.import-alert { margin-bottom: 8px; }
.import-errors { color: #c45656; font-size: 12px; }
@media (max-width: 720px) {
  .indicator-filter {
    min-width: 0;
    grid-template-columns: 1fr;
  }

  .indicator-filter-actions {
    min-height: 0;
    align-items: center;
  }
}
</style>
