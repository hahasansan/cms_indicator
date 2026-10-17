<template>
  <div class="page-host">
   s <OverviewPage v-if="view === 'overview'" :data="data" @go="go" />
    <ModelsPage v-else-if="view === 'models'" :data="data" @reload="reload" />
    <DictPage v-else-if="view === 'dict'" :data="data" @reload="reload" />
    <BuilderPage v-else-if="view === 'builder'" :data="data" :editing-id="editingId" @saved="saved" @back="back" />
    <IndicatorsPage v-else-if="view === 'indicators'" :data="data" @go="go" @edit="edit" @reload="reload" />
    <VersionsPage v-else-if="view === 'versions'" :data="data" :indicator-id="indicatorId" @go="go" @reload="reload" />
    <ResultsPage v-else-if="view === 'results'" :data="data" :indicator-id="indicatorId" />
    <LineagePage v-else-if="view === 'lineage'" :data="data" :indicator-id="indicatorId" />
    <ImpactPage v-else-if="view === 'impact'" :data="data" :indicator-id="indicatorId" />
    <SchedulesPage v-else-if="view === 'schedules'" :data="data" @reload="reload" />
    <JobsPage v-else-if="view === 'jobs'" :data="data" />

    <div v-else class="page">
      <div class="card pad">
        <div class="card-title">页面未找到</div>
        <div class="notice">当前菜单状态没有匹配页面：{{ view }}</div>
        <div class="actions footer-actions"><button class="btn primary" type="button" @click="go('overview')">返回首页</button></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import OverviewPage from '../views/dashboard/OverviewPage.vue'
import ModelsPage from '../views/data-assets/ModelsPage.vue'
import DictPage from '../views/data-assets/DictPage.vue'
import BuilderPage from '../views/indicator-center/BuilderPage.vue'
import ImpactPage from '../views/indicator-center/ImpactPage.vue'
import IndicatorsPage from '../views/indicator-center/IndicatorsPage.vue'
import LineagePage from '../views/indicator-center/LineagePage.vue'
import ResultsPage from '../views/indicator-center/ResultsPage.vue'
import VersionsPage from '../views/indicator-center/VersionsPage.vue'
import JobsPage from '../views/runtime/JobsPage.vue'
import SchedulesPage from '../views/runtime/SchedulesPage.vue'
import type { ViewKey } from '../router'
import type { BootstrapData } from '../types'

defineProps<{
  data: BootstrapData
  view: ViewKey
  activeLabel?: string
  editingId?: string
  indicatorId?: string
}>()

const emit = defineEmits<{
  go: [target: ViewKey, indicatorId?: string]
  edit: [id: string]
  reload: []
  saved: [id: string]
  back: []
}>()

function go(target: ViewKey, indicatorId?: string) { emit('go', target, indicatorId) }
function edit(id: string) { emit('edit', id) }
function reload() { emit('reload') }
function saved(id: string) { emit('saved', id) }
function back() { emit('back') }
</script>

<style scoped>
.page-host {
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.card-title {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 700;
  color: var(--ink);
}
</style>
