import type { RouteRecordRaw } from 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

export type ViewKey = 'overview' | 'models' | 'dict' | 'builder' | 'indicators' | 'versions' | 'results' | 'lineage' | 'impact' | 'schedules' | 'jobs'

export type MenuGroup = {
  title: string
  icon: string
  desc: string
  items: Array<{ key: ViewKey; label: string }>
}

export const menuGroups: MenuGroup[] = [
  { title: '工作台', icon: '台', desc: '总览与待办', items: [{ key: 'overview', label: '首页概览' }] },
  { title: '数据资产', icon: '数', desc: '模型与码值', items: [{ key: 'models', label: '模型管理' }, { key: 'dict', label: '码值管理' }] },
  { title: '指标中心', icon: '指', desc: '指标 / 查询', items: [{ key: 'indicators', label: '指标管理' }, { key: 'versions', label: '版本管理' }, { key: 'results', label: '指标数据查询' }] },
  { title: '运行中心', icon: '运', desc: '调度与日志', items: [{ key: 'schedules', label: '调度管理' }, { key: 'jobs', label: '运行日志' }] },
]

export const viewPaths: Record<ViewKey, string> = {
  overview: '/',
  models: '/data-assets/models',
  dict: '/data-assets/dict',
  indicators: '/indicator-center/indicators',
  builder: '/indicator-center/indicators/new',
  versions: '/indicator-center/versions',
  results: '/indicator-center/results',
  lineage: '/indicator-center/lineage',
  impact: '/indicator-center/impact',
  schedules: '/runtime/schedules',
  jobs: '/runtime/jobs',
}

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'overview', component: MainLayout, meta: { view: 'overview' } },
  { path: '/data-assets/models', name: 'models', component: MainLayout, meta: { view: 'models' } },
  { path: '/data-assets/dict', name: 'dict', component: MainLayout, meta: { view: 'dict' } },
  { path: '/data-assets/reports', redirect: '/data-assets/models' },
  { path: '/indicator-center/indicators', name: 'indicators', component: MainLayout, meta: { view: 'indicators' } },
  { path: '/indicator-center/indicators/new', name: 'indicatorCreate', component: MainLayout, meta: { view: 'builder' } },
  { path: '/indicator-center/indicators/:id/edit', name: 'indicatorEdit', component: MainLayout, meta: { view: 'builder' } },
  { path: '/indicator-center/versions', name: 'versions', component: MainLayout, meta: { view: 'versions' } },
  { path: '/indicator-center/results', name: 'results', component: MainLayout, meta: { view: 'results' } },
  { path: '/indicator-center/lineage', name: 'lineage', component: MainLayout, meta: { view: 'lineage' } },
  { path: '/indicator-center/impact', name: 'impact', component: MainLayout, meta: { view: 'impact' } },
  { path: '/runtime/schedules', name: 'schedules', component: MainLayout, meta: { view: 'schedules' } },
  { path: '/runtime/jobs', name: 'jobs', component: MainLayout, meta: { view: 'jobs' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
