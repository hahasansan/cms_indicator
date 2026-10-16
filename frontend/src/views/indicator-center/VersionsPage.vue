<template>
    <div class="page data-list-page">
      <div class="page-head"><div><h1>版本管理</h1><div class="desc">查看指标每次保存形成的版本，核对 SQL、配置和保存时间，为后续回滚能力保留版本基线。</div></div><div class="actions"><el-button @click="emit('go','indicators')">返回指标管理</el-button></div></div>
      <div class="filterbar version-filter">
        <div class="filter-item"><span>选择指标</span><el-select v-model="selectedId" style="width:100%"><el-option v-for="i in data.indicators" :key="i.id" :value="i.id" :label="`${i.name} (${i.code})`" /></el-select></div>
        <el-button type="primary" @click="loadVersions">查询版本</el-button>
      </div>
      <div class="version-layout data-list-main data-list-split">
        <el-card shadow="never" class="data-list-panel source-panel">
          <template #header><div class="head-bar"><strong>版本列表</strong><el-tag type="info" size="small">{{ versions.length }} 个版本</el-tag></div></template>
          <div class="source-list data-list-viewport">
            <button v-for="v in versions" :key="String(v.id)" class="source-item" :class="{ active: selectedVersion?.id === v.id }" @click="selectedVersion = v">
              <span><b>V{{ v.version }}</b><small>{{ v.savedAt }}</small></span><el-tag size="small" type="success">已保存</el-tag>
            </button>
            <div v-if="!versions.length" class="data-list-empty"><b>暂无版本</b><span>选择指标并查询版本记录。</span></div>
          </div>
        </el-card>
        <el-card v-if="selectedVersion" shadow="never">
          <div class="detail-head">
            <div><div class="eyebrow">版本详情</div><h2>{{ indicator?.name }} · V{{ selectedVersion.version }}</h2><div class="muted">{{ indicator?.code }} · {{ indicator ? modelDisplayName(data.models, indicator.modelId) : '-' }}</div></div>
            <div class="actions"><el-button size="small" type="primary" @click="restoreVersion">恢复此版本</el-button><el-tag size="small" :type="indicator ? (['enabled','success'].includes(indicator.status) ? 'success' : 'info') : 'info'">{{ indicator?.status }}</el-tag></div>
          </div>
          <div class="grid-2">
            <div><div class="section-title">SQL</div><pre class="sql">{{ selectedVersion.sqlText }}</pre></div>
            <div><div class="section-title">配置 JSON</div><pre class="sql">{{ JSON.stringify(selectedVersion.config, null, 2) }}</pre></div>
          </div>
        </el-card>
      </div>
    </div>

</template>

<script lang="ts">
import { defineComponent, inject, ref, ref as vueRef, computed as vueComputed, watch as vueWatch } from 'vue'
import { api as requestApi, jsonBody as toJsonBody } from '../../api'
import type { BootstrapData, ModelOption as ModelOptionT } from '../../types'

const ToastInject = 'notify'

function useNotify() {
  return inject<(message: string) => void>(ToastInject, () => undefined)
}

function modelDisplayName(models: ModelOptionT[], modelId: string) {
  return models.find((m) => m.id === modelId)?.name ?? '-'
}

const VersionsPage = defineComponent({
  props: { data: { type: Object as () => BootstrapData, required: true }, indicatorId: { type: String, default: '' } },
  emits: ['go', 'reload'],
  setup(props, { emit }) {
    const notify = useNotify()
    const selectedId = vueRef(props.indicatorId || props.data.indicators[0]?.id || '')
    const versions = vueRef<Record<string, unknown>[]>([])
    const selectedVersion = vueRef<Record<string, unknown> | null>(null)
    const indicator = vueComputed(() => props.data.indicators.find((i) => i.id === selectedId.value))
    async function loadVersions() {
      if (!selectedId.value) return
      versions.value = await requestApi<Record<string, unknown>[]>(`/api/indicators/${selectedId.value}/versions`)
      selectedVersion.value = versions.value[0] ?? null
    }
    async function restoreVersion() {
      if (!selectedVersion.value || !selectedId.value) return
      if (!window.confirm(`确认恢复到 V${selectedVersion.value.version}？当前配置会作为新版本继续保留。`)) return
      await requestApi(`/api/indicators/${selectedId.value}/versions/${selectedVersion.value.id}/restores`, { method: 'POST', body: toJsonBody({}) })
      notify('版本已恢复，并生成新的当前版本')
      await loadVersions()
      emit('reload')
    }
    vueWatch(selectedId, loadVersions, { immediate: true })
    vueWatch(() => props.indicatorId, (id) => { if (id) selectedId.value = id })
    return { selectedId, versions, selectedVersion, indicator, emit, modelDisplayName, loadVersions, restoreVersion }
  },

})

export default VersionsPage
</script>

<style scoped>
.version-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line-soft);
}
.source-panel :deep(.el-card__body) { padding: 0; }
.head-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.head-bar strong { color: var(--ink); }
</style>
