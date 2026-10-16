<template>
  <div class="report-preview-panel">
    <!-- 业务日期参数设计 -->
    <div v-if="state.showParamDesign" class="param-design-block report-design">
      <div class="section-title-line"><h3>业务日期参数设计</h3></div>
      <div class="muted report-dialog-tip">核对自动识别的业务日期参数是否指对 SQL 里的位置。可切换类型或修改参数名。</div>
      <el-form label-width="120px" class="bizdate-form">
        <el-form-item label="业务日期类型">
          <el-select v-model="state.bizDateConfig.type" style="width:200px" @change="onBizTypeChange">
            <el-option value="balance" label="余额类（单日期）" />
            <el-option value="period" label="时段类（起止日期）" />
            <el-option value="none" label="无业务日期" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="state.bizDateConfig.type !== 'none'" label="业务日期字段">
          <el-input v-model="state.bizDateConfig.field" placeholder="例如 data_date" style="width:240px" />
        </el-form-item>
        <el-form-item v-if="state.bizDateConfig.type !== 'none'" label="起始日期参数">
          <el-input v-model="state.bizDateConfig.start_param" placeholder="例如 bgdate" style="width:240px" />
        </el-form-item>
        <el-form-item v-if="state.bizDateConfig.type === 'period'" label="结束日期参数">
          <el-input v-model="state.bizDateConfig.end_param" placeholder="例如 edate" style="width:240px" />
        </el-form-item>
      </el-form>

      <div v-if="state.bizDateConfig.type === 'none'" class="notice">无业务日期参数时，跑批时 SQL 不替换日期参数，时间仅作结果表标签。</div>

      <div v-if="state.bizDateConfig.type !== 'none'" class="bizdate-sample">
        <div class="sample-row">
          <el-form label-width="80px" inline class="sample-form">
            <el-form-item v-if="state.bizDateConfig.type === 'balance'" label="示例日期">
              <el-input v-model="state.sampleDate" style="width:160px" />
            </el-form-item>
            <template v-if="state.bizDateConfig.type === 'period'">
              <el-form-item label="示例开始">
                <el-input v-model="state.sampleStartDate" style="width:160px" />
              </el-form-item>
              <el-form-item label="示例结束">
                <el-input v-model="state.sampleEndDate" style="width:160px" />
              </el-form-item>
            </template>
          </el-form>
          <el-button :loading="state.resolveLoading" type="primary" @click="$emit('resolve-preview')">代入示例预览</el-button>
        </div>
        <div v-if="state.resolveError" class="notice">{{ state.resolveError }}</div>
      </div>

      <!-- SQL 预览：双列 / 单列布局 -->
      <div v-if="layout === 'side-by-side'" class="sql-preview-grid">
        <div class="sql-preview-col">
          <div class="section-title-line"><h4>原始 SQL（参数高亮）</h4></div>
          <pre class="sql" v-html="state.highlightedTemplate"></pre>
        </div>
        <div class="sql-preview-col">
          <div class="section-title-line"><h4>代入后 SQL</h4></div>
          <pre v-if="state.resolvedSql" class="sql">{{ state.resolvedSql }}</pre>
          <div v-else class="muted sql-placeholder">点"代入示例预览"查看替换后的 SQL</div>
        </div>
      </div>
      <div v-else class="sql-preview-grid" style="grid-template-columns: 1fr;">
        <div class="sql-preview-col">
          <div class="muted">替换后的 SQL：</div>
          <pre v-if="state.resolvedSql" class="sql">{{ state.resolvedSql }}</pre>
          <div v-else class="muted sql-placeholder">点"代入示例预览"查看替换后的 SQL</div>
        </div>
      </div>
    </div>

    <!-- 字段设计：7 列（字段 / 业务名称 / 角色 / 数据类型 / 日期 / 机构 / 可筛选） -->
    <div class="section-title-line field-design-title"><h3>字段设计</h3></div>
    <div class="muted report-dialog-tip">{{ fieldTip }}</div>
    <el-table :data="state.fieldList" size="small" border max-height="420" empty-text="暂无字段">
      <el-table-column label="字段" min-width="140">
        <template #default="{ row }">
          <b>{{ row.field_name }}</b>
          <div class="muted">{{ row.data_type }}</div>
        </template>
      </el-table-column>
      <el-table-column label="业务名称" min-width="180">
        <template #default="{ row }"><el-input v-model="row.alias" /></template>
      </el-table-column>
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-select v-model="row.role" size="small" style="width:100%">
            <el-option value="dimension" label="维度" />
            <el-option value="measure" label="度量" />
            <el-option value="normal" label="普通" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="数据类型" min-width="140">
        <template #default="{ row }"><el-input v-model="row.data_type" /></template>
      </el-table-column>
      <el-table-column label="日期字段" width="100">
        <template #default="{ row }"><el-checkbox v-model="row.is_date" /></template>
      </el-table-column>
      <el-table-column label="机构字段" width="100">
        <template #default="{ row }"><el-checkbox v-model="row.is_org" /></template>
      </el-table-column>
      <el-table-column label="可筛选" width="90">
        <template #default="{ row }"><el-checkbox v-model="row.filterable" /></template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export type PreviewFieldRow = {
  field_name: string
  alias: string
  role: string
  data_type: string
  is_date: boolean
  is_org: boolean
  filterable: boolean
}

export type ImportPanelState = {
  bizDateConfig: { type: string; field: string; start_param: string; end_param: string }
  showParamDesign: boolean
  sampleDate: string
  sampleStartDate: string
  sampleEndDate: string
  resolveLoading: boolean
  resolveError: string
  highlightedTemplate: string
  resolvedSql: string
  fieldList: PreviewFieldRow[]
}

export default defineComponent({
  name: 'ReportImportPreviewPanel',
  props: {
    state: { type: Object as () => ImportPanelState, required: true },
    layout: { type: String as () => 'side-by-side' | 'single', default: 'side-by-side' },
    fieldTip: { type: String, default: '确认字段角色和业务属性。' },
  },
  emits: ['toggle-param-design', 'biz-type-change', 'resolve-preview'],
  setup(_props, { emit }) {
    function onBizTypeChange() {
      emit('biz-type-change')
      emit('toggle-param-design') // 通知父级有类型变更，父级可清 resolvedSql
    }
    return { onBizTypeChange }
  },
})
</script>

<style scoped>
.report-design { display: grid; gap: 12px; }
.param-design-block { display: grid; gap: 12px; }
.bizdate-form { margin-top: 8px; }
.bizdate-sample { margin-top: 4px; }
.sample-row { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.sample-form { flex: 1; min-width: 0; }
.sample-form :deep(.el-form-item) { margin-bottom: 0; }
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
</style>
