<template>
    <ReportImportList
      v-if="showReportList"
      show-back
      @reload="emitReload"
      @back="showReportList = false"
    />
    <div v-else class="page data-list-page">
      <div class="page-head">
        <div><h1>模型管理</h1><div class="desc">按业务域管理数据模型，维护字段口径、角色、属性、样例数据、引用指标和上下游血缘。</div></div>
        <div class="actions">
          <el-button @click="showReportList = true">将系统报表导入</el-button>
          <el-button type="primary" @click="sqlImportOpen = true">自定义 SQL 导入</el-button>
        </div>
      </div>

      <div class="model-main-layout data-list-main">
        <el-card shadow="never" class="model-domain">
          <template #header><div class="head-bar"><strong>模型目录</strong><el-tag type="info" size="small">{{ data.models.length }}</el-tag></div></template>
          <button class="domain-node" :class="{active: selectedModule==='all'}" @click="selectModule('all')"><span>全部模型</span><b>{{ data.models.length }}</b></button>
          <button v-for="moduleName in modules" :key="moduleName" class="domain-node" :class="{active: selectedModule===moduleName}" @click="selectModule(moduleName)">
            <span>{{ moduleName }}</span><b>{{ data.models.filter(m => (m.module || '未分组') === moduleName).length }}</b>
          </button>
        </el-card>

        <div class="model-main-panel data-list-panel">
          <el-card shadow="never">
            <template #header>
              <div class="model-toolbar">
                <div class="model-search"><el-input v-model="keyword" placeholder="搜索模型名称、编码、表名" clearable @keyup.enter="query" /></div>
                <el-button type="primary" size="small" :loading="loading" @click="query">查询</el-button>
                <span class="muted">共 {{ total }} 个模型</span>
              </div>
            </template>
            <el-table :data="modelList" v-loading="loading" size="small" highlight-current-row empty-text="暂无模型" @row-click="openDetail">
              <el-table-column label="模型" min-width="200">
                <template #default="{ row }"><b>{{ row.name }}</b><div class="muted">{{ row.code }}</div></template>
              </el-table-column>
              <el-table-column prop="table" label="物理表" min-width="170" show-overflow-tooltip />
              <el-table-column prop="module" label="业务域" width="110" />
              <el-table-column label="字段数" width="120">
                <template #default="{ row }"><span>维度 {{ fieldCounts(row)[0] }}</span> · <span>度量 {{ fieldCounts(row)[1] }}</span></template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }"><el-tag size="small" :type="row.status==='enabled' ? 'success' : 'info'">{{ row.status }}</el-tag></template>
              </el-table-column>
              <el-table-column label="更新时间" width="150"><template #default="{ row }">{{ row.createdAt }}</template></el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button size="small" type="primary" link @click.stop="openDetail(row)">配置</el-button>
                  <el-button v-if="row.sourceType === 'custom_sql'" size="small" type="primary" link @click.stop="openSqlEditor(row)">编辑 SQL</el-button>
                  <el-button size="small" type="danger" link @click.stop="removeModel(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="total" class="model-pagination">
              <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background @current-change="loadModels" @size-change="loadModels" />
            </div>
          </el-card>
        </div>
      </div>

      <el-drawer v-model="drawerOpen" :title="active ? active.name : '模型详情'" size="min(920px, 100%)" append-to-body>
        <div v-if="active" class="model-drawer-body">
          <div class="model-title">
            <div><div class="eyebrow">当前模型</div><h2>{{ active.name }}</h2><div class="muted">{{ active.code }} · {{ active.table }} · 负责人：{{ active.owner }}</div></div>
            <el-tag :type="active.status === 'enabled' ? 'success' : 'info'">{{ active.status }}</el-tag>
          </div>
          <div class="model-summary">
            <div><span>维度字段</span><b>{{ counts.dimension }}</b></div>
            <div><span>度量字段</span><b>{{ counts.measure }}</b></div>
            <div><span>普通字段</span><b>{{ counts.normal }}</b></div>
            <div><span>引用指标</span><b>{{ referencedIndicators.length }}</b></div>
          </div>
          <div class="model-desc">{{ active.description || '暂无模型说明，可在后续增加模型基础信息维护。' }}</div>

          <el-tabs v-model="activeTab">
            <el-tab-pane label="字段配置" name="fields">
              <div class="filterbar model-field-filter">
                <div class="filter-item"><span>字段检索</span><el-input v-model="fieldKeyword" placeholder="字段名、中文名、类型" /></div>
                <div class="filter-item"><span>字段角色</span><el-select v-model="fieldRole" style="width:100%"><el-option value="all" label="全部" /><el-option value="dimension" label="dimension" /><el-option value="measure" label="measure" /><el-option value="normal" label="normal" /></el-select></div>
                <el-button @click="fieldKeyword=''; fieldRole='all'">重置</el-button>
              </div>
              <el-table :data="filteredFields" size="small" empty-text="暂无字段">
                <el-table-column label="字段" min-width="150">
                  <template #default="{ row }"><b>{{ row.name }}</b><div class="muted">{{ row.dataType }}</div></template>
                </el-table-column>
                <el-table-column prop="alias" label="业务名称" min-width="120" show-overflow-tooltip />
                <el-table-column label="角色" width="90">
                  <template #default="{ row }"><el-tag size="small" type="info">{{ row.role==='dimension' ? '维度' : row.role==='measure' ? '度量' : '普通' }}</el-tag></template>
                </el-table-column>
                <el-table-column label="单位" width="80"><template #default="{ row }">{{ row.unit || '-' }}</template></el-table-column>
                <el-table-column label="业务属性" min-width="150">
                  <template #default="{ row }">
                    <el-tag v-if="row.isDate" size="small">日期字段</el-tag>
                    <el-tag v-if="row.isOrg" size="small">机构字段</el-tag>
                    <el-tag v-if="row.filterable" size="small">可筛选</el-tag>
                    <span v-if="!row.isDate && !row.isOrg && !row.filterable">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="码值集" width="120"><template #default="{ row }">{{ row.dictSetName || '-' }}</template></el-table-column>
                <el-table-column label="操作" width="90"><template #default="{ row }"><el-button size="small" type="primary" @click="openFieldEditor(row)">配置</el-button></template></el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane label="模型结构" name="structure">
              <div class="field-groups">
                <div v-for="group in fieldGroups" :key="group.key" class="field-group">
                  <div class="section-title">{{ group.label }} <el-tag size="small" type="info">{{ group.rows.length }}</el-tag></div>
                  <div class="chips"><el-tag v-for="f in group.rows" :key="f.name" size="small">{{ f.alias }} · {{ f.name }}</el-tag></div>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="引用指标" name="indicators">
              <el-table v-if="referencedIndicators.length" :data="referencedIndicators" size="small">
                <el-table-column prop="name" label="指标" min-width="160" show-overflow-tooltip />
                <el-table-column prop="code" label="编码" width="120" />
                <el-table-column label="状态" width="90">
                  <template #default="{ row }"><el-tag size="small" :type="['enabled','success'].includes(row.status) ? 'success' : (['disabled','offline','failed'].includes(row.status) ? 'danger' : 'info')">{{ row.status }}</el-tag></template>
                </el-table-column>
                <el-table-column label="结果表" width="150"><template #default="{ row }">{{ getResultTable(row) }}</template></el-table-column>
              </el-table>
              <div v-else class="empty">当前模型暂未被指标引用</div>
            </el-tab-pane>

          </el-tabs>
        </div>
      </el-drawer>

      <el-dialog v-model="fieldDialogOpen" :title="editingField ? editingField.alias : ''" width="640px" append-to-body>
        <div v-if="editingField">
          <div class="muted field-dialog-meta">{{ editingField.name }} · {{ editingField.dataType }}</div>
          <el-form label-width="110px">
            <el-form-item label="业务名称"><el-input v-model="editingField.alias" /></el-form-item>
            <el-form-item label="字段角色"><el-select v-model="editingField.role" style="width:100%"><el-option value="dimension" label="维度字段" /><el-option value="measure" label="度量字段" /><el-option value="normal" label="普通字段" /></el-select></el-form-item>
            <el-form-item label="单位"><el-input v-model="editingField.unit" placeholder="例如：元、户、%" /></el-form-item>
            <el-form-item label="业务属性">
              <el-checkbox v-model="editingField.isDate">日期字段</el-checkbox>
              <el-checkbox v-model="editingField.isOrg">机构字段</el-checkbox>
              <el-checkbox v-model="editingField.filterable">可用于筛选</el-checkbox>
            </el-form-item>
            <el-form-item label="关联码值集">
              <div class="dict-set-picker">
                <el-select v-model="fieldCategoryFilter" placeholder="按分类筛选" clearable size="small" style="width:160px" @change="onFieldCategoryChange">
                  <el-option v-for="c in dictCategories" :key="c.id" :value="c.id" :label="c.categoryName" />
                </el-select>
                <el-select v-model="editingField.dictSetId" placeholder="选择码值集（可清空）" clearable filterable size="small" style="flex:1">
                  <el-option
                    v-for="s in filteredDictSets"
                    :key="s.id"
                    :value="s.id"
                    :label="`${s.setName}（${s.setCode}）`"
                  />
                </el-select>
              </div>
              <div class="muted" style="margin-top:4px">关联后，该字段值可按码值集翻译为业务名称。可留空表示纯文本字段。</div>
            </el-form-item>
          </el-form>
        </div>
        <template #footer>
          <el-button @click="closeFieldEditor">取消</el-button>
          <el-button type="primary" @click="saveField">保存字段</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="sqlEditorOpen" title="编辑自定义 SQL" width="760px" append-to-body :close-on-click-modal="false">
        <div class="muted field-dialog-meta">{{ editingSqlModel?.name }}（{{ editingSqlModel?.code }}）</div>
        <el-input v-model="sqlEditorText" type="textarea" :rows="12" placeholder="请输入自定义 SQL 模板" @input="invalidateSqlPreview" />
        <div v-if="sqlEditorError" class="notice report-preview-error">{{ sqlEditorError }}</div>
        <div v-if="sqlEditorPreview" class="muted field-dialog-meta">SQL 校验通过，解析到 {{ sqlEditorPreview.fields.length }} 个输出字段；保存后会同步模型字段。</div>
        <template #footer>
          <el-button @click="sqlEditorOpen = false">取消</el-button>
          <el-button :loading="sqlEditorLoading" @click="previewSqlUpdate">解析校验</el-button>
          <el-button type="primary" :disabled="!sqlEditorPreview || sqlEditorPreview.templateSql !== sqlEditorText" :loading="sqlEditorSaving" @click="saveSqlUpdate">保存 SQL</el-button>
        </template>
      </el-dialog>
    </div>
    <CustomSqlImportDialog v-model="sqlImportOpen" @reload="emitReload" />

