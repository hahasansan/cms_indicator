<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>度量公式管理</h1>
        <div class="desc">维护可复用的 SQL 公式模板。公式可按字段计算，再在指标配置中选择统计方式。</div>
      </div>
      <div class="actions"><el-button type="primary" @click="openCreate">新增公式</el-button></div>
    </div>

    <el-card shadow="never">
      <el-table :data="functions" v-loading="loading" empty-text="暂无公式">
        <el-table-column prop="name" label="公式名称" min-width="150" />
        <el-table-column prop="code" label="编码" width="170" />
        <el-table-column label="操作数" width="110">
          <template #default="{ row }">{{ row.parameterCount }} 个</template>
        </el-table-column>
        <el-table-column label="操作数含义" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ parameterSummary(row.parameters) }}
          </template>
        </el-table-column>
        <el-table-column prop="formula" label="公式模板" min-width="300" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogOpen" :title="editing ? '编辑公式' : '新增公式'" width="680px" append-to-body>
      <el-form label-width="100px">
        <el-form-item label="公式编码" required><el-input v-model="form.code" placeholder="例如 WEIGHTED_SUM" /></el-form-item>
        <el-form-item label="公式名称" required><el-input v-model="form.name" placeholder="例如 加权求和" /></el-form-item>
        <el-form-item label="SQL 公式" required>
          <div class="formula-editor">
            <div class="formula-toolbar">
              <div class="toolbar-row">
                <span class="toolbar-label">函数</span>
                <el-select v-model="selectedFunction" placeholder="选择函数" filterable class="function-select">
                  <el-option v-for="item in functionOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
                <el-button size="small" :disabled="!selectedFunction" @click="insertFunction">插入函数</el-button>
              </div>
              <div class="toolbar-row">
                <span class="toolbar-label">变量</span>
                <el-select v-model="selectedVariable" placeholder="选择字段变量" class="variable-select">
                  <el-option v-for="item in variableOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
                <el-button size="small" @click="insertText(selectedVariable)">插入变量</el-button>
              </div>
              <div class="toolbar-row">
                <span class="toolbar-label">系统占位符</span>
                <el-select v-model="selectedSystemPlaceholder" placeholder="选择系统内置占位符" class="variable-select">
                  <el-option v-for="item in systemPlaceholderOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
                <el-button size="small" :disabled="!selectedSystemPlaceholder" @click="insertText(selectedSystemPlaceholder)">插入占位符</el-button>
              </div>
              <div class="toolbar-row operator-row">
                <span class="toolbar-label">运算符</span>
                <el-button v-for="item in operatorOptions" :key="item.label" size="small" @click="insertText(item.value)">{{ item.label }}</el-button>
                <el-button size="small" @click="insertText('OVER (PARTITION BY ')">OVER</el-button>
                <el-button size="small" @click="insertText(' ORDER BY ')">ORDER BY</el-button>
              </div>
            </div>
            <textarea
              ref="formulaEditor"
              v-model="form.formula"
              class="formula-textarea"
              rows="4"
              placeholder="例如 SUM({1} * {2})；也可直接输入中文字段名"
            />
            <div v-if="currentFunctionDetail" class="function-detail-card">
              <div class="fd-header">
                <el-tag size="small" :type="fdTagType(currentFunctionDetail.category)" effect="plain">{{ currentFunctionDetail.category }}</el-tag>
                <span class="fd-name">{{ currentFunctionDetail.name }}</span>
                <span class="fd-syntax"><code>{{ currentFunctionDetail.syntax }}</code></span>
              </div>
              <div class="fd-desc">{{ currentFunctionDetail.desc }}</div>
              <div class="fd-params"><b>参数：</b>{{ currentFunctionDetail.params }}</div>
              <div v-if="currentFunctionDetail.example" class="fd-example">
                <b>示例：</b><code>{{ currentFunctionDetail.example }}</code>
              </div>
              <div v-if="currentFunctionDetail.note" class="fd-note">💡 {{ currentFunctionDetail.note }}</div>
            </div>
          </div>
        </el-form-item>
        <div class="formula-help">选择函数、字段变量、系统占位符或运算符后会插入到光标位置。字段变量编号须从 {1} 连续递增；也可直接输入中文字段名。若公式已包含聚合或窗口函数，指标统计方式请选择“不聚合”。</div>
        <el-form-item v-if="operandCount" label="操作数含义">
          <div class="parameter-editor">
            <div v-for="(_, index) in form.parameters" :key="index" class="parameter-row">
              <span class="parameter-token">{{ '{' + (index + 1) + '}' }}</span>
              <el-input v-model="form.parameters[index]" maxlength="32" :placeholder="`第 ${index + 1} 个字段的业务含义，例如：数量`" />
            </div>
            <div class="parameter-help">填写后会在「新增指标」选择该公式时，作为操作数标签提示每个字段代表什么。</div>
          </div>
        </el-form-item>
        <el-form-item label="公式说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api, jsonBody } from '../../api'
