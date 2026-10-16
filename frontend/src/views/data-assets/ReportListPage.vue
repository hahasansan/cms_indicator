<template>
  <div class="page report-list-page">
    <div class="page-head">
      <div><h1>报表列表</h1><div class="desc">将 RP_REPORT 里的报表解析为指标系统的数据模型，选中后即可基于报表 SQL 构建指标。报表数据来自业务数据源。</div></div>
      <div class="actions"><el-button @click="load">刷新</el-button></div>
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
          <el-button type="success" size="small" @click="openSqlImport">自定义 SQL 导入</el-button>
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

    <el-dialog v-model="sqlImportOpen" title="导入自定义 SQL 为数据模型" width="960px" append-to-body :close-on-click-modal="false">
      <div class="report-design">
        <div class="section-title-line"><h3>基本信息</h3></div>
        <el-form label-width="100px" class="sql-import-basic">
          <el-form-item label="模型编码" required><el-input v-model="sqlForm.code" placeholder="例如 SQL_CUSTOM_01" /></el-form-item>
          <el-form-item label="模型名称" required><el-input v-model="sqlForm.name" placeholder="例如 客户资产明细" /></el-form-item>
          <el-form-item label="业务模块"><el-input v-model="sqlForm.module" placeholder="例如 零售业务" /></el-form-item>
          <el-form-item label="负责人"><el-input v-model="sqlForm.owner" /></el-form-item>
          <el-form-item label="占位表名"><el-input v-model="sqlForm.tableName" placeholder="留空则自动按编码生成" /></el-form-item>
          <el-form-item label="模型描述"><el-input v-model="sqlForm.description" type="textarea" :rows="2" /></el-form-item>
        </el-form>
        <div class="section-title-line"><h3>SQL 模板</h3></div>
        <div class="muted report-dialog-tip">支持以下参数写法：<code>[:bgdate]</code> 单日期 / <code>[bgdate,edate]</code> 起止日期 / <code>:org_code</code> 具名绑定参数。</div>
        <el-input v-model="sqlForm.sqlText" type="textarea" :rows="8" placeholder="SELECT cust_id, ... FROM cust_account WHERE data_date = [:bgdate]" />

        <div v-if="sqlPreviewError" class="notice report-preview-error">{{ sqlPreviewError }}</div>
        <div v-if="sqlPreviewInfo" class="report-dialog-meta">
          <span class="muted">输出字段 {{ sqlPreviewInfo.fields.length }} 个</span>
          <el-button text type="primary" @click="showParamDesign_Sql = !showParamDesign_Sql">
            {{ showParamDesign_Sql ? '收起参数设计' : '展开参数设计' }}
          </el-button>
        </div>

        <!-- 业务日期参数设计 + 字段设计（公共组件） -->
        <ReportImportPreviewPanel
          v-if="sqlPreviewInfo"
          :state="sqlPanelState"
          layout="single"
          field-tip="角色 = 维度（分类字段）/ 度量（可计算数值）/ 普通（原始字段）；默认根据数据类型推断，可手动调整。"
          @biz-type-change="onBizDateTypeChange_Sql"
          @resolve-preview="resolvePreview_Sql"
        />
      </div>
      <template #footer>
        <el-button @click="closeSqlImport">取消</el-button>
        <el-button type="primary" :loading="previewLoading_Sql" @click="preview_Sql">解析预览</el-button>
        <el-button type="primary" :disabled="!sqlPreviewInfo" :loading="sqlImporting" @click="doImportSql">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, inject, onMounted, reactive, ref, watch } from 'vue'