</template>

<script lang="ts">
import { defineComponent, inject, ref, ref as vueRef, computed as vueComputed, watch as vueWatch } from 'vue'
import { ElMessageBox } from 'element-plus'
import CustomSqlImportDialog from '../../components/CustomSqlImportDialog.vue'
import { api as requestApi, jsonBody as toJsonBody } from '../../api'
import ReportImportList from '../../components/ReportImportList.vue'
import type {
  BootstrapData as BootstrapDataT,
  DataModel as DataModelT,
  FieldMeta as FieldMetaT,
  IndicatorOption as IndicatorOptionT,
  IndicatorMeasure as IndicatorMeasureT,
  PageResult as PageResultT,
  ReportPreviewResult as ReportPreviewResultT,
} from '../../types'

const ToastInject = 'notify'

function useNotify() {
  return inject<(message: string) => void>(ToastInject, () => undefined)
}

function getMeasures(indicator: IndicatorOptionT): IndicatorMeasureT[] {
  return []
}

function getResultTable(indicator: IndicatorOptionT) {
  return indicator.resultTable || 'T_IND_RESULT_D'
}

const ModelsPage = defineComponent({
  components: { CustomSqlImportDialog, ReportImportList },
  props: { data: { type: Object as () => BootstrapDataT, required: true } },
  emits: ['reload'],
  setup(props, { emit }) {
    const notify = useNotify()
    const showReportList = vueRef(false)
    const sqlImportOpen = vueRef(false)
    const activeId = vueRef('')
    const drawerOpen = vueRef(false)
    const keyword = vueRef('')
    const selectedModule = vueRef('all')
    const activeTab = vueRef('fields')
    const fieldKeyword = vueRef('')
    const fieldRole = vueRef('all')
    const fieldDialogOpen = vueRef(false)
    const editingField = vueRef<FieldMetaT | null>(null)
    const fieldCategoryFilter = vueRef<number | ''>('')
    const dictCategories = vueRef<Array<{ id: number; categoryName: string }>>([])
    const dictSetsAll = vueRef<Array<{ id: number; setCode: string; setName: string; categoryId: number }>>([])
    const filteredDictSets = vueComputed(() => {
      if (fieldCategoryFilter.value === '') return dictSetsAll.value
      return dictSetsAll.value.filter(s => s.categoryId === fieldCategoryFilter.value)
    })
    const pageSize = vueRef(10)
    const currentPage = vueRef(1)
    const loading = vueRef(false)
    const total = vueRef(0)
    const modelList = vueRef<DataModelT[]>([])
    const activeDetail = vueRef<DataModelT | null>(null)
    const sqlEditorOpen = vueRef(false)
    const editingSqlModel = vueRef<DataModelT | null>(null)
    const sqlEditorText = vueRef('')
    const sqlEditorPreview = vueRef<ReportPreviewResultT | null>(null)
    const sqlEditorError = vueRef('')
    const sqlEditorLoading = vueRef(false)
    const sqlEditorSaving = vueRef(false)
    const modules = vueComputed(() => Array.from(new Set(props.data.models.map((m) => m.module || '未分组'))))
    const active = vueComputed(() => activeDetail.value)

    async function loadModels() {
      loading.value = true
      try {
        const moduleParam = selectedModule.value === 'all' ? '' : selectedModule.value
        const result = await requestApi<PageResultT<DataModelT>>(`/api/models?page=${currentPage.value}&pageSize=${pageSize.value}&keyword=${encodeURIComponent(keyword.value)}&module=${encodeURIComponent(moduleParam)}`)
        modelList.value = result.items
        total.value = result.total
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        loading.value = false
      }
    }

    function query() {
      currentPage.value = 1
      loadModels()
    }

    const counts = vueComputed(() => {
      const fields = active.value?.fields ?? []
      return {
        dimension: fields.filter((f) => f.role === 'dimension').length,
        measure: fields.filter((f) => f.role === 'measure').length,
        normal: fields.filter((f) => f.role === 'normal').length,
      }
    })
    const referencedIndicators = vueComputed(() => {
      const model = active.value
      return model ? props.data.indicators.filter((i) => i.modelId === model.id) : []
    })
    const filteredFields = vueComputed(() => {
      const fields = active.value?.fields ?? []
      return fields.filter((f) => {
        const keywordOk = !fieldKeyword.value || `${f.name}${f.alias}${f.dataType}`.toLowerCase().includes(fieldKeyword.value.toLowerCase())
        const roleOk = fieldRole.value === 'all' || f.role === fieldRole.value
        return keywordOk && roleOk
      })
    })
    const fieldGroups = vueComputed(() => [
      { key: 'dimension', label: '维度字段', rows: (active.value?.fields ?? []).filter((f) => f.role === 'dimension') },
      { key: 'measure', label: '度量字段', rows: (active.value?.fields ?? []).filter((f) => f.role === 'measure') },
      { key: 'normal', label: '普通字段', rows: (active.value?.fields ?? []).filter((f) => f.role === 'normal') },
    ])

    function fieldCounts(model: DataModelT) {
      return [model.fields.filter((f) => f.role === 'dimension').length, model.fields.filter((f) => f.role === 'measure').length]
    }

    async function openDetail(model: DataModelT) {
      activeId.value = model.id
      activeTab.value = 'fields'
      fieldKeyword.value = ''
      fieldRole.value = 'all'
      drawerOpen.value = true
      try {
        activeDetail.value = await requestApi<DataModelT>(`/api/models/${model.id}`)
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      }
    }
    function openSqlEditor(model: DataModelT) {
      editingSqlModel.value = model
      sqlEditorText.value = model.sourceTemplate || model.sourceSql || ''
      sqlEditorPreview.value = null
      sqlEditorError.value = ''
      sqlEditorOpen.value = true
    }
    function invalidateSqlPreview() {
      sqlEditorPreview.value = null
      sqlEditorError.value = ''
    }
    async function previewSqlUpdate() {
      if (!sqlEditorText.value.trim()) {
        notify('SQL 模板不能为空')
        return
      }
      sqlEditorLoading.value = true
      sqlEditorError.value = ''
      try {
        sqlEditorPreview.value = await requestApi<ReportPreviewResultT>('/api/models/sql-preview', {
          method: 'POST',
          body: toJsonBody({ sqlText: sqlEditorText.value }),
        })
      } catch (error) {
        sqlEditorPreview.value = null
        sqlEditorError.value = error instanceof Error ? error.message : String(error)
      } finally {
        sqlEditorLoading.value = false
      }
    }
    async function saveSqlUpdate() {
      const model = editingSqlModel.value
      if (!model || !sqlEditorPreview.value || sqlEditorPreview.value.templateSql !== sqlEditorText.value) return
      sqlEditorSaving.value = true
      try {
        await requestApi(`/api/models/${model.id}/sql`, {
          method: 'PUT',
          body: toJsonBody({ sqlText: sqlEditorText.value }),
        })
        notify('模型 SQL 已更新')
        sqlEditorOpen.value = false
        await emitReload()
        if (activeId.value === model.id) {
          activeDetail.value = await requestApi<DataModelT>(`/api/models/${model.id}`)
        }
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      } finally {
        sqlEditorSaving.value = false
      }
    }
    async function removeModel(model: DataModelT) {
      try {
        await ElMessageBox.confirm(
          `确定删除模型「${model.name}」？关联指标也会逻辑删除，历史数据会保留。`,
          '删除模型',
          { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
        )
      } catch {
        return
      }
      try {
        const result = await requestApi<{ deletedIndicators: number }>(`/api/models/${model.id}`, { method: 'DELETE' })
        notify(`模型已删除，关联指标 ${result.deletedIndicators} 个`)
        if (activeId.value === model.id) {
          drawerOpen.value = false
          activeDetail.value = null
        }
        await emitReload()
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      }
    }
    function openFieldEditor(field: FieldMetaT) {
      editingField.value = { ...field }
      fieldCategoryFilter.value = ''
      fieldDialogOpen.value = true
      loadFieldDictOptions()
    }
    function closeFieldEditor() {
      fieldDialogOpen.value = false
      editingField.value = null
      fieldCategoryFilter.value = ''
    }
    function onFieldCategoryChange() {
      // 切换分类时，若当前已选码值集不在该分类下，则清空
      if (editingField.value && fieldCategoryFilter.value !== '') {
        const stillIn = filteredDictSets.value.some(s => s.id === editingField.value!.dictSetId)
        if (!stillIn) editingField.value.dictSetId = null
      }
    }
    async function loadFieldDictOptions() {
      try {
        const [cats, sets] = await Promise.all([
          requestApi<Array<{ id: number; categoryName: string }>>('/api/dict/categories'),
          requestApi<Array<{ id: number; setCode: string; setName: string; categoryId: number }>>('/api/dict/sets/options'),
        ])
        dictCategories.value = cats
        dictSetsAll.value = sets
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error))
      }
    }
    async function saveField() {
      const model = active.value
      if (!editingField.value || !model) return
      if (!editingField.value.alias.trim()) {
        notify('请填写字段业务名称')
        return
      }
      const payload = {
        alias: editingField.value.alias,
        role: editingField.value.role,
        dataType: editingField.value.dataType,
        unit: editingField.value.unit ?? '',
        isDate: editingField.value.isDate,
        isOrg: editingField.value.isOrg,
        filterable: editingField.value.filterable,
        dictSetId: editingField.value.dictSetId ?? null,
      }
      await requestApi(`/api/models/${model.id}/fields/${editingField.value.name}`, { method: 'PUT', body: toJsonBody(payload) })
      notify('字段已保存')
      closeFieldEditor()
      activeDetail.value = await requestApi<DataModelT>(`/api/models/${model.id}`)
      emit('reload')
    }
    function selectModule(moduleName: string) {
      selectedModule.value = moduleName
      currentPage.value = 1
      loadModels()
    }
    async function emitReload() {
      emit('reload')
      await loadModels()
    }
    vueWatch(pageSize, () => { currentPage.value = 1; loadModels() })
    loadModels()
    return { activeId, active, drawerOpen, activeTab, keyword, selectedModule, modules, total, currentPage, pageSize, modelList, loading, counts, referencedIndicators, filteredFields, fieldGroups, fieldCounts, fieldKeyword, fieldRole, fieldDialogOpen, editingField, fieldCategoryFilter, dictCategories, filteredDictSets, onFieldCategoryChange, openDetail, openFieldEditor, closeFieldEditor, saveField, selectModule, query, loadModels, getResultTable, showReportList, sqlImportOpen, emitReload, sqlEditorOpen, editingSqlModel, sqlEditorText, sqlEditorPreview, sqlEditorError, sqlEditorLoading, sqlEditorSaving, openSqlEditor, invalidateSqlPreview, previewSqlUpdate, saveSqlUpdate, removeModel }
  },

})