import type { MeasureFunction } from '../../types'

const notify = inject<(message: string) => void>('notify', () => undefined)
const functions = ref<MeasureFunction[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const editing = ref<MeasureFunction | null>(null)
const form = reactive({ code: '', name: '', formula: '', description: '', parameters: [] as string[] })
// 公式中的占位符数量：取 {n} 的最大编号
const operandCount = computed(() => {
  const numbers = [...form.formula.matchAll(/\{(\d+)\}/g)].map((match) => Number(match[1]))
  return numbers.length ? Math.max(...numbers) : 0
})
const parameterSummary = (parameters?: string[]) =>
  (parameters || []).filter((item) => item).join('、') || '未维护'
// 操作数含义数组长度随占位符数量自动同步，已填写的内容尽量保留
watch(operandCount, (count) => {
  const next = form.parameters.slice(0, count)
  while (next.length < count) next.push('')
  form.parameters = next
})
const formulaEditor = ref<HTMLTextAreaElement | null>(null)
const selectedFunction = ref('')
const selectedVariable = ref('{1}')
const selectedSystemPlaceholder = ref('')

// 选中函数的详细说明：从 functionDetailMap 查，不存在则返回通用说明
const currentFunctionDetail = computed<FunctionDetail | null>(() => {
  const value = selectedFunction.value.trim().toUpperCase()
  if (!value) return null
  return functionDetailMap[value] || {
    name: value, category: 'SQL 函数', syntax: `${value}(...)`,
    desc: `这是一个标准 SQL 函数：${value}`, params: '请参考函数文档',
    example: '', note: '',
  }
})
function fdTagType(category: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    '聚合函数': '', '空值处理': 'success', '字符串': 'info',
    '类型转换': 'warning', '条件分支': 'danger', '日期': '', '窗口函数': 'info', '数值计算': '',
  }
  return map[category] ?? ''
}

