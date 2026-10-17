<template>
  <div class="page report-list-page">
    <div class="page-head">
      <div><h1>系统报表导入</h1><div class="desc">将 RP_REPORT 里的报表解析为指标系统的数据模型，选中后即可基于报表 SQL 构建指标。报表数据来自业务数据源。</div></div>
      <div class="actions">
        <el-button v-if="showBack" @click="$emit('back')">返回模型管理</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-card shadow="never" class="report-card">
      <template #header>
        <div class="report-toolbar">
          <strong class="report-toolbar-title">可导入报表</strong>
          <el-tag type="info" size="small">{{ total }} 张</el-tag>
          <div class="report-search"><el-input v-model="keyword" placeholder="搜索报表名称、ID" clearable @keyup.enter="queryReports" /></div>
          <el-button type="primary" size="small" @click="queryReports">查询</el-button>
          <el-button
            type="primary"
            size="small"
            :disabled="!selectedReports.length"
            :loading="batchImporting"
            @click="confirmBatchImport"
          >
            批量导入{{ selectedReports.length ? `（${selectedReports.length}）` : '' }}
          </el-button>
        </div>
      </template>

      <el-table :data="reportList" v-loading="loading" size="small" empty-text="暂无报表" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="44" :selectable="canSelectRow" />
        <el-table-column prop="reptid" label="报表ID" width="96" />
        <el-table-column prop="reptna" label="报表名称" min-width="240" show-overflow-tooltip />
        <el-table-column prop="fieldCount" label="字段数" width="80" />
        <el-table-column label="业务日期" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.bizDateType === 'balance'" size="small">余额类</el-tag>
            <el-tag v-else-if="row.bizDateType === 'period'" size="small" type="warning">时段类</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <el-tag :type="row.imported ? 'success' : 'info'" size="small">{{ row.imported ? '已导入' : '未导入' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button v-if="!row.imported" type="primary" size="small" @click="openImport(row)">导入为数据模型</el-button>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total" class="report-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="load"
          @size-change="load"
        />
      </div>
    </el-card>

    <el-dialog v-model="importOpen" :title="importing ? `导入为数据模型：${importing.reptna}` : '导入为数据模型'" width="960px" append-to-body :close-on-click-modal="false">
      <div v-if="importing">
        <div class="report-dialog-meta">
          <span class="muted">报表 ID：{{ importing.reptid }} · 字段 {{ importing.fieldCount }} 个</span>
          <el-button v-if="previewInfo" text type="primary" @click="showParamDesign = !showParamDesign">
            {{ showParamDesign ? '收起参数设计' : '展开参数设计' }}
          </el-button>
        </div>
        <div v-if="previewError" class="notice report-preview-error">{{ previewError }}</div>

        <!-- 业务日期参数设计 + 字段设计（公共组件） -->
        <ReportImportPreviewPanel
          v-if="previewInfo"
          :state="reportPanelState"
          layout="side-by-side"
          field-tip="确认字段角色和业务属性。列表包含 RP_TITLE 登记的输出字段和可选块里的筛选参数字段。"
          @biz-type-change="onBizDateTypeChange"
          @resolve-preview="resolvePreview"
        />
      </div>
      <template #footer>
        <el-button @click="closeImport">取消</el-button>
        <el-button type="primary" :loading="importingReport" @click="doImport">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入确认对话框 -->
    <el-dialog v-model="batchConfirmOpen" title="批量导入为数据模型" width="640px" append-to-body :close-on-click-modal="false">
      <div class="muted report-dialog-tip">
        将对以下 {{ selectedReports.length }} 张报表执行批量导入，自动识别业务日期与字段配置，不会弹出参数/字段设计界面。
        个别报表的字段/参数不准时，可在数据模型管理页修改，或对失败项使用单条"导入为数据模型"细调。
      </div>
      <el-table :data="selectedReports" size="small" border max-height="320" empty-text="未选择">
        <el-table-column prop="reptid" label="报表ID" width="96" />
        <el-table-column prop="reptna" label="报表名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="业务日期" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.bizDateType === 'balance'" size="small">余额类</el-tag>
            <el-tag v-else-if="row.bizDateType === 'period'" size="small" type="warning">时段类</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="batchConfirmOpen = false">取消</el-button>
        <el-button type="primary" :loading="batchImporting" @click="doBatchImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入结果对话框 -->
    <el-dialog v-model="batchResultOpen" title="批量导入结果" width="720px" append-to-body>
      <div v-if="batchResult" class="batch-result">
        <div class="batch-result-summary">
          <el-tag type="success">成功 {{ batchResult.success.length }}</el-tag>
          <el-tag type="danger" v-if="batchResult.failed.length">失败 {{ batchResult.failed.length }}</el-tag>
        </div>
        <div v-if="batchResult.success.length" class="section-title-line"><h4>导入成功</h4></div>
        <el-table v-if="batchResult.success.length" :data="batchResult.success" size="small" border max-height="200">
          <el-table-column prop="reptid" label="报表ID" width="96" />
          <el-table-column prop="reptna" label="报表名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="reptna" label="模型名称" min-width="160" show-overflow-tooltip />
        </el-table>
        <div v-if="batchResult.failed.length" class="section-title-line batch-failed-title"><h4>导入失败</h4></div>
        <el-table v-if="batchResult.failed.length" :data="batchResult.failed" size="small" border max-height="240">
          <el-table-column prop="reptid" label="报表ID" width="96" />
          <el-table-column prop="reptna" label="报表名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="error" label="失败原因" min-width="240" show-overflow-tooltip />
        </el-table>
      </div>
      <template #footer>
        <el-button type="primary" @click="closeBatchResult">关闭</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script lang="ts">
import { computed, defineComponent, inject, onMounted, reactive, ref } from 'vue'
import ReportImportPreviewPanel from './ReportImportPreviewPanel.vue'
import { api as requestApi, jsonBody as toJsonBody } from '../api'
import type { BatchImportResult, PageResult as PageResultT, ReportInfo, ReportPreviewResult, ResolvePreviewResult } from '../types'

const useNotify = () => inject<(message: string) => void>('notify', () => undefined)

function highlightSqlParams(sql: string): string {
  if (!sql) return ''
  let result = sql
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  result = result.replace(/\[[^\]]*\]/g, (match) => `<span class="sql-block">${match}</span>`)
  result = result.replace(/:([A-Za-z_][A-Za-z0-9_]*)/g, '<span class="sql-param">:$1</span>')
  return result
}

export default defineComponent({
  name: 'ReportImportList',
  components: { ReportImportPreviewPanel },
  props: {
    showBack: { type: Boolean, default: false },
  },
  emits: ['reload', 'back'],
  setup(_props, { emit }) {
    const notify = useNotify()

    // 报表列表与分页
    const reportList = ref<ReportInfo[]>([])
    const loading = ref(false)
    const keyword = ref('')
    const total = ref(0)
    const pageSize = ref(10)
    const currentPage = ref(1)

    // 单条报表导入与预览
    const importOpen = ref(false)
    const importing = ref<ReportInfo | null>(null)
    const previewInfo = ref<ReportPreviewResult | null>(null)
    const previewLoading = ref(false)
    const previewError = ref('')
    const importingReport = ref(false)

    const bizDateConfig = reactive<{ type: string; field: string; start_param: string; end_param: string }>({
      type: 'none',
      field: '',
      start_param: '',
      end_param: '',
    })
    const fieldList = ref<Array<{ field_name: string; alias: string; role: string; data_type: string; is_date: boolean; is_org: boolean; filterable: boolean }>>([])
    const highlightedTemplate = computed(() => highlightSqlParams(previewInfo.value?.templateSql || ''))
    const sampleDate = ref('2026-08-20')
    const sampleStartDate = ref('2026-08-01')
    const sampleEndDate = ref('2026-08-31')
    const resolvedSql = ref('')
    const resolveLoading = ref(false)
    const resolveError = ref('')
    const showParamDesign = ref(false)

    // 批量导入与结果
    const selectedReports = ref<ReportInfo[]>([])
    const batchConfirmOpen = ref(false)
    const batchImporting = ref(false)
    const batchResultOpen = ref(false)
    const batchResult = ref<BatchImportResult | null>(null)

    // 报表列表操作
    async function load() {
      loading.value = true
      try {
        const result = await requestApi<PageResultT<ReportInfo>>(
          `/api/reports?page=${currentPage.value}&pageSize=${pageSize.value}&keyword=${encodeURIComponent(keyword.value)}`
        )
        reportList.value = result.items
        total.value = result.total
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        loading.value = false
      }
    }

    function queryReports() {
      currentPage.value = 1
      load()
    }

    // 单条报表导入操作
    function resetDesign() {
      bizDateConfig.type = 'none'
      bizDateConfig.field = ''
      bizDateConfig.start_param = ''
      bizDateConfig.end_param = ''
      fieldList.value = []
      resolvedSql.value = ''
      resolveError.value = ''
      showParamDesign.value = false
    }

    function fillDesignFromPreview(info: ReportPreviewResult) {
      const biz = info.bizDate
      if (biz && biz.type) {
        bizDateConfig.type = biz.type
        bizDateConfig.field = biz.field || ''
        bizDateConfig.start_param = biz.start_param || ''
        bizDateConfig.end_param = biz.end_param || ''
      } else {
        bizDateConfig.type = 'none'
        bizDateConfig.field = ''
        bizDateConfig.start_param = ''
        bizDateConfig.end_param = ''
      }
      fieldList.value = info.fields.map((f) => ({
        field_name: f.field_name,
        alias: f.alias,
        role: f.role,
        data_type: f.data_type,
        is_date: f.is_date,
        is_org: false,
        filterable: true,
      }))
    }

    function openImport(report: ReportInfo) {
      importing.value = report
      importingReport.value = false
      previewError.value = ''
      previewInfo.value = null
      resetDesign()
      importOpen.value = true
      // 打开即自动加载预览
      preview()
    }
    function closeImport() {
      importOpen.value = false
      importing.value = null
      previewInfo.value = null
      previewError.value = ''
      resetDesign()
    }

    async function preview() {
      if (!importing.value) return
      previewLoading.value = true
      previewError.value = ''
      try {
        previewInfo.value = await requestApi<ReportPreviewResult>(`/api/reports/${importing.value.reptid}/previews`, {
          method: 'POST',
          body: toJsonBody({
            reptid: importing.value.reptid,
            sampleDate: sampleDate.value,
            sampleStartDate: sampleStartDate.value,
            sampleEndDate: sampleEndDate.value,
          }),
        })
        if (previewInfo.value) {
          fillDesignFromPreview(previewInfo.value)
        }
      } catch (error) {
        previewError.value = error instanceof Error ? error.message : String(error)
      } finally {
        previewLoading.value = false
      }
    }

    function onBizDateTypeChange() {
      resolvedSql.value = ''
      resolveError.value = ''
      if (bizDateConfig.type === 'balance') {
        bizDateConfig.end_param = ''
      }
    }

    async function resolvePreview() {
      if (!importing.value) return
      resolveLoading.value = true
      resolveError.value = ''
      try {
        const result = await requestApi<ResolvePreviewResult>(`/api/reports/${importing.value.reptid}/resolve-preview`, {
          method: 'POST',
          body: toJsonBody({
            reptid: importing.value.reptid,
            bizDateType: bizDateConfig.type,
            bizDateField: bizDateConfig.field,
            bizDateStartParam: bizDateConfig.start_param,
            bizDateEndParam: bizDateConfig.end_param,
            sampleDate: sampleDate.value,
            sampleStartDate: sampleStartDate.value,
            sampleEndDate: sampleEndDate.value,
          }),
        })
        resolvedSql.value = result.sqlText
      } catch (error) {
        resolveError.value = error instanceof Error ? error.message : String(error)
      } finally {
        resolveLoading.value = false
      }
    }

    async function doImport() {
      if (!importing.value) return
      if (!previewInfo.value) {
        notify('请先点击"解析预览"加载字段和业务日期参数')
        return
      }
      importingReport.value = true
      try {
        await requestApi('/api/models', {
          method: 'POST',
          body: toJsonBody({
            reptid: importing.value.reptid,
            fields: fieldList.value.map((f) => ({
              field_name: f.field_name,
              alias: f.alias,
              role: f.role,
              data_type: f.data_type,
              is_date: f.is_date,
              is_org: f.is_org,
              filterable: f.filterable,
            })),
            sampleDate: sampleDate.value,
            sampleStartDate: sampleStartDate.value,
            sampleEndDate: sampleEndDate.value,
          }),
        })
        notify(`报表「${importing.value.reptna}」已导入为数据模型`)
        closeImport()
        emit('reload')
        await load()
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        importingReport.value = false
      }
    }

    // 批量报表导入操作
    function canSelectRow(row: ReportInfo) {
      return !row.imported
    }
    function onSelectionChange(rows: ReportInfo[]) {
      selectedReports.value = rows
    }

    function confirmBatchImport() {
      if (!selectedReports.value.length) return
      batchResult.value = null
      batchConfirmOpen.value = true
    }

    async function doBatchImport() {
      if (!selectedReports.value.length) return
      batchImporting.value = true
      try {
        const result = await requestApi<BatchImportResult>('/api/reports/batch-import', {
          method: 'POST',
          body: toJsonBody({
            reptids: selectedReports.value.map((r) => r.reptid),
            sampleDate: sampleDate.value,
            sampleStartDate: sampleStartDate.value,
            sampleEndDate: sampleEndDate.value,
          }),
        })
        batchResult.value = result
        batchConfirmOpen.value = false
        batchResultOpen.value = true
        emit('reload')
        await load()
        // 清空选择（已导入的行会被 :selectable 禁掉）
        selectedReports.value = []
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        batchImporting.value = false
      }
    }

    function closeBatchResult() {
      batchResultOpen.value = false
      batchResult.value = null
    }

    // 预览面板状态映射
    const reportPanelState = reactive({
      bizDateConfig, showParamDesign,
      sampleDate, sampleStartDate, sampleEndDate,
      resolveLoading, resolveError,
      highlightedTemplate, resolvedSql,
      fieldList,
    })
    // 页面生命周期
    onMounted(load)

    // 模板绑定
    return {
      reportList, loading, keyword, total, pageSize, currentPage,
      importOpen, importing, previewInfo, previewLoading, previewError, importingReport,
      bizDateConfig, fieldList, sampleDate, sampleStartDate, sampleEndDate, resolvedSql, resolveLoading, resolveError, showParamDesign,
      selectedReports, batchConfirmOpen, batchImporting, batchResultOpen, batchResult,
      highlightedTemplate, reportPanelState,
      load, queryReports, openImport, closeImport, preview, onBizDateTypeChange, resolvePreview, doImport,
      canSelectRow, onSelectionChange, confirmBatchImport, doBatchImport, closeBatchResult,
    }
  },
})
</script>

<style scoped>
.report-card { box-shadow: var(--shadow); }
.report-toolbar { display: flex; align-items: center; gap: 10px; }
.report-toolbar-title { color: var(--ink); font-size: 14px; }
.report-search { margin-left: auto; width: 260px; }
.report-search :deep(.el-input) { width: 100%; }
.report-pagination { display: flex; justify-content: flex-end; padding-top: 12px; }
.report-dialog-meta { margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.report-dialog-tip { margin-bottom: 6px; }
.report-section { margin-bottom: 8px; }
.report-preview-error { margin-top: 10px; }

.batch-result { display: grid; gap: 12px; }
.batch-result-summary { display: flex; gap: 8px; align-items: center; }
.batch-failed-title { margin-top: 4px; }

.section-title-line { margin: 4px 0; }
.section-title-line h3,
.section-title-line h4 { margin: 0; font-size: 14px; border-left: 3px solid var(--brand); padding-left: 8px; color: var(--ink); }
.notice {
  background: #fef9c3;
  color: #713f12;
  border: 1px solid #fde047;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}
</style>
