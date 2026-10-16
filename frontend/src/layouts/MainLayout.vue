<template>
  <div class="shell">
    <aside class="sidebar" :class="{ 'mobile-open': mobileMenuOpen }">
      <div class="brand">
        <div class="brand-mark">指</div>
        <div class="brand-title">指标管理系统</div>
        <button class="mobile-menu-close" title="关闭菜单" aria-label="关闭菜单" @click="mobileMenuOpen = false">×</button>
      </div>

      <el-menu
        :default-active="activeIndex"
        :default-openeds="defaultOpeneds"
        class="side-menu"
        @select="onMenuSelect"
        background-color="transparent"
        text-color="#d6e1ee"
        active-text-color="#8bd6ff"
      >
        <el-sub-menu v-for="group in menuGroups" :key="group.title" :index="group.title">
          <template #title>
            <span class="side-menu-title">{{ group.title }}</span>
          </template>
          <el-menu-item v-for="item in group.items" :key="item.key" :index="item.key">
            {{ item.label }}
          </el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div class="sidebar-foot">当前连接：达梦数据库 · 不含审核发布流程</div>
    </aside>

    <main class="main">
      <header class="topbar">
        <button class="mobile-menu-trigger" type="button" title="打开菜单" aria-label="打开菜单" @click="mobileMenuOpen = true">☰</button>
        <div class="crumb">统一指标管理平台 <span>/</span> {{ activeMenuLabel }}</div>
        <div class="user"><span class="avatar">业</span>业务用户</div>
      </header>

      <div class="system-tabs-wrap" :class="{ overflow: tabsOverflow }">
        <nav ref="tabsRef" class="system-tabs" aria-label="已打开页面" @scroll="updateHiddenTabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :data-tab-key="tab.key"
            class="system-tab"
            :class="{ active: tab.key === currentTabKey, fixed: tab.key === homeTabKey }"
            type="button"
            @click="openTab(tab)"
          >
            <span class="system-tab-label">{{ tab.label }}</span>
            <span v-if="tab.key !== homeTabKey" class="system-tab-close" title="关闭页签" aria-label="关闭页签" @click.stop="closeTab(tab.key)">×</span>
          </button>
        </nav>
        <div v-if="tabsOverflow" class="tabs-more">
          <el-dropdown trigger="click" @command="onMoreTabCommand">
            <el-button size="small">更多 <span class="tabs-more-caret">⌄</span></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="tab in hiddenTabs" :key="tab.key" :command="tab">
                  <span class="more-tab-row"><span class="more-tab-label">{{ tab.label }}</span><span class="more-tab-close" title="关闭" @click.stop="closeTab(tab.key)">×</span></span>
                </el-dropdown-item>
                <el-dropdown-item v-if="!hiddenTabs.length" disabled>暂无可隐藏页签</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <section class="content">
        <div v-if="pageError" class="page-error" role="alert">
          <strong>页面加载异常</strong><span>{{ pageError }}</span><button class="btn small" type="button" @click="load">重新加载</button>
        </div>
        <div v-if="!data" class="page"><div class="card pad loading-state">正在加载指标系统...</div></div>
        <component
          :is="pageHostComponent"
          v-else
          :data="data"
          :view="view"
          :active-label="activeMenuLabel"
          :editing-id="editingIndicatorId"
          :indicator-id="focusIndicatorId"
          @go="go"
          @edit="editIndicator"
          @reload="load"
          @saved="onIndicatorSaved"
          @back="go('indicators')"
        />
      </section>
    </main>

    <div v-if="toastText" class="toast" role="status">{{ toastText }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onErrorCaptured, onMounted, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { menuGroups, viewPaths, type ViewKey } from '../router'
import { useAppStore } from '../stores/app'
import PageHost from '../components/PageHost.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const view = computed(() => (route.meta.view as ViewKey) ?? 'overview')
const data = computed(() => appStore.data)
const editingIndicatorId = computed(() => String(route.params.id ?? ''))
const focusIndicatorId = computed(() => String(route.query.indicatorId ?? ''))
const toastText = ref('')
const pageError = computed(() => appStore.error)
const mobileMenuOpen = ref(false)

// el-menu 配置
const activeIndex = computed(() => view.value as string)
const defaultOpeneds = computed(() => menuGroups.map((g) => g.title))
function onMenuSelect(index: string) {
  go(index as ViewKey)
}

type SystemTab = { key: string; path: string; label: string }
const homeTabKey = '/'
const tabs = ref<SystemTab[]>([
  { key: homeTabKey, path: homeTabKey, label: '首页概览' },
])
const currentTabKey = computed(() => tabKey(route.path))
const tabsRef = ref<HTMLElement | null>(null)
const tabsOverflow = ref(false)
const hiddenTabs = ref<SystemTab[]>([])

function checkTabsOverflow() {
  const el = tabsRef.value
  tabsOverflow.value = !!el && el.scrollWidth > el.clientWidth + 1
  updateHiddenTabs()
}
function updateHiddenTabs() {
  const nav = tabsRef.value
  if (!nav) { hiddenTabs.value = []; return }
  const left = nav.scrollLeft
  const right = left + nav.clientWidth
  hiddenTabs.value = tabs.value.filter((tab) => {
    const el = nav.querySelector(`[data-tab-key="${tab.key}"]`) as HTMLElement | null
    if (!el) return false
    const elLeft = el.offsetLeft
    const elRight = elLeft + el.offsetWidth
    return elLeft < left || elRight > right
  })
}
function scrollActiveTabIntoView() {
  const nav = tabsRef.value
  const el = nav?.querySelector(`[data-tab-key="${currentTabKey.value}"]`) as HTMLElement | null
  el?.scrollIntoView({ inline: 'nearest', block: 'nearest' })
}

const activeMenuLabel = computed(() => menuGroups.flatMap((group) => group.items).find((item) => item.key === view.value)?.label ?? (view.value === 'builder' ? (editingIndicatorId.value ? '编辑指标' : '新增指标') : ''))
const pageHostComponent = PageHost

function tabKey(path: string) { return path || '/' }
function tabLabel(path: string) {
  if (path === '/') return '首页概览'
  if (path.includes('/indicators/new')) return '新增指标'
  if (path.includes('/indicators/') && path.endsWith('/edit')) return '编辑指标'
  return menuGroups.flatMap((group) => group.items).find((item) => viewPaths[item.key] === path)?.label ?? activeMenuLabel.value
}
function ensureCurrentTab() {
  const key = tabKey(route.path)
  const current = tabs.value.find((tab) => tab.key === key)
  if (current) {
    current.path = route.fullPath
    current.label = tabLabel(route.path)
    return
  }
  tabs.value.push({ key, path: route.fullPath, label: tabLabel(route.path) })
}
function openTab(tab: SystemTab) {
  mobileMenuOpen.value = false
  router.push(tab.path)
}
function onMoreTabCommand(tab: SystemTab) {
  openTab(tab)
}
function closeTab(key: string) {
  if (key === homeTabKey) return
  const index = tabs.value.findIndex((tab) => tab.key === key)
  if (index < 0) return
  const wasActive = currentTabKey.value === key
  tabs.value.splice(index, 1)
  if (wasActive) {
    const fallback = tabs.value[index - 1] || tabs.value[index] || tabs.value[0]
    if (fallback) router.push(fallback.path)
  }
  window.setTimeout(checkTabsOverflow, 0)
}

function notify(message: string) {
  toastText.value = message
  window.setTimeout(() => { toastText.value = '' }, 2200)
}
provide('notify', notify)

async function load() { await appStore.load() }
function go(target: ViewKey, indicatorId = '') {
  mobileMenuOpen.value = false
  router.push({ path: viewPaths[target], query: indicatorId ? { indicatorId } : undefined })
}
function editIndicator(id: string) {
  mobileMenuOpen.value = false
  router.push(`/indicator-center/indicators/${id}/edit`)
}
async function onIndicatorSaved(id: string) {
  await load()
  await router.push(viewPaths.indicators)
  notify(`指标已保存：${id}`)
}
onMounted(() => {
  window.addEventListener('error', (event) => { appStore.error = event.message || '页面脚本异常' })
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    appStore.error = reason instanceof Error ? reason.message : String(reason || '接口请求异常')
  })
  ensureCurrentTab()
  load()
  checkTabsOverflow()
  window.addEventListener('resize', checkTabsOverflow)
})
watch(() => route.fullPath, () => { ensureCurrentTab(); load(); window.setTimeout(() => { scrollActiveTabIntoView(); checkTabsOverflow() }, 0) })
onErrorCaptured((error) => {
  appStore.error = error instanceof Error ? error.message : String(error)
  return false
})
</script>

