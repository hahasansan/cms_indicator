<template>
  <div class="page data-list-page">
    <div class="page-head">
      <div>
        <h1>码值管理</h1>
        <div class="desc">维护码值分类 / 码值集 / 码值项。业务侧只看到业务名称，底层全部按 item_code 存储。码值项只停用不删除，保证历史指标配置永远可翻译。</div>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="dict-tabs">
      <!-- ===================== 分类管理 ===================== -->
      <el-tab-pane label="码值分类" name="category">
        <el-card shadow="never" class="data-list-panel">
          <template #header>
            <div class="model-toolbar">
              <div class="model-search"><el-input v-model="catKeyword" placeholder="搜索分类编码 / 名称" clearable @keyup.enter="loadCategories" /></div>
              <el-button type="primary" size="small" @click="loadCategories">查询</el-button>
              <el-button type="primary" size="small" @click="openCatEditor(null)">新增分类</el-button>
            </div>
          </template>
          <el-table :data="categories" size="small" v-loading="catLoading" empty-text="暂无分类">
            <el-table-column label="分类编码" min-width="140"><template #default="{ row }"><b>{{ row.categoryCode }}</b></template></el-table-column>
            <el-table-column prop="categoryName" label="分类名称" min-width="160" />
            <el-table-column prop="sort" label="排序" width="80" />
            <el-table-column label="关联码值集" width="120"><template #default="{ row }">{{ row.setCount }}</template></el-table-column>
            <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="openCatEditor(row)">编辑</el-button>
                <el-button size="small" type="danger" link @click="removeCategory(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ===================== 码值集管理 ===================== -->
      <el-tab-pane label="码值集" name="set">
        <el-card shadow="never" class="data-list-panel">
          <template #header>
            <div class="model-toolbar">
              <div class="filter-item">
                <span>分类</span>
                <el-select v-model="setFilter.categoryId" clearable placeholder="全部分类" style="width:180px" @change="querySets">
                  <el-option v-for="c in categories" :key="c.id" :value="c.id" :label="c.categoryName" />
                </el-select>
              </div>
              <div class="model-search"><el-input v-model="setFilter.keyword" placeholder="搜索码值集编码 / 名称" clearable @keyup.enter="querySets" /></div>
              <el-button type="primary" size="small" @click="querySets">查询</el-button>
              <el-button type="primary" size="small" @click="openSetEditor(null)">新增码值集</el-button>
              <span class="muted">共 {{ setTotal }} 个</span>
            </div>
          </template>
          <el-table :data="sets" size="small" v-loading="setLoading" empty-text="暂无码值集" @row-click="openSetItems">
            <el-table-column label="码值集编码" min-width="160"><template #default="{ row }"><b>{{ row.setCode }}</b></template></el-table-column>
            <el-table-column prop="setName" label="码值集名称" min-width="160" />
            <el-table-column prop="categoryName" label="所属分类" width="140" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="row.status === 'enabled' ? 'success' : 'info'">{{ row.status === 'enabled' ? '启用' : '停用' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="码值项数" width="100"><template #default="{ row }">{{ row.itemCount }}</template></el-table-column>
            <el-table-column label="模型字段引用" width="120"><template #default="{ row }">{{ row.refCount }}</template></el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click.stop="openSetItems(row)">码值项</el-button>
                <el-button size="small" type="primary" link @click.stop="openSetEditor(row)">编辑</el-button>
                <el-button size="small" :type="row.status === 'enabled' ? 'warning' : 'success'" link @click.stop="toggleSetStatus(row)">{{ row.status === 'enabled' ? '停用' : '启用' }}</el-button>
                <el-button size="small" type="danger" link @click.stop="removeSet(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="setTotal" class="model-pagination">
            <el-pagination v-model:current-page="setPage.page" v-model:page-size="setPage.pageSize" :total="setTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background @current-change="loadSets" @size-change="loadSets" />
          </div>
        </el-card>
      </el-tab-pane>

      <!-- ===================== 码值项管理 ===================== -->
      <el-tab-pane label="码值项" name="item">
        <el-card shadow="never" class="data-list-panel">
          <template #header>
            <div class="model-toolbar">
              <div class="filter-item">
                <span>码值集</span>
                <el-select v-model="itemFilter.setId" filterable placeholder="选择码值集" style="width:240px" @change="loadItems">
                  <el-option v-for="s in setOptions" :key="s.id" :value="s.id" :label="`${s.setName}（${s.setCode}）`" />
                </el-select>
              </div>
              <el-button type="primary" size="small" :disabled="!itemFilter.setId" @click="openItemEditor(null)">新增码值项</el-button>
              <el-checkbox v-model="itemFilter.onlyEnabled" @change="loadItems">仅显示启用</el-checkbox>
            </div>
          </template>
          <el-table :data="filteredItems" size="small" v-loading="itemLoading" empty-text="请先选择码值集">
            <el-table-column label="码值编码" min-width="120"><template #default="{ row }"><b>{{ row.itemCode }}</b></template></el-table-column>
            <el-table-column prop="itemName" label="业务名称" min-width="160" />
            <el-table-column prop="sort" label="排序" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="row.status === 'enabled' ? 'success' : 'info'">{{ row.status === 'enabled' ? '启用' : '停用' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="openItemEditor(row)">编辑</el-button>
                <el-button size="small" :type="row.status === 'enabled' ? 'warning' : 'success'" link @click="toggleItemStatus(row)">{{ row.status === 'enabled' ? '停用' : '启用' }}</el-button>
                <el-button size="small" type="danger" link @click="removeItem(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- ===================== 分类编辑对话框 ===================== -->
    <el-dialog v-model="catDialogOpen" :title="catForm.id ? '编辑分类' : '新增分类'" width="520px" append-to-body>
      <el-form label-width="90px">
        <el-form-item label="分类编码" required><el-input v-model="catForm.categoryCode" placeholder="例如 RISK" /></el-form-item>
        <el-form-item label="分类名称" required><el-input v-model="catForm.categoryName" placeholder="例如 风险类" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="catForm.sort" :min="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="catForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="catDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveCategory">保存</el-button>
      </template>
    </el-dialog>

    <!-- ===================== 码值集编辑对话框 ===================== -->
    <el-dialog v-model="setDialogOpen" :title="setForm.id ? '编辑码值集' : '新增码值集'" width="520px" append-to-body>
      <el-form label-width="90px">
        <el-form-item label="所属分类" required>
          <el-select v-model="setForm.categoryId" style="width:100%" placeholder="选择分类">
            <el-option v-for="c in categories" :key="c.id" :value="c.id" :label="c.categoryName" />
          </el-select>
        </el-form-item>
        <el-form-item label="码值集编码" required><el-input v-model="setForm.setCode" placeholder="例如 LOAN_FIVE_LEVEL" /></el-form-item>
        <el-form-item label="码值集名称" required><el-input v-model="setForm.setName" placeholder="例如 贷款五级分类" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="setForm.status" style="width:100%">
            <el-option value="enabled" label="启用" />
            <el-option value="disabled" label="停用" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="setForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="setDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveSet">保存</el-button>
      </template>
    </el-dialog>

    <!-- ===================== 码值项编辑对话框 ===================== -->
    <el-dialog v-model="itemDialogOpen" :title="itemForm.id ? '编辑码值项' : '新增码值项'" width="520px" append-to-body>
      <el-form label-width="90px">
        <el-form-item label="码值编码" required><el-input v-model="itemForm.itemCode" placeholder="例如 01" /></el-form-item>
        <el-form-item label="业务名称" required><el-input v-model="itemForm.itemName" placeholder="例如 正常" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="itemForm.sort" :min="0" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="itemForm.status" style="width:100%">
            <el-option value="enabled" label="启用" />
            <el-option value="disabled" label="停用" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { defineComponent, inject, reactive, ref, computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api as requestApi, jsonBody as toJsonBody } from '../../api'
import type { BootstrapData, DictCategory, DictItem, DictSet } from '../../types'

const ToastInject = 'notify'
function useNotify() {
  return inject<(message: string) => void>(ToastInject, () => undefined)
}

const DictPage = defineComponent({
  name: 'DictPage',
  props: { data: { type: Object as () => BootstrapData, required: true } },
  emits: ['reload'],
  setup(props, { emit }) {
    const notify = useNotify()

    const activeTab = ref<'category' | 'set' | 'item'>('category')

    // ---------- 分类 ----------
    const catKeyword = ref('')
    const catLoading = ref(false)
    const categories = ref<DictCategory[]>([])
    const catDialogOpen = ref(false)
    const catForm = reactive<{ id: number | null; categoryCode: string; categoryName: string; sort: number; remark: string }>({
      id: null, categoryCode: '', categoryName: '', sort: 0, remark: '',
    })

    async function loadCategories() {
      catLoading.value = true
      try {
        categories.value = await requestApi<DictCategory[]>(`/api/dict/categories?keyword=${encodeURIComponent(catKeyword.value)}`)
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      } finally {
        catLoading.value = false
      }
    }
    function openCatEditor(row: DictCategory | null) {
      if (row) {
        catForm.id = row.id
        catForm.categoryCode = row.categoryCode
        catForm.categoryName = row.categoryName
        catForm.sort = row.sort
        catForm.remark = row.remark
      } else {
        catForm.id = null
        catForm.categoryCode = ''
        catForm.categoryName = ''
        catForm.sort = 0
        catForm.remark = ''
      }
      catDialogOpen.value = true
    }
    async function saveCategory() {
      if (!catForm.categoryCode || !catForm.categoryName) {
        notify('分类编码和名称必填'); return
      }
      try {
        const payload = { categoryCode: catForm.categoryCode, categoryName: catForm.categoryName, sort: catForm.sort, remark: catForm.remark }
        if (catForm.id) {
          await requestApi(`/api/dict/categories/${catForm.id}`, { method: 'PUT', body: toJsonBody(payload) })
        } else {
          await requestApi('/api/dict/categories', { method: 'POST', body: toJsonBody(payload) })
        }
        catDialogOpen.value = false
        await loadCategories()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }
    async function removeCategory(row: DictCategory) {
      try {
        await ElMessageBox.confirm(`确定删除分类「${row.categoryName}」？`, '提示', { type: 'warning' })
      } catch { return }
      try {
        await requestApi(`/api/dict/categories/${row.id}`, { method: 'DELETE' })
        await loadCategories()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }

    // ---------- 码值集 ----------
    const setFilter = reactive<{ categoryId: number | ''; keyword: string }>({ categoryId: '', keyword: '' })
    const setPage = reactive<{ page: number; pageSize: number }>({ page: 1, pageSize: 10 })
    const setTotal = ref(0)
    const setLoading = ref(false)
    const sets = ref<DictSet[]>([])
    const setDialogOpen = ref(false)
    const setForm = reactive<{ id: number | null; categoryId: number | ''; setCode: string; setName: string; status: string; remark: string }>({
      id: null, categoryId: '', setCode: '', setName: '', status: 'enabled', remark: '',
    })

    async function loadSets() {
      setLoading.value = true
      try {
        const cid = setFilter.categoryId === '' ? '' : `&categoryId=${setFilter.categoryId}`
        const res = await requestApi<{ items: DictSet[]; total: number }>(
          `/api/dict/sets?page=${setPage.page}&pageSize=${setPage.pageSize}&keyword=${encodeURIComponent(setFilter.keyword)}${cid}`
        )
        sets.value = res.items
        setTotal.value = res.total
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      } finally {
        setLoading.value = false
      }
    }
    function querySets() { setPage.page = 1; loadSets() }

    function openSetEditor(row: DictSet | null) {
      if (row) {
        setForm.id = row.id
        setForm.categoryId = row.categoryId
        setForm.setCode = row.setCode
        setForm.setName = row.setName
        setForm.status = row.status
        setForm.remark = row.remark
      } else {
        setForm.id = null
        setForm.categoryId = categories.value[0]?.id ?? ''
        setForm.setCode = ''
        setForm.setName = ''
        setForm.status = 'enabled'
        setForm.remark = ''
      }
      setDialogOpen.value = true
    }
    async function saveSet() {
      if (!setForm.categoryId || !setForm.setCode || !setForm.setName) {
        notify('分类、码值集编码、名称必填'); return
      }
      try {
        const payload = {
          categoryId: setForm.categoryId,
          setCode: setForm.setCode,
          setName: setForm.setName,
          status: setForm.status,
          remark: setForm.remark,
        }
        if (setForm.id) {
          await requestApi(`/api/dict/sets/${setForm.id}`, { method: 'PUT', body: toJsonBody(payload) })
        } else {
          await requestApi('/api/dict/sets', { method: 'POST', body: toJsonBody(payload) })
        }
        setDialogOpen.value = false
        await loadSets()
        await loadSetOptions()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }
    async function toggleSetStatus(row: DictSet) {
      const next = row.status === 'enabled' ? 'disabled' : 'enabled'
      try {
        await requestApi(`/api/dict/sets/${row.id}`, {
          method: 'PUT',
          body: toJsonBody({ categoryId: row.categoryId, setCode: row.setCode, setName: row.setName, status: next, remark: row.remark }),
        })
        await loadSets()
        await loadSetOptions()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }
    async function removeSet(row: DictSet) {
      try {
        await ElMessageBox.confirm(`确定删除码值集「${row.setName}」？该操作会级联删除其码值项。`, '提示', { type: 'warning' })
      } catch { return }
      try {
        await requestApi(`/api/dict/sets/${row.id}`, { method: 'DELETE' })
        await loadSets()
        await loadSetOptions()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }

    // 码值集下拉选项（仅 enabled）—— 用于码值项 tab 选择
    const setOptions = ref<Array<{ id: number; setCode: string; setName: string; categoryId: number }>>([])
    async function loadSetOptions() {
      try {
        setOptions.value = await requestApi<typeof setOptions.value>('/api/dict/sets/options')
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }

    // ---------- 码值项 ----------
    const itemFilter = reactive<{ setId: number | ''; onlyEnabled: boolean }>({ setId: '', onlyEnabled: false })
    const itemLoading = ref(false)
    const items = ref<DictItem[]>([])
    const itemDialogOpen = ref(false)
    const itemForm = reactive<{ id: number | null; itemCode: string; itemName: string; sort: number; status: string }>({
      id: null, itemCode: '', itemName: '', sort: 0, status: 'enabled',
    })

    const filteredItems = computed(() => itemFilter.onlyEnabled ? items.value.filter(i => i.status === 'enabled') : items.value)

    async function loadItems() {
      if (!itemFilter.setId) { items.value = []; return }
      itemLoading.value = true
      try {
        items.value = await requestApi<DictItem[]>(`/api/dict/items?setId=${itemFilter.setId}`)
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      } finally {
        itemLoading.value = false
      }
    }
    function openSetItems(row: DictSet) {
      activeTab.value = 'item'
      itemFilter.setId = row.id
      loadItems()
    }
    function openItemEditor(row: DictItem | null) {
      if (row) {
        itemForm.id = row.id
        itemForm.itemCode = row.itemCode
        itemForm.itemName = row.itemName
        itemForm.sort = row.sort
        itemForm.status = row.status
      } else {
        itemForm.id = null
        itemForm.itemCode = ''
        itemForm.itemName = ''
        itemForm.sort = 0
        itemForm.status = 'enabled'
      }
      itemDialogOpen.value = true
    }
    async function saveItem() {
      if (!itemFilter.setId) { notify('请先选择码值集'); return }
      if (!itemForm.itemCode || !itemForm.itemName) { notify('码值编码和业务名称必填'); return }
      try {
        const payload = { itemCode: itemForm.itemCode, itemName: itemForm.itemName, sort: itemForm.sort, status: itemForm.status }
        if (itemForm.id) {
          await requestApi(`/api/dict/items/${itemForm.id}`, { method: 'PUT', body: toJsonBody(payload) })
        } else {
          await requestApi(`/api/dict/items?setId=${itemFilter.setId}`, { method: 'POST', body: toJsonBody(payload) })
        }
        itemDialogOpen.value = false
        await loadItems()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }
    async function toggleItemStatus(row: DictItem) {
      const next = row.status === 'enabled' ? 'disabled' : 'enabled'
      try {
        await requestApi(`/api/dict/items/${row.id}/status`, { method: 'PUT', body: toJsonBody({ itemCode: row.itemCode, itemName: row.itemName, sort: row.sort, status: next }) })
        await loadItems()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }
    async function removeItem(row: DictItem) {
      try {
        await ElMessageBox.confirm('码值项只能停用，不能物理删除。是否将该项停用？', '提示', { type: 'warning' })
      } catch { return }
      try {
        await requestApi(`/api/dict/items/${row.id}`, { method: 'DELETE' })
        await loadItems()
      } catch (e) {
        notify(e instanceof Error ? e.message : String(e))
      }
    }

    // 初始化
    loadCategories()
    loadSets()
    loadSetOptions()

    return {
      activeTab,
      // category
      catKeyword, catLoading, categories, catDialogOpen, catForm,
      loadCategories, openCatEditor, saveCategory, removeCategory,
      // set
      setFilter, setPage, setTotal, setLoading, sets, setDialogOpen, setForm, setOptions,
      loadSets, querySets, openSetEditor, saveSet, toggleSetStatus, removeSet,
      openSetItems, loadSetOptions,
      // item
      itemFilter, itemLoading, items, itemDialogOpen, itemForm, filteredItems,
      loadItems, openItemEditor, saveItem, toggleItemStatus, removeItem,
    }
  },
})

export default DictPage
</script>

<style scoped>
.dict-tabs { padding: 0 16px; }
.model-toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.model-toolbar .muted { color: #909399; font-size: 12px; }
.model-search { min-width: 220px; }
.model-toolbar .filter-item { display: flex; align-items: center; gap: 8px; }
.model-pagination { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