type FunctionDetail = {
  name: string; category: string; syntax: string; desc: string; params: string; example: string; note: string
}
const functionDetailMap: Record<string, FunctionDetail> = {
  // ========== 数值计算 ==========
  ABS:        { name: 'ABS',        category: '数值计算', syntax: 'ABS(n)',         desc: '返回 n 的绝对值（去掉负号）',                  params: 'n — 数值或表达式', example: 'ABS(-123)  → 123', note: '' },
  CEIL:       { name: 'CEIL',       category: '数值计算', syntax: 'CEIL(n)',        desc: '向上取整，返回大于等于 n 的最小整数',          params: 'n — 数值或表达式', example: 'CEIL(3.2)  → 4', note: '同义词：CEILING' },
  CEILING:    { name: 'CEILING',    category: '数值计算', syntax: 'CEILING(n)',     desc: '向上取整（同 CEIL）',                          params: 'n — 数值或表达式', example: 'CEILING(3.2) → 4', note: 'CEIL 的别名，写哪个都可以' },
  EXP:        { name: 'EXP',        category: '数值计算', syntax: 'EXP(n)',         desc: '返回自然常数 e（≈2.71828）的 n 次方',        params: 'n — 指数', example: 'EXP(1) → 2.71828', note: '' },
  FLOOR:      { name: 'FLOOR',      category: '数值计算', syntax: 'FLOOR(n)',       desc: '向下取整，返回小于等于 n 的最大整数',          params: 'n — 数值或表达式', example: 'FLOOR(3.9) → 3', note: '' },
  GREATEST:   { name: 'GREATEST',   category: '数值计算', syntax: 'GREATEST(a, b, …)', desc: '返回多个参数中最大的一个',                  params: '至少 2 个值', example: 'GREATEST({1}, 0) — 避免负数', note: '所有参数为 NULL 时返回 NULL' },
  LEAST:      { name: 'LEAST',      category: '数值计算', syntax: 'LEAST(a, b, …)',  desc: '返回多个参数中最小的一个',                    params: '至少 2 个值', example: 'LEAST({1}, 10000) — 封顶', note: '' },
  LN:         { name: 'LN',         category: '数值计算', syntax: 'LN(n)',          desc: '自然对数（以 e 为底）',                        params: 'n — 正数', example: 'LN(2.71828) → 1', note: 'n ≤ 0 会报错' },
  LOG:        { name: 'LOG',        category: '数值计算', syntax: 'LOG(n, base)',   desc: '返回以 base 为底的 n 的对数',                  params: 'n — 真数；base — 底数（默认 10 或 e）', example: 'LOG(1000, 10) → 3', note: '' },
  MOD:        { name: 'MOD',        category: '数值计算', syntax: 'MOD(a, b)',      desc: '取 a 除以 b 的余数',                          params: 'a — 被除数；b — 除数', example: 'MOD(10, 3) → 1', note: '达梦里除数为 0 会报错，建议配合 NULLIF 防御' },
  POWER:      { name: 'POWER',      category: '数值计算', syntax: 'POWER(a, n)',    desc: '返回 a 的 n 次方',                            params: 'a — 底数；n — 指数', example: 'POWER(2, 3) → 8', note: '' },
  ROUND:      { name: 'ROUND',      category: '数值计算', syntax: 'ROUND(n, d)',    desc: '四舍五入到 d 位小数',                        params: 'n — 数值；d — 小数位数（可选，默认 0）', example: 'ROUND(3.1415, 2) → 3.14', note: 'd 为负时按整数部分舍入，如 ROUND(1234, -2) → 1200' },
  SIGN:       { name: 'SIGN',       category: '数值计算', syntax: 'SIGN(n)',        desc: '返回 n 的符号：正数返回 1，负数返回 -1，零返回 0', params: 'n — 数值', example: 'SIGN(-5) → -1', note: '' },
  SIN:        { name: 'SIN',        category: '数值计算', syntax: 'SIN(x)',         desc: '正弦（x 为弧度）',                            params: 'x — 弧度值', example: 'SIN(0) → 0', note: '' },
  SQRT:       { name: 'SQRT',       category: '数值计算', syntax: 'SQRT(n)',        desc: '返回 n 的平方根',                            params: 'n — 非负数', example: 'SQRT(144) → 12', note: '负数会报错，建议用 GREATEST 防御' },
  TAN:        { name: 'TAN',        category: '数值计算', syntax: 'TAN(x)',         desc: '正切（x 为弧度）',                            params: 'x — 弧度值', example: 'TAN(0) → 0', note: '' },
  TRUNC:      { name: 'TRUNC',      category: '数值计算', syntax: 'TRUNC(n, d)',    desc: '截断，直接去掉多余小数位，不做四舍五入',      params: 'n — 数值；d — 小数位数', example: 'TRUNC(3.99, 1) → 3.9', note: '区别于 ROUND：TRUNC 直接截断，ROUND 会进位' },
  // ========== 聚合函数（自动忽略 NULL） ==========
  SUM:        { name: 'SUM',        category: '聚合函数', syntax: 'SUM(expr)',      desc: '对同一分组内的多行值求和',                    params: 'expr — 数值字段或表达式', example: 'SUM({1}) — 按维度汇总{1}', note: '聚合函数会对多行合并；如果公式里已经写了 SUM，BuilderPage 的统计方式请选「不聚合」' },
  AVG:        { name: 'AVG',        category: '聚合函数', syntax: 'AVG(expr)',      desc: '同一分组内所有值的算术平均值',                params: 'expr — 数值字段', example: 'AVG({1})', note: '自动忽略 NULL；需要区间日均请配合 {__BIZ_DAYS__} 使用' },
  MAX:        { name: 'MAX',        category: '聚合函数', syntax: 'MAX(expr)',      desc: '同一分组内的最大值',                          params: 'expr — 数值/日期/字符串', example: 'MAX({1})', note: '也可用于取最大日期' },
  MIN:        { name: 'MIN',        category: '聚合函数', syntax: 'MIN(expr)',      desc: '同一分组内的最小值',                          params: 'expr — 数值/日期/字符串', example: 'MIN({1})', note: '' },
  COUNT:      { name: 'COUNT',      category: '聚合函数', syntax: 'COUNT(expr)',    desc: '统计同一分组内行数',                          params: 'expr — 任意字段；COUNT(*) 统计总行数', example: 'COUNT({1}) — {1} 非空行数', note: 'COUNT(字段) 忽略 NULL，COUNT(*) 不忽略' },
  STDDEV:     { name: 'STDDEV',     category: '聚合函数', syntax: 'STDDEV(expr)',   desc: '标准差，反映数据离散程度',                    params: 'expr — 数值字段', example: 'STDDEV({1})', note: '' },
  VARIANCE:   { name: 'VARIANCE',   category: '聚合函数', syntax: 'VARIANCE(expr)', desc: '方差，标准差的平方',                          params: 'expr — 数值字段', example: 'VARIANCE({1})', note: '' },
  // ========== 空值处理 ==========
  COALESCE:   { name: 'COALESCE',   category: '空值处理', syntax: 'COALESCE(v1, v2, …)', desc: '返回参数列表中第一个非 NULL 的值',         params: '至少 2 个值', example: 'COALESCE({1}, 0) — {1} 为空时取 0', note: 'NVL 只能传 2 个，COALESCE 可传多个' },
  NANVL:      { name: 'NANVL',      category: '空值处理', syntax: 'NANVL(x, y)',    desc: '达梦/Oracle 专用：x 为 NULL 或 NaN 时返回 y', params: 'x — 原值；y — 默认值', example: 'NANVL({1}, 0)', note: '标准 SQL 建议用 NVL 或 COALESCE' },
  NULLIF:     { name: 'NULLIF',     category: '空值处理', syntax: 'NULLIF(a, b)',   desc: '若 a = b 则返回 NULL，否则返回 a',            params: 'a, b — 同类型值', example: 'NULLIF({2}, 0) — 分母为 0 时置空，防止除零', note: '除法分母场景最常用' },
  NVL:        { name: 'NVL',        category: '空值处理', syntax: 'NVL(x, y)',      desc: 'x 为 NULL 时返回 y，否则返回 x',              params: 'x — 原值；y — 默认值', example: 'NVL({1}, 0)', note: '达梦/Oracle 专用，标准 SQL 等价写法：COALESCE(x, y)' },
  NVL2:       { name: 'NVL2',       category: '空值处理', syntax: 'NVL2(x, y, z)',  desc: 'x 非 NULL 返回 y，x 为 NULL 返回 z',          params: 'x — 判定值；y — 非空返回；z — 为空返回', example: 'NVL2({1}, {1}*1.1, 0)', note: '达梦/Oracle 专用，标准 SQL 可用 CASE WHEN 改写' },
  // ========== 字符串 ==========
  INSTR:      { name: 'INSTR',      category: '字符串',   syntax: 'INSTR(s, sub)',   desc: 'sub 在 s 中第一次出现的位置（从 1 开始），未找到返回 0', params: 's — 原串；sub — 查找串', example: 'INSTR("ABCDE", "CD") → 3', note: '' },
  LENGTH:     { name: 'LENGTH',     category: '字符串',   syntax: 'LENGTH(s)',       desc: '字符串长度（达梦返回字符数）',                params: 's — 字符串', example: 'LENGTH("你好A") → 3', note: '多字节字符按字符计，不是字节' },
  LOWER:      { name: 'LOWER',      category: '字符串',   syntax: 'LOWER(s)',        desc: '全部转小写',                                    params: 's — 字符串', example: 'LOWER("ABC") → "abc"', note: '' },
  LTRIM:      { name: 'LTRIM',      category: '字符串',   syntax: 'LTRIM(s)',        desc: '去掉左侧空格',                                  params: 's — 字符串', example: 'LTRIM("  hi ") → "hi "', note: '' },
  REPLACE:    { name: 'REPLACE',    category: '字符串',   syntax: 'REPLACE(s, old, new)', desc: '把 s 中所有 old 替换为 new',              params: 's — 原串；old — 被替换；new — 替换成', example: 'REPLACE("{1}", " ", "") — 去所有空格', note: '' },
  RTRIM:      { name: 'RTRIM',      category: '字符串',   syntax: 'RTRIM(s)',        desc: '去掉右侧空格',                                  params: 's — 字符串', example: 'RTRIM("  hi ") → "  hi"', note: '' },
  SUBSTR:     { name: 'SUBSTR',     category: '字符串',   syntax: 'SUBSTR(s, pos, len)', desc: '从 s 的 pos 位置取 len 个字符',             params: 's — 原串；pos — 起始位置（从 1 开始，负数表示倒数）；len — 长度（可选）', example: 'SUBSTR("ABCDE", 2, 3) → "BCD"', note: '' },
  SUBSTRING:  { name: 'SUBSTRING',  category: '字符串',   syntax: 'SUBSTRING(s FROM pos FOR len)', desc: '取子串（同 SUBSTR，写法更标准）',    params: 's FROM pos FOR len', example: 'SUBSTRING("ABCDE" FROM 2 FOR 3) → "BCD"', note: '达梦也支持 SUBSTR，写哪个都行' },
  TRIM:       { name: 'TRIM',       category: '字符串',   syntax: 'TRIM(s)',         desc: '同时去掉左右两侧空格',                          params: 's — 字符串', example: 'TRIM("  hi ") → "hi"', note: '' },
  UPPER:      { name: 'UPPER',      category: '字符串',   syntax: 'UPPER(s)',        desc: '全部转大写',                                    params: 's — 字符串', example: 'UPPER("abc") → "ABC"', note: '' },
  // ========== 类型转换 ==========
  CAST:       { name: 'CAST',       category: '类型转换', syntax: 'CAST(x AS T)',    desc: '把 x 转为目标类型 T',                           params: 'x — 原值；T — 目标类型（NUMBER / VARCHAR / DATE 等）', example: 'CAST({1} AS VARCHAR2(20))', note: '达梦建议用 TO_NUMBER / TO_CHAR / TO_DATE' },
  TO_CHAR:    { name: 'TO_CHAR',    category: '类型转换', syntax: 'TO_CHAR(x, fmt)', desc: '日期→字符串 或 数值→字符串，并可格式化',      params: 'x — 日期/数值；fmt — 格式串（可选）', example: "TO_CHAR({1}, 'YYYY-MM-DD') — 日期转yyyy-mm-dd", note: '格式串用单引号' },
  TO_DATE:    { name: 'TO_DATE',    category: '类型转换', syntax: 'TO_DATE(s, fmt)', desc: '按 fmt 格式把字符串 s 解析成日期',            params: 's — 日期字符串；fmt — 格式串', example: "TO_DATE('20261101', 'YYYYMMDD')", note: '公式里业务时间参数用 TO_DATE 包一下' },
  TO_NUMBER:  { name: 'TO_NUMBER',  category: '类型转换', syntax: 'TO_NUMBER(s, fmt)', desc: '把字符串按 fmt 解析成数值',                  params: 's — 数值字符串；fmt — 格式串（可选）', example: 'TO_NUMBER("123.45") → 123.45', note: '字符串含非数字会报错，建议先用 NVL2 防御' },
  // ========== 条件分支 ==========
  DECODE:     { name: 'DECODE',     category: '条件分支', syntax: 'DECODE(v, k1, r1, k2, r2, …, def)', desc: '达梦/Oracle 的多分支条件，等价 CASE WHEN', params: 'v — 判定值；成对的 (key, result)；最后可跟默认值', example: 'DECODE({1}, 1, "正常", 0, "异常", "未知")', note: '标准 SQL 用 CASE WHEN 更清晰：CASE WHEN {1}=1 THEN "正常" WHEN {1}=0 THEN "异常" ELSE "未知" END' },
  // ========== 日期 ==========
  LAST_DAY:   { name: 'LAST_DAY',   category: '日期',     syntax: 'LAST_DAY(d)',     desc: '返回日期 d 所在月份的最后一天',                params: 'd — 日期', example: 'LAST_DAY(TO_DATE("2026-11-10", "YYYY-MM-DD")) → 2026-11-30', note: '适合取月末值' },
  MONTHS_BETWEEN: { name: 'MONTHS_BETWEEN', category: '日期', syntax: 'MONTHS_BETWEEN(d1, d2)', desc: '返回两个日期相差的月数', params: 'd1, d2 — 日期', example: 'MONTHS_BETWEEN(TO_DATE("2026-12-01", "YYYY-MM-DD"), TO_DATE("2026-06-01", "YYYY-MM-DD")) → 6', note: '返回值可为小数' },
  // ========== 窗口函数（必须配合 OVER (...) 使用） ==========
  DENSE_RANK: { name: 'DENSE_RANK',  category: '窗口函数', syntax: 'DENSE_RANK() OVER (PARTITION BY g ORDER BY k)', desc: '分组内按 k 排名，相同值同号，排名不跳号', params: 'PARTITION BY — 分组；ORDER BY — 排名依据', example: 'DENSE_RANK() OVER (ORDER BY {1} DESC)', note: 'RANK 跳号、DENSE_RANK 不跳号；窗口函数不能与 BuilderPage 聚合同时用，统计方式选「不聚合」' },
  LAG:        { name: 'LAG',         category: '窗口函数', syntax: 'LAG(expr, n, def) OVER (... desc 1', desc: '窗口内上一行的值',              params: 'expr — 取值表达式；n — 向前第几行（默认 1）；def — 首行时默认值', example: 'LAG({1}) OVER (ORDER BY DATA_DATE)', note: '适合算环比：{1} - LAG({1}) OVER (ORDER BY DATA_DATE)' },
  LEAD:       { name: 'LEAD',        category: '窗口函数', syntax: 'LEAD(expr, n, def) OVER (... desc 1', desc: '窗口内下一行的值',              params: 'expr — 取值表达式；n — 向后第几行；def — 末行默认值', example: 'LEAD({1}) OVER (ORDER BY DATA_DATE)', note: '' },
  LAST_VALUE: { name: 'LAST_VALUE',  category: '窗口函数', syntax: 'LAST_VALUE(expr) OVER (... desc 1', desc: '窗口内最后一个值',              params: 'expr — 取值表达式', example: 'LAST_VALUE({1}) OVER (ORDER BY DATA_DATE ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)', note: '需要指定窗口边界才能保证取到整个分区的最后一个' },
  NTH_VALUE:  { name: 'NTH_VALUE',   category: '窗口函数', syntax: 'NTH_VALUE(expr, n) OVER (... desc 1', desc: '窗口内第 n 行的值',              params: 'expr — 取值表达式；n — 第几行（从 1 开始）', example: 'NTH_VALUE({1}, 2) OVER (ORDER BY DATA_DATE)', note: '' },
  NTILE:      { name: 'NTILE',       category: '窗口函数', syntax: 'NTILE(n) OVER (... desc 1', desc: '把分区内行等分成 n 组，返回每组编号', params: 'n — 分组数', example: 'NTILE(4) OVER (ORDER BY {1}) — 四分位', note: '' },
  RANK:       { name: 'RANK',        category: '窗口函数', syntax: 'RANK() OVER (... desc 1', desc: '分组内排名，相同值同号且会跳号',   params: 'PARTITION BY — 分组；ORDER BY — 排名依据', example: 'RANK() OVER (ORDER BY {1} DESC)', note: '与 DENSE_RANK 的区别：若两个第一名，RANK 下一名为 3，DENSE_RANK 下一名为 2' },
  ROW_NUMBER: { name: 'ROW_NUMBER',  category: '窗口函数', syntax: 'ROW_NUMBER() OVER (... desc 1', desc: '给每行一个递增序号（不重复）',   params: 'PARTITION BY — 分组；ORDER BY — 排序', example: 'ROW_NUMBER() OVER (PARTITION BY {2} ORDER BY DATA_DATE)', note: '常用作去重：取 ROW_NUMBER() = 1 的行' },
}