<style scoped>
/* ============ 布局 ============ */
.shell {
  height: 100%;
  min-height: 100%;
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
}

.main {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ============ 侧边栏 ============ */
.sidebar {
  background-color: #125488;
  color: #cbd7e6;
  border-right: 1px solid rgba(255, 255, 255, .06);
  display: flex;
  flex-direction: column;
  width: 232px;
  min-width: 232px;
  overflow: hidden;
}

.brand {
  height: 60px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  background: #2a9fd6;
  color: white;
  font-weight: 700;
  font-size: 15px;
  box-shadow: 0 2px 8px rgba(42, 159, 214, .3);
}

.brand-title {
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.mobile-menu-close,
.mobile-menu-trigger {
  display: none;
}

/* ============ el-menu 菜单（深色主题） ============ */
.side-menu {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-right: 0 !important;
  background: transparent !important;
  padding: 10px 8px;
  width: 100%;
}

.side-menu :deep(.el-sub-menu) {
  margin-bottom: 2px;
  width: 100%;
}

/* 一级菜单标题 */
.side-menu :deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  border-radius: 6px;
  padding: 0 16px !important;
  color: #d6e1ee;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.3px;
  transition: background .15s, color .15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, .08);
  color: #ffffff;
}

.side-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #8bd6ff;
}

