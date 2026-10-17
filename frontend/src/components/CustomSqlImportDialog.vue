<template>
  <el-dialog
    v-model="dialogOpen"
    title="导入自定义 SQL 为数据模型"
    width="960px"
    append-to-body
    :close-on-click-modal="false"
  >
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

      <div v-if="previewError" class="notice report-preview-error">{{ previewError }}</div>
      <div v-if="previewInfo" class="report-dialog-meta">
        <span class="muted">输出字段 {{ previewInfo.fields.length }} 个</span>
        <el-button text type="primary" @click="showParamDesign = !showParamDesign">
          {{ showParamDesign ? '收起参数设计' : '展开参数设计' }}
        </el-button>
      </div>

      <ReportImportPreviewPanel
        v-if="previewInfo"
        :state="panelState"
        layout="single"
        field-tip="角色 = 维度（分类字段）/ 度量（可计算数值）/ 普通（原始字段）；默认根据数据类型推断，可手动调整。"
        @biz-type-change="onBizDateTypeChange"
        @resolve-preview="resolvePreview"
      />
    </div>
    <template #footer>
      <el-button @click="dialogOpen = false">取消</el-button>
      <el-button type="primary" :loading="previewLoading" @click="preview">解析预览</el-button>
      <el-button type="primary" :disabled="!previewInfo" :loading="importing" @click="doImport">确认导入</el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts">
import { computed, defineComponent, inject, reactive, ref, watch } from 'vue'
import ReportImportPreviewPanel from './ReportImportPreviewPanel.vue'
import { api as requestApi, jsonBody as toJsonBody } from '../api'
import type { ReportPreviewResult, ResolvePreviewResult } from '../types'

const useNotify = () => inject<(message: string) => void>('notify', () => undefined)

