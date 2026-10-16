<template>
  <div class="indicator-tree-node">
    <div class="indicator-tree-row" :style="{ paddingLeft: `${level * 16 + 8}px` }">
      <button v-if="node.children.length" class="tree-toggle" type="button" @click="toggleExpanded" :aria-label="expanded ? '收起' : '展开'">{{ expanded ? '⌄' : '›' }}</button>
      <span v-else class="tree-toggle-spacer"></span>
      <div v-if="node.indicatorId" class="tree-check">
        <el-checkbox :model-value="selectedIds.includes(node.indicatorId)" @change="(checked: boolean) => emit('select', node.indicatorId!, checked)" class="tree-checkbox">
          <span class="tree-label"><b>{{ node.label }}</b><small>{{ node.code }}<template v-if="node.categoryName"> · {{ node.categoryName }}</template></small></span>
        </el-checkbox>
      </div>
      <button v-else class="tree-folder" type="button" @click="toggleExpanded"><b>{{ node.label }}</b><small>{{ node.children.length }} 项</small></button>
    </div>
    <div v-if="expanded && node.children.length" class="indicator-tree-children">
      <IndicatorTreeNode v-for="child in node.children" :key="child.id" :node="child" :level="level + 1" :selected-ids="selectedIds" @toggle="forwardToggle" @select="forwardSelect" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { IndicatorTreeNode as TreeNode } from '../types'

const props = withDefaults(defineProps<{ node: TreeNode; level?: number; selectedIds: string[] }>(), { level: 0 })
const emit = defineEmits<{ toggle: [id: string]; select: [id: string, checked: boolean] }>()
const expanded = ref(true)

function toggleExpanded() { expanded.value = !expanded.value }
function forwardToggle(id: string) { emit('toggle', id) }
function forwardSelect(id: string, checked: boolean) { emit('select', id, checked) }
</script>

<style scoped>
.indicator-tree-row {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding-right: 8px;
}

.indicator-tree-row:hover {
  background: #f3f8fc;
}

.tree-toggle,
.tree-toggle-spacer {
  width: 24px;
  height: 26px;
  flex: 0 0 24px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 17px;
}

.tree-check {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
}

.tree-check input {
  width: 15px;
  height: 15px;
  accent-color: var(--brand);
}

.tree-label {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.tree-label b,
.tree-label small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-label b {
  color: var(--ink);
  font-size: 13px;
}

.tree-label small {
  color: var(--muted);
  font-size: 11px;
}

.tree-folder {
  min-width: 0;
  border: 0;
  background: transparent;
  display: grid;
  gap: 2px;
  text-align: left;
  color: var(--brand);
  padding: 4px 0;
}

.tree-folder small {
  color: var(--muted);
  font-size: 11px;
  font-weight: 400;
}
</style>