const functionOptions = [
  // 数值计算
  { value: 'ABS', label: 'ABS 取绝对值' },
  { value: 'AVG', label: 'AVG 平均值（聚合）' },
  { value: 'CEIL', label: 'CEIL 向上取整' },
  { value: 'CEILING', label: 'CEILING 向上取整（同 CEIL）' },
  { value: 'COUNT', label: 'COUNT 计数（聚合）' },
  { value: 'EXP', label: 'EXP e 的 n 次方' },
  { value: 'FLOOR', label: 'FLOOR 向下取整' },
  { value: 'GREATEST', label: 'GREATEST 取多个值中最大' },
  { value: 'LEAST', label: 'LEAST 取多个值中最小' },
  { value: 'LN', label: 'LN 自然对数' },
  { value: 'LOG', label: 'LOG 对数' },
  { value: 'MAX', label: 'MAX 最大值（聚合）' },
  { value: 'MIN', label: 'MIN 最小值（聚合）' },
  { value: 'MOD', label: 'MOD 取余数' },
  { value: 'POWER', label: 'POWER 幂运算' },
  { value: 'ROUND', label: 'ROUND 四舍五入' },
  { value: 'SIGN', label: 'SIGN 符号函数（-1/0/1）' },
  { value: 'SIN', label: 'SIN 正弦' },
  { value: 'SQRT', label: 'SQRT 平方根' },
  { value: 'STDDEV', label: 'STDDEV 标准差（聚合）' },
  { value: 'SUM', label: 'SUM 求和（聚合）' },
  { value: 'TAN', label: 'TAN 正切' },
  { value: 'TRUNC', label: 'TRUNC 截断（不四舍五入）' },
  { value: 'VARIANCE', label: 'VARIANCE 方差（聚合）' },
  // 空值处理
  { value: 'COALESCE', label: 'COALESCE 返回第一个非空值' },
  { value: 'NANVL', label: 'NANVL 空值/NaN 返回默认值' },
  { value: 'NULLIF', label: 'NULLIF 两值相等则返回空' },
  { value: 'NVL', label: 'NVL 空值返回默认值' },
  { value: 'NVL2', label: 'NVL2 空值/非空分别返回不同值' },
  // 字符串
  { value: 'INSTR', label: 'INSTR 查找子串位置' },
  { value: 'LENGTH', label: 'LENGTH 字符长度' },
  { value: 'LOWER', label: 'LOWER 转小写' },
  { value: 'LTRIM', label: 'LTRIM 去前导空格' },
  { value: 'REPLACE', label: 'REPLACE 替换子串' },
  { value: 'RTRIM', label: 'RTRIM 去尾部空格' },
  { value: 'SUBSTR', label: 'SUBSTR 取子串' },
  { value: 'SUBSTRING', label: 'SUBSTRING 取子串（同 SUBSTR）' },
  { value: 'TRIM', label: 'TRIM 去前后空格' },
  { value: 'UPPER', label: 'UPPER 转大写' },
  // 类型转换
  { value: 'CAST', label: 'CAST 类型转换' },
  { value: 'TO_CHAR', label: 'TO_CHAR 转字符串/格式化日期' },
  { value: 'TO_DATE', label: 'TO_DATE 字符串转日期' },
  { value: 'TO_NUMBER', label: 'TO_NUMBER 字符串转数字' },
  // 条件分支
  { value: 'DECODE', label: 'DECODE 条件匹配（类似 CASE WHEN）' },
  // 日期
  { value: 'LAST_DAY', label: 'LAST_DAY 返回当月最后一天' },
  { value: 'MONTHS_BETWEEN', label: 'MONTHS_BETWEEN 两日期相隔月数' },
  // 窗口函数（排序/排名/相邻行访问）
  { value: 'DENSE_RANK', label: 'DENSE_RANK 排名（不跳号）' },
  { value: 'LAG', label: 'LAG 取上一行的值' },
  { value: 'LEAD', label: 'LEAD 取下一行的值' },
  { value: 'LAST_VALUE', label: 'LAST_VALUE 窗口内最后一个值' },
  { value: 'NTH_VALUE', label: 'NTH_VALUE 窗口内第 n 个值' },
  { value: 'NTILE', label: 'NTILE 等分成 n 组' },
  { value: 'RANK', label: 'RANK 排名（相同值并列，跳号）' },
  { value: 'ROW_NUMBER', label: 'ROW_NUMBER 行号' },
].map((item) => ({ ...item }))
const variableOptions = Array.from({ length: 25 }, (_, index) => {
  const value = `{${index + 1}}`
  return { value, label: `字段变量 ${value}` }
})
const systemPlaceholderOptions = [
  { value: '{__BIZ_DAYS__}', label: '{__BIZ_DAYS__} 业务区间天数（period=区间天数+1，balance=1）' },
]
const operatorOptions = [
  { label: '+', value: ' + ' },
  { label: '-', value: ' - ' },
  { label: '*', value: ' * ' },
  { label: '/', value: ' / ' },
  { label: '%', value: ' % ' },
  { label: '(', value: '(' },
  { label: ')', value: ')' },
  { label: ',', value: ', ' },
]