export default defineComponent({
  name: 'CustomSqlImportDialog',
  components: { ReportImportPreviewPanel },
  props: {
    modelValue: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'reload'],
  setup(props, { emit }) {
    const notify = useNotify()
    const dialogOpen = computed({
      get: () => props.modelValue,
      set: (value: boolean) => emit('update:modelValue', value),
    })
    const importing = ref(false)
    const previewLoading = ref(false)
    const previewError = ref('')
    const showParamDesign = ref(true)
    const sqlForm = reactive({ code: '', name: '', module: '', owner: '', tableName: '', description: '', sqlText: '' })
    const bizDateConfig = reactive<{ type: string; field: string; start_param: string; end_param: string }>({
      type: 'none', field: '', start_param: '', end_param: '',
    })
    const fieldList = ref<Array<{ field_name: string; alias: string; role: string; data_type: string; is_date: boolean; is_org: boolean; filterable: boolean }>>([])
    const previewInfo = ref<ReportPreviewResult | null>(null)
    const sampleDate = ref('2026-08-20')
    const sampleStartDate = ref('2026-08-01')
    const sampleEndDate = ref('2026-08-31')
    const resolvedSql = ref('')
    const resolveLoading = ref(false)
    const resolveError = ref('')

    function reset() {
      sqlForm.code = ''
      sqlForm.name = ''
      sqlForm.module = ''
      sqlForm.owner = ''
      sqlForm.tableName = ''
      sqlForm.description = ''
      sqlForm.sqlText = ''
      bizDateConfig.type = 'none'
      bizDateConfig.field = ''
      bizDateConfig.start_param = ''
      bizDateConfig.end_param = ''
      fieldList.value = []
      previewInfo.value = null
      previewError.value = ''
      resolveError.value = ''
      resolvedSql.value = ''
      sampleDate.value = '2026-08-20'
      sampleStartDate.value = '2026-08-01'
      sampleEndDate.value = '2026-08-31'
      showParamDesign.value = true
    }

    function fillDesignFromPreview(info: ReportPreviewResult) {
      const biz = info.bizDate
      if (biz?.type) {
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
      fieldList.value = info.fields.map((field) => ({
        field_name: field.field_name,
        alias: field.alias,
        role: field.role,
        data_type: field.data_type,
        is_date: field.is_date,
        is_org: false,
        filterable: true,
      }))
    }

    async function preview() {
      if (!sqlForm.sqlText.trim()) {
        notify('请先填写自定义 SQL 模板')
        return
      }
      previewLoading.value = true
      previewError.value = ''
      try {
        const result = await requestApi<ReportPreviewResult>('/api/models/sql-preview', {
          method: 'POST',
          body: toJsonBody({
            sqlText: sqlForm.sqlText,
            sampleDate: sampleDate.value,
            sampleStartDate: sampleStartDate.value,
            sampleEndDate: sampleEndDate.value,
          }),
        })
        previewInfo.value = result
        fillDesignFromPreview(result)
        resolvedSql.value = result.sqlText
      } catch (error) {
        previewError.value = error instanceof Error ? error.message : String(error)
      } finally {
        previewLoading.value = false
      }
    }

    function onBizDateTypeChange() {
      resolvedSql.value = ''
      resolveError.value = ''
      if (bizDateConfig.type === 'balance') bizDateConfig.end_param = ''
    }

    async function resolvePreview() {
      resolveLoading.value = true
      resolveError.value = ''
      try {
        const result = await requestApi<ResolvePreviewResult>('/api/models/sql-resolve-preview', {
          method: 'POST',
          body: toJsonBody({
            sqlText: sqlForm.sqlText,
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
      if (!sqlForm.code.trim() || !sqlForm.name.trim()) {
        notify('请填写模型编码和模型名称')
        return
      }
      if (!previewInfo.value || !fieldList.value.length) {
        notify('请先点击「解析预览」生成字段列表')
        return
      }
      importing.value = true
      try {
        await requestApi('/api/models', {
          method: 'POST',
          body: toJsonBody({
            code: sqlForm.code.trim(),
            name: sqlForm.name.trim(),
            module: sqlForm.module.trim() || '自定义SQL',
            owner: sqlForm.owner.trim() || '当前用户',
            description: sqlForm.description,
            tableName: sqlForm.tableName.trim(),
            sqlText: sqlForm.sqlText,
            fields: fieldList.value.map((field) => ({
              field_name: field.field_name,
              alias: field.alias,
              role: field.role,
              data_type: field.data_type,
              is_date: field.is_date,
              is_org: field.is_org,
              filterable: field.filterable,
            })),
            sampleDate: sampleDate.value,
            sampleStartDate: sampleStartDate.value,
            sampleEndDate: sampleEndDate.value,
          }),
        })
        notify(`模型「${sqlForm.name}」已创建`)
        dialogOpen.value = false
        emit('reload')
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        importing.value = false
      }
    }

    watch(() => props.modelValue, (open) => {
      if (open) reset()
    })

    const panelState = reactive({
      bizDateConfig,
      showParamDesign,
      sampleDate,
      sampleStartDate,
      sampleEndDate,
      resolveLoading,
      resolveError,
      highlightedTemplate: '',
      resolvedSql,
      fieldList,
    })

    return {
      dialogOpen,
      importing,
      previewLoading,
      previewError,
      showParamDesign,
      sqlForm,
      previewInfo,
      panelState,
      preview,
      onBizDateTypeChange,
      resolvePreview,
      doImport,
    }
  },
})
</script>

<style scoped>
.report-design { display: grid; gap: 12px; }
.report-dialog-tip { margin-bottom: 6px; }
.report-preview-error { margin-top: 10px; }
.report-dialog-meta { margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.section-title-line { margin: 4px 0; }
.section-title-line h3 { margin: 0; font-size: 14px; border-left: 3px solid var(--brand); padding-left: 8px; color: var(--ink); }
.sql-import-basic { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.notice {
  background: #fef9c3;
  color: #713f12;
  border: 1px solid #fde047;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}
</style>