export default ModelsPage
</script>

<style scoped>
.model-main-layout { display: grid; grid-template-columns: 230px minmax(0, 1fr); gap: 12px; align-items: start; }
.model-main-panel { min-width: 0; }
.model-domain {
  position: sticky;
  top: 0;
}
.domain-node {
  width: calc(100% - 16px);
  margin: 4px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: white;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  color: #334155;
  text-align: left;
}
.domain-node.active,
.domain-node:hover {
  border-color: #b9d8f0;
  background: #eef7ff;
  color: var(--brand);
}
.domain-node b {
  color: var(--muted);
}
.head-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.head-bar strong { color: var(--ink); }
.model-toolbar { display: flex; align-items: center; gap: 12px; }
.model-toolbar .model-search { width: 320px; }
.model-field-filter {
  grid-template-columns: minmax(240px, 1fr) 180px auto;
  box-shadow: none;
}
.field-groups {
  display: grid;
  gap: 12px;
}
.field-group {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: #fbfdff;
  padding: 12px;
}
.dict-set-picker {
  display: flex;
  gap: 8px;
  width: 100%;
}
.model-pagination { display: flex; justify-content: flex-end; padding-top: 12px; }
.model-list-empty { display: grid; justify-items: center; gap: 8px; padding: 20px; }
.model-drawer-body { display: grid; gap: 12px; }
.field-dialog-meta { margin-bottom: 12px; }
@media (max-width: 1180px) {
  .model-field-filter {
    grid-template-columns: 1fr;
  }

  .model-domain {
    position: static;
  }
}
</style>