import ReportImportPreviewPanel from '../../components/ReportImportPreviewPanel.vue'
import { api as requestApi, jsonBody as toJsonBody } from '../../api'
import type { BatchImportResult, BootstrapData, PageResult as PageResultT, ReportInfo, ReportPreviewResult, ResolvePreviewResult } from '../../types'

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
  name: 'ReportListPage',
  components: { ReportImportPreviewPanel },
  props: { data: { type: Object as () => BootstrapData, required: true } },
  emits: ['reload'],
  setup(_props, { emit }) {
    const notify = useNotify()
    const reports = ref<ReportInfo[]>([])
    const reportList = ref<ReportInfo[]>([])
    const loading = ref(false)
    const keyword = ref('')
    const total = ref(0)
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
    const sampleDate = ref('2026-08-20')
    const sampleStartDate = ref('2026-08-01')
    const sampleEndDate = ref('2026-08-31')
    const resolvedSql = ref('')
    const resolveLoading = ref(false)
    const resolveError = ref('')
    const showParamDesign = ref(false)

    // 批量导入相关
    const selectedReports = ref<ReportInfo[]>([])
    const batchConfirmOpen = ref(false)
    const batchImporting = ref(false)
    const batchResultOpen = ref(false)
    const batchResult = ref<BatchImportResult | null>(null)

    const highlightedTemplate = computed(() => highlightSqlParams(previewInfo.value?.templateSql || ''))

    const pageSize = ref(10)
    const currentPage = ref(1)

    async function load() {
      loading.value = true
      try {
        const result = await requestApi<PageResultT<ReportInfo>>(
          `/api/reports?page=${currentPage.value}&pageSize=${pageSize.value}&keyword=${encodeURIComponent(keyword.value)}`
        )
        reportList.value = result.items
        total.value = result.total
        // 保留 reports 供历史兼容：合并当前页 items，避免旧引用报错
        reports.value = reportList.value
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

    // 批量导入：选择控制
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

    // —— 自定义 SQL 导入（_Sql 后缀，与报表导入 state 区分）——
    const sqlImportOpen = ref(false)
    const sqlImporting = ref(false)
    const previewLoading_Sql = ref(false)
    const sqlPreviewError = ref('')
    const showParamDesign_Sql = ref(true)
    const sqlForm = reactive({ code: '', name: '', module: '', owner: '', tableName: '', description: '', sqlText: '' })
    const bizDateConfig_Sql = reactive<{ type: string; field: string; start_param: string; end_param: string }>({
      type: 'none', field: '', start_param: '', end_param: '',
    })
    const fieldList_Sql = ref<Array<{ field_name: string; alias: string; role: string; data_type: string; is_date: boolean; is_org: boolean; filterable: boolean }>>([])
    const sqlPreviewInfo = ref<ReportPreviewResult | null>(null)
    const sampleDate_Sql = ref('2026-08-20')
    const sampleStartDate_Sql = ref('2026-08-01')
    const sampleEndDate_Sql = ref('2026-08-31')
    const resolvedSql_Sql = ref('')
    const resolveLoading_Sql = ref(false)
    const resolveError_Sql = ref('')

    function openSqlImport() {
      sqlForm.code = ''; sqlForm.name = ''; sqlForm.module = ''; sqlForm.owner = ''; sqlForm.tableName = ''; sqlForm.description = ''; sqlForm.sqlText = ''
      bizDateConfig_Sql.type = 'none'; bizDateConfig_Sql.field = ''; bizDateConfig_Sql.start_param = ''; bizDateConfig_Sql.end_param = ''
      fieldList_Sql.value = []; sqlPreviewInfo.value = null; sqlPreviewError.value = ''; resolveError_Sql.value = ''; resolvedSql_Sql.value = ''
      sampleDate_Sql.value = '2026-08-20'; sampleStartDate_Sql.value = '2026-08-01'; sampleEndDate_Sql.value = '2026-08-31'
      showParamDesign_Sql.value = true; sqlImportOpen.value = true
    }
    function closeSqlImport() { sqlImportOpen.value = false }
    function fillDesignFromPreview_Sql(info: ReportPreviewResult) {
      const biz = info.bizDate
      if (biz && biz.type) {
        bizDateConfig_Sql.type = biz.type
        bizDateConfig_Sql.field = biz.field || ''
        bizDateConfig_Sql.start_param = biz.start_param || ''
        bizDateConfig_Sql.end_param = biz.end_param || ''
      } else {
        bizDateConfig_Sql.type = 'none'; bizDateConfig_Sql.field = ''; bizDateConfig_Sql.start_param = ''; bizDateConfig_Sql.end_param = ''
      }
      fieldList_Sql.value = info.fields.map((f) => ({
        field_name: f.field_name, alias: f.alias, role: f.role, data_type: f.data_type, is_date: f.is_date, is_org: false, filterable: true,
      }))
    }
    async function preview_Sql() {
      if (!sqlForm.sqlText.trim()) { notify('请先填写自定义 SQL 模板'); return }
      previewLoading_Sql.value = true; sqlPreviewError.value = ''
      try {
        const r = await requestApi<ReportPreviewResult>('/api/models/sql-preview', {
          method: 'POST',
          body: toJsonBody({
            sqlText: sqlForm.sqlText,
            sampleDate: sampleDate_Sql.value,
            sampleStartDate: sampleStartDate_Sql.value,
            sampleEndDate: sampleEndDate_Sql.value,
          }),
        })
        sqlPreviewInfo.value = r
        fillDesignFromPreview_Sql(r)
        resolvedSql_Sql.value = r.sqlText
      } catch (error) {
        sqlPreviewError.value = error instanceof Error ? error.message : String(error)
      } finally { previewLoading_Sql.value = false }
    }
    function onBizDateTypeChange_Sql() {
      resolvedSql_Sql.value = ''; resolveError_Sql.value = ''
      if (bizDateConfig_Sql.type === 'balance') bizDateConfig_Sql.end_param = ''
    }
    async function resolvePreview_Sql() {
      resolveLoading_Sql.value = true; resolveError_Sql.value = ''
      try {
        const r = await requestApi<ResolvePreviewResult>('/api/models/sql-resolve-preview', {
          method: 'POST',
          body: toJsonBody({
            sqlText: sqlForm.sqlText,
            bizDateType: bizDateConfig_Sql.type,
            bizDateField: bizDateConfig_Sql.field,
            bizDateStartParam: bizDateConfig_Sql.start_param,
            bizDateEndParam: bizDateConfig_Sql.end_param,
            sampleDate: sampleDate_Sql.value,
            sampleStartDate: sampleStartDate_Sql.value,
            sampleEndDate: sampleEndDate_Sql.value,
          }),
        })
        resolvedSql_Sql.value = r.sqlText
      } catch (error) {
        resolveError_Sql.value = error instanceof Error ? error.message : String(error)
      } finally { resolveLoading_Sql.value = false }
    }
    async function doImportSql() {
      if (!sqlForm.code.trim() || !sqlForm.name.trim()) { notify('请填写模型编码和模型名称'); return }
      if (!sqlPreviewInfo.value || !fieldList_Sql.value.length) { notify('请先点击「解析预览」生成字段列表'); return }
      sqlImporting.value = true
      try {
        await requestApi('/api/models', {
          method: 'POST',
          body: toJsonBody({
            code: sqlForm.code.trim(), name: sqlForm.name.trim(),
            module: sqlForm.module.trim() || '自定义SQL',
            owner: sqlForm.owner.trim() || '当前用户',
            description: sqlForm.description,
            tableName: sqlForm.tableName.trim(),
            sqlText: sqlForm.sqlText,
            fields: fieldList_Sql.value.map((f) => ({
              field_name: f.field_name, alias: f.alias, role: f.role, data_type: f.data_type,
              is_date: f.is_date, is_org: f.is_org, filterable: f.filterable,
            })),
            sampleDate: sampleDate_Sql.value, sampleStartDate: sampleStartDate_Sql.value, sampleEndDate: sampleEndDate_Sql.value,
          }),
        })
        notify(`模型「${sqlForm.name}」已创建`)
        closeSqlImport()
        emit('reload')
        await load()
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally { sqlImporting.value = false }
    }

    onMounted(load)

    const reportPanelState = reactive({
      bizDateConfig, showParamDesign,
      sampleDate, sampleStartDate, sampleEndDate,
      resolveLoading, resolveError,
      highlightedTemplate, resolvedSql,
      fieldList,
    })
    const sqlPanelState = reactive({
      bizDateConfig: bizDateConfig_Sql,
      showParamDesign: showParamDesign_Sql,
      sampleDate: sampleDate_Sql, sampleStartDate: sampleStartDate_Sql, sampleEndDate: sampleEndDate_Sql,
      resolveLoading: resolveLoading_Sql, resolveError: resolveError_Sql,
      highlightedTemplate: '', resolvedSql: resolvedSql_Sql,
      fieldList: fieldList_Sql,
    })

    return {
      reports, reportList, loading, keyword, total, pageSize, currentPage,
      importOpen, importing, previewInfo, previewLoading, previewError, importingReport,
      bizDateConfig, fieldList, sampleDate, sampleStartDate, sampleEndDate, resolvedSql, resolveLoading, resolveError, showParamDesign,
      selectedReports, batchConfirmOpen, batchImporting, batchResultOpen, batchResult,
      highlightedTemplate, reportPanelState, sqlPanelState,
      sqlImportOpen, sqlImporting, previewLoading_Sql, sqlPreviewError, showParamDesign_Sql,
      sqlForm, bizDateConfig_Sql, fieldList_Sql, sqlPreviewInfo,
      sampleDate_Sql, sampleStartDate_Sql, sampleEndDate_Sql, resolvedSql_Sql, resolveLoading_Sql, resolveError_Sql,
      load, queryReports, openImport, closeImport, preview, onBizDateTypeChange, resolvePreview, doImport,
      canSelectRow, onSelectionChange, confirmBatchImport, doBatchImport, closeBatchResult,
      openSqlImport, closeSqlImport, preview_Sql, onBizDateTypeChange_Sql, resolvePreview_Sql, doImportSql,
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

.report-design { display: grid; gap: 12px; }
.param-design-block { display: grid; gap: 12px; }
.bizdate-form { margin-top: 8px; }
.bizdate-sample { margin-top: 4px; }
.sample-row { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.sample-form { flex: 1; min-width: 0; }
.sample-form :deep(.el-form-item) { margin-bottom: 0; }

.sql-preview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }
.sql-preview-col { display: grid; gap: 6px; }
.sql-placeholder { padding: 12px; border: 1px dashed var(--border); border-radius: 4px; text-align: center; }
pre.sql {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
pre.sql :deep(.sql-param) { color: #60a5fa; font-weight: 600; }
pre.sql :deep(.sql-block) { color: #64748b; }

.field-design-title { margin-top: 8px; }
.field-design-title + .report-dialog-tip { margin-bottom: 8px; }

.batch-result { display: grid; gap: 12px; }
.batch-result-summary { display: flex; gap: 8px; align-items: center; }
.batch-failed-title { margin-top: 4px; }

/* 自定义 SQL Dialog：基本信息 2 列栅格 + 小节标题样式 */
.sql-import-basic { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
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