async function insertText(text: string, cursorOffset = text.length) {
  const editor = formulaEditor.value
  const start = editor?.selectionStart ?? form.formula.length
  const end = editor?.selectionEnd ?? start
  form.formula = `${form.formula.slice(0, start)}${text}${form.formula.slice(end)}`
  await nextTick()
  editor?.focus()
  editor?.setSelectionRange(start + cursorOffset, start + cursorOffset)
}

function insertFunction() {
  if (!selectedFunction.value) return
  const text = `${selectedFunction.value}()`
  void insertText(text, text.length - 1)
}

async function load() {
  loading.value = true
  try {
    functions.value = await api<MeasureFunction[]>('/api/measure-functions')
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { code: '', name: '', formula: '', description: '', parameters: [] })
  selectedFunction.value = ''
  selectedVariable.value = '{1}'
  selectedSystemPlaceholder.value = ''
  dialogOpen.value = true
}

function openEdit(row: MeasureFunction) {
  editing.value = row
  Object.assign(form, {
    code: row.code,
    name: row.name,
    formula: row.formula,
    description: row.description || '',
    parameters: [...(row.parameters || [])],
  })
  selectedFunction.value = ''
  selectedVariable.value = '{1}'
  dialogOpen.value = true
}

async function save() {
  if (!form.code.trim() || !form.name.trim() || !form.formula.trim()) {
    notify('请填写公式编码、名称和 SQL 公式')
    return
  }
  saving.value = true
  try {
    const path = editing.value ? `/api/measure-functions/${editing.value.id}` : '/api/measure-functions'
    const body = {
      code: form.code,
      name: form.name,
      formula: form.formula,
      description: form.description,
      parameters: form.parameters.map((item) => (item || '').trim()),
    }
    await api(path, { method: editing.value ? 'PUT' : 'POST', body: jsonBody(body) })
    notify('度量公式已保存')
    dialogOpen.value = false
    await load()
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  } finally {
    saving.value = false
  }
}

