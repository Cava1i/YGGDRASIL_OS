# YGGDRASIL_OS 团队协作系统操作手册

## 1. 系统简介

YGGDRASIL_OS 面向 CTF / 电子数据取证比赛场景，提供比赛管理、题目导入、答案协作、Writeup 沉淀、附件管理和管理员控制台。YGGDRASIL 取自北欧神话中的世界树，也代表团队协作中多条线索向同一目标汇聚。

核心流程：

1. 管理员创建比赛行动。
2. 管理员或成员通过 Excel / 手动方式导入题目。
3. 团队成员在协作大表中提交答案、WP、备注和附件。
4. 系统统计答案一致率，并保留审计日志与附件下载入口。

## 2. 登录与注册

用户进入系统后会看到登录面板；新成员需要邀请码才能注册。

![image-20260511122436653](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122436653.png)

## 3. 控制中心

登录后进入控制中心，可快速进入比赛行动和题目上传页面。顶部导航展示当前用户和角色。

![image-20260511122504743](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122504743.png)

## 4. 比赛行动

比赛行动用于隔离不同比赛或训练场景。每个比赛拥有独立编码、题目集合和协作大表。

![image-20260511122551844](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122551844.png)

创建比赛：

![image-20260511122537466](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122537466.png)

操作说明：

- 点击“新建比赛”创建新的比赛行动。
- 点击比赛卡片进入该比赛的题目协作大表。
- 管理员可以删除比赛，删除前请确认数据已备份。

## 5. 题目上传与测试 Excel

系统支持两种题目录入方式：

- 手动上传单道题目。
- 上传 Excel 批量导入题目。

测试用例 Excel 已放在：

```text
docs/testdata/yggdrasil_sample_tasks.xlsx
```

Excel 说明：

- `Tasks` 工作表：用于批量建题，前两列为 `题目ID`、`题目内容`，可直接上传。
- `BatchUpdate` 工作表：用于演示批量回传答案、WP 和备注。
- `Readme` 工作表：说明字段含义。

![image-20260511122641893](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122641893.png)

## 6. 答题协作大表

协作大表是日常工作区，支持：

- 按题目 ID 和题目内容筛选。
- 提交答案。
- 提交 WP。
- 提交备注。
- 上传 WP 附件。
- 查看答案分布和最终候选答案。
- 导出数据矩阵。
- 下载提交模板并批量回传。

![image-20260511122742904](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122742904.png)

![image-20260511122831239](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511122831239.png)

## 7. 题目详情与附件下载

题目详情页用于查看单题内容、答案、WP、备注和附件。

![image-20260511123013989](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123013989.png)

![image-20260511123142804](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123142804.png)

## 8. 管理员战情室

管理员后台集中管理系统态势、用户、邀请码、比赛、附件、备份、配置和审计日志。

### 8.1 概览

![image-20260511123224291](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123224291.png)

### 8.2 用户管理

管理员可以查看已注册用户、修改角色、启用/禁用账号、重置密码。

当前管理员账号不能把自己降级为 `member`，也不能禁用自己，避免失去后台入口。

![image-20260511123236027](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123236027.png)

### 8.3 邀请码管理

管理员可以创建、启用、禁用邀请码，并设置使用次数和备注。

![image-20260511123244957](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123244957.png)



![image-20260511123314847](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123314847.png)

### 8.4 附件管理

后台附件页可以查看附件数量、占用空间、孤立附件，并下载附件。

![image-20260511123328760](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123328760.png)

### 8.5 系统配置与日志

管理员可以调整注册开关、默认角色、上传上限、会话有效期、普通用户权限和系统公告，并查看审计日志。

![image-20260511123342969](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123342969.png)

![image-20260511123350814](USER_MANUAL_GITHUB_TEMPLATE.assets/image-20260511123350814.png)
