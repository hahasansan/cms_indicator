# 指标结果查询接口文档

## 接口概述

查询指定指标在某一时间范围内的结果数据，支持：

- 多指标组合查询
- 日期范围过滤
- 维度筛选
- 字段映射（fieldMap）
- 分页返回

对应路由：

- GET /api/indicator-results

> 说明：本项目在后端统一挂载了 `/api` 前缀，实际访问地址通常为 `https://collage-rockstar-deluge.ngrok-free.dev/api/indicator-results`。

---

## 请求方式

```http
GET /api/indicator-results
```

---

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---:|---|
| indicatorIds | string | 否 | "" | 指标 ID 列表，多个以英文逗号分隔，例如 `101,102,103` |
| startDate | string | 否 | "" | 查询开始日期，格式 `YYYY-MM-DD` |
| endDate | string | 否 | "" | 查询结束日期，格式 `YYYY-MM-DD` |
| dimensionFilters | string | 否 | "" | 维度筛选条件 JSON 字符串，例如 `{ "region": "上海", "dept": "研发部" }` |
| fieldMap | string | 否 | "" | 返回字段映射 JSON 字符串，用于字段名转换或前端展示映射 |
| page | integer | 否 | 1 | 页码，从 1 开始 |
| pageSize | integer | 否 | 100 | 每页条数，范围 1-500 |

### 参数规范

1. `indicatorIds`
   - 允许传多个指标，使用英文逗号分隔。
   - 如果传入的指标 ID 不存在，接口将返回 `400` 错误：`存在不存在的指标`。

2. `startDate` / `endDate`
   - 仅接受 `YYYY-MM-DD` 格式。
   - 如果 `startDate > endDate`，接口返回 `400`：`数据日期起始日不能晚于结束日`。

3. `dimensionFilters`
   - 必须是有效 JSON 字符串。
   - 若 JSON 解析失败，将返回 `400`：`维度筛选条件格式错误`。
   - 接口内部会把值统一转为字符串并做 `lower()` 处理，以便进行大小写不敏感匹配。

4. `fieldMap`
   - 若不为空，必须是合法 JSON 对象。
   - 解析失败返回 `400`：`fieldMap 格式错误`。

---

## 返回结构

接口成功返回如下结构：

```json
{
  "indicators": [
    {
      "id": "1001",
      "name": "销售额",
      "code": "sales_amount",
      "unit": "元",
      "type": "number"
    }
  ],
  "rows": [
    {
      "indicatorId": "1001",
      "indicatorName": "销售额",
      "date": "2026-10-15",
      "region": "上海",
      "value": 123456.78
    }
  ],
  "page": 1,
  "pageSize": 100,
  "hasMore": false
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| indicators | array | 选中的指标列表信息 |
| rows | array | 当前页查询结果数据 |
| page | integer | 当前页码 |
| pageSize | integer | 每页大小 |
| hasMore | boolean | 是否还有下一页 |

---

## 示例请求

### 1）查询单个指标

```http
GET /api/indicator-results?indicatorIds=1001&startDate=2026-10-01&endDate=2026-10-31&page=1&pageSize=20
```

### 2）查询多个指标并过滤维度

```http
GET /api/indicator-results?indicatorIds=1001,1002&startDate=2026-10-01&endDate=2026-10-31&dimensionFilters=%7B%22region%22%3A%22%E4%B8%8A%E6%B5%B7%22%2C%22dept%22%3A%22%E7%A0%94%E5%8F%91%E9%83%A8%22%7D&page=1&pageSize=50
```

### 3）带字段映射

```http
GET /api/indicator-results?indicatorIds=1001&fieldMap=%7B%22date%22%3A%22statDate%22%2C%22value%22%3A%22resultValue%22%7D
```

---

## 错误响应

### 400 Bad Request

参数格式错误或业务校验失败，例如：

- `存在不存在的指标`
- `startDate 日期格式应为 YYYY-MM-DD`
- `endDate 日期格式应为 YYYY-MM-DD`
- `数据日期起始日不能晚于结束日`
- `维度筛选条件格式错误`
- `fieldMap 格式错误`

### 404 Not Found

该接口本身不使用 404 返回；但如果调用到单指标详情接口时，指标不存在会返回 404。

---

## 典型使用场景

- 查看某个指标在某段时间内的数据趋势
- 对比多个指标的结果数据
- 根据地区、部门、业务线等维度进行筛选
- 前端分页展示查询结果

---

## 备注

- 该接口返回的数据结构是分页结果，不保证一次返回全量数据。
- 结果数据的字段名称与 `fieldMap` 规则有关，实际返回内容可能按前端展示需要进行映射。
- 若未传 `indicatorIds`，接口会直接返回空结果：`{"indicators": [], "rows": [], "page": 1, "pageSize": pageSize, "hasMore": false}`。