async function remove(row: MeasureFunction) {
  try {
    await ElMessageBox.confirm(`确定删除公式「${row.name}」？已被指标引用的公式不能删除。`, '删除公式', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api(`/api/measure-functions/${row.id}`, { method: 'DELETE' })
    notify('度量公式已删除')
    await load()
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}

onMounted(load)
</script>

<style scoped>
.formula-help {
  margin: -8px 0 14px 100px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

.formula-editor {
  width: 100%;
}

.parameter-editor {
  display: grid;
  gap: 6px;
  width: 100%;
}

.parameter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.parameter-token {
  flex: none;
  min-width: 38px;
  padding: 0 6px;
  border-radius: 4px;
  background: #eef5fb;
  color: #2c5879;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  text-align: center;
  line-height: 24px;
}

.parameter-help {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.formula-toolbar {
  display: grid;
  gap: 8px;
  margin-bottom: 10px;
}

.toolbar-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.toolbar-label {
  width: 46px;
  color: var(--muted);
  font-size: 12px;
}

.function-select {
  width: 190px;
}

.variable-select {
  width: 160px;
}

.formula-textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 96px;
  padding: 8px 11px;
  color: var(--el-input-text-color, var(--el-text-color-regular));
  background: var(--el-input-bg-color, var(--el-fill-color-blank));
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-input-border-radius, var(--el-border-radius-base));
  font: inherit;
  line-height: 1.5;
  resize: vertical;
}

.formula-textarea:focus {
  border-color: var(--el-color-primary);
  outline: none;
}
.function-detail-card {
  margin-top: 10px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1px solid #dce7f5;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.55;
}
.function-detail-card .fd-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.function-detail-card .fd-name {
  font-size: 13px;
  font-weight: 700;
  color: #1d3a6b;
  letter-spacing: 0.3px;
}
.function-detail-card .fd-syntax code {
  background: #eaf2ff;
  color: #1d3a6b;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-family: Consolas, "Menlo", monospace;
}
.function-detail-card .fd-desc {
  color: #3d4a5c;
  margin-bottom: 4px;
}
.function-detail-card .fd-params {
  color: #4a5568;
  margin-bottom: 2px;
}
.function-detail-card .fd-example {
  margin-top: 4px;
}
.function-detail-card .fd-example code {
  display: inline-block;
  margin-top: 2px;
  background: #f5f7fa;
  color: #2c3e50;
  padding: 3px 8px;
  border-radius: 3px;
  font-family: Consolas, "Menlo", monospace;
  font-size: 11px;
  border-left: 2px solid #409eff;
}
.function-detail-card .fd-note {
  margin-top: 6px;
  padding: 4px 8px;
  background: #fff8e7;
  color: #9a6a00;
  border-radius: 3px;
  font-size: 11.5px;
}
</style>