/* 折叠箭头 */
.side-menu :deep(.el-sub-menu__title .el-sub-menu__icon-arrow) {
  color: #6b85a3;
  font-size: 12px;
}

/* 二级菜单容器 */
.side-menu :deep(.el-menu) {
  background: transparent !important;
  padding: 4px 0 8px;
  width: 100%;
}

/* 二级菜单项 */
.side-menu :deep(.el-menu-item) {
  height: 40px;
  line-height: 40px;
  border-radius: 5px;
  margin: 2px 0;
  padding: 0 14px 0 32px !important;
  color: #9fb3cd;
  font-size: 14px;
  font-weight: 400;
  transition: background .15s, color .15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, .06);
  color: #ffffff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: rgba(42, 159, 214, .15);
  color: #8bd6ff;
  font-weight: 500;
  box-shadow: inset 2px 0 0 #2a9fd6;
}

/* ============ 底部 ============ */
.sidebar-foot {
  margin-top: auto;
  padding: 14px 20px;
  color: #6b85a3;
  font-size: 12px;
  border-top: 1px solid rgba(255, 255, 255, .08);
  white-space: nowrap;
}

/* ============ 顶部栏与内容区 ============ */
.topbar {
  flex: 0 0 60px;
  height: 60px;
  background: white;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
}

.crumb {
  color: var(--muted);
}

.user {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #42526a;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1769aa;
  color: white;
  display: grid;
  place-items: center;
}

.content {
  flex: 1 1 auto;
  min-height: 0;
  padding: 18px 20px 28px;
  overflow: auto;
}

/* ============ 系统页签 ============ */
.system-tabs-wrap {
  position: relative;
  flex: 0 0 42px;
  min-width: 0;
  display: flex;
  align-items: stretch;
}

.system-tabs {
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
  display: flex;
  align-items: stretch;
  gap: 2px;
  padding: 5px 14px 0;
  overflow-x: auto;
  overflow-y: hidden;
  border-bottom: 1px solid var(--line);
  background: #f7f9fc;
  scrollbar-width: none;
}

.system-tabs::-webkit-scrollbar {
  display: none;
}

.system-tabs-wrap.overflow .system-tabs {
  -webkit-mask-image: linear-gradient(to right, black calc(100% - 48px), transparent 100%);
  mask-image: linear-gradient(to right, black calc(100% - 48px), transparent 100%);
}

.tabs-more {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  padding: 5px 10px 0;
  border-bottom: 1px solid var(--line);
  background: #f7f9fc;
}

.tabs-more-caret {
  margin-left: 2px;
  font-size: 12px;
}

.system-tab {
  flex: 0 0 auto;
  min-width: 112px;
  max-width: 220px;
  height: 37px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: 1px solid transparent;
  border-bottom: 0;
  border-radius: 6px 6px 0 0;
  padding: 0 11px;
  background: transparent;
  color: #66788c;
  text-align: left;
}

.system-tab:hover {
  background: #edf4f9;
  color: var(--brand);
}

.system-tab.active {
  border-color: var(--line);
  background: white;
  color: var(--ink);
  box-shadow: 0 -1px 0 white;
}

.system-tab-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.system-tab-close {
  flex: 0 0 18px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 4px;
  color: #8a9aab;
  font-size: 16px;
  line-height: 1;
}

.system-tab-close:hover {
  background: #e4edf4;
  color: var(--red);
}

.toast {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  background: #172033;
  color: white;
  border-radius: 8px;
  padding: 10px 14px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, .25);
  z-index: 20;
}

/* ============ 页签下拉 ============ */
.more-tab-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 170px; }
.more-tab-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.more-tab-close { flex: 0 0 auto; padding: 0 4px; color: var(--muted); font-weight: 700; }
.more-tab-close:hover { color: var(--red); }

@media (max-width: 1180px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 1002;
    width: min(300px, 86vw);
    display: flex;
    transform: translateX(-100%);
    overflow-y: auto;
    box-shadow: 18px 0 36px rgba(8, 18, 32, .24);
    transition: transform .2s ease;
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .mobile-menu-close {
    width: 30px;
    height: 30px;
    margin-left: auto;
    display: grid;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, .16);
    border-radius: 6px;
    background: rgba(255, 255, 255, .06);
    color: white;
    font-size: 20px;
    line-height: 1;
  }

  .mobile-menu-trigger {
    flex: 0 0 36px;
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: white;
    color: var(--brand);
    font-size: 20px;
    line-height: 1;
  }

  .topbar {
    padding: 0 12px;
  }

  .crumb {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .content {
    padding: 12px 10px 22px;
  }
}
</style>
