# 鹤山北控水务 Home Assistant 集成
![Version](https://img.shields.io/badge/version-v1.0.0-blue)
![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.5%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 简述： 
HA上查看抄表读数、欠费、计费水量等信息。  
  
## 传感器列表 
生成如下传感器实体：户名、水表地址、本期抄表日期、上期抄表日期、本期读数、上期读数、计费水量、欠费金额、缴费状态、计费月份以及Token有效状态监控，数据是最近抄表月份的数据。


## 功能特点

* ✅ 自动登录获取 Token，无需手动填写动态令牌
* ✅ 支持灵活的数据更新频率：小时、天、周、月
* ✅ 提供欠费金额、上期/本期读数、计费月份、缴费状态等传感器

## 安装

### 方法 1：HACS 安装（推荐）
1. 打开 HACS → 集成
2. 点击右上角 `⋮` → 自定义存储库
3. 输入仓库地址：https://github.com/codepriince/heshan_water
4. 类别选择 `集成`
5. 搜索并安装 “鹤山北控水务”

### 方法 2：手动安装
```bash
# 下载后复制到 custom_components 目录
cp -r heshan_water ~/.homeassistant/custom_components/
```

## 配置

### 第一步：获取认证参数
登录微信 **鹤山北控水务** 小程序，使用抓包工具获取以下参数：

| 参数 | 说明 | 抓包来源 |
|------|------|----------|
| `username` | 用户名 | 请求体 (`username=xxx`) |
| `password` | 密码 | 请求体 (`password=xxx`) |
| `open_id` | 用户唯一标识 | 请求体 (`open_id=xxx`) |

> **注意：** `open_id` 是小程序分配给当前微信用户的固定 ID，更换微信账号后需要重新获取。

### 第二步：添加集成
1. 在 Home Assistant 中进入 **设置 → 设备与服务 → 添加集成**
2. 搜索 **鹤山北控水务**
3. 填写用户名、密码、open_id
4. 选择数据更新频率（默认为每小时更新一次）
5. 点击提交，集成会立即验证并抓取数据

## 传感器

安装后会自动创建以下传感器实体：

| 传感器名称 | 实体 ID（示例） | 说明 | 单位 |
|------------|----------------|------|------|
| 表地址 | `sensor.he_shan_bei_kong_shui_wu_he_shan_biao_di_zhi` | 水表安装地址 | — |
| 户名 | `sensor.he_shan_bei_kong_shui_wu_he_shan_hu_ming` | 用水户姓名 | — |
| 欠费金额 | `sensor.he_shan_bei_kong_shui_wu_he_shan_qian_fei_jin_e` | 当前未缴纳的水费 | 元 |
| 本期抄表日期 | `sensor.he_shan_bei_kong_shui_wu_he_shan_ben_qi_chao_biao_ri_qi` | 最近一次抄表日期 | — |
| 上期抄表日期 | `sensor.he_shan_bei_kong_shui_wu_he_shan_shang_qi_chao_biao_ri_qi` | 上一次抄表日期 | — |
| 本期读数 | `sensor.he_shan_bei_kong_shui_wu_he_shan_ben_qi_du_shu` | 本期水表读数 | m³ |
| 上期读数 | `sensor.he_shan_bei_kong_shui_wu_he_shan_shang_qi_du_shu` | 上期水表读数 | m³ |
| 计费月份 | `sensor.he_shan_bei_kong_shui_wu_he_shan_ji_fei_yue_fen` | 最新账单对应的月份 | — |
| 计费水量 | `sensor.he_shan_bei_kong_shui_wu_he_shan_ji_fei_shui_liang` | 本期结算用水量 | m³ |
| 缴费状态 | `sensor.he_shan_bei_kong_shui_wu_he_shan_jiao_fei_zhuang_tai` | 最新账单缴费状态 | — |
| Token 状态 | `sensor.he_shan_bei_kong_shui_wu_he_shan_token_zhuang_tai` | 当前 Token 是否有效 | — |


## 配置选项

| 更新模式 | 说明 | 示例值 |
|----------|------|--------|
| 小时 | 每 N 小时更新一次 | 1、2、6、12、24 |
| 天 | 每天指定时间更新 | 每天 08:00（填 8） |
| 周 | 每周指定星期几更新 | 每周一（填 1）、周三（3） |
| 月 | 每月指定日期更新 | 每月 1 日、15 日 |




## 故障排除

### 无法连接或认证失败
* 检查 Home Assistant 主机能否访问 `http://XXX.XXX.XXX.XXX:端口号`（可在HA终端使用命令 `curl http://XXX.XXX.XXX.XXX:端口号` 测试）。
* 确认用户名、密码、open_id 完全与抓包时一致。
* 查看 HA 日志（配置 → 系统 → 日志），搜索 `heshan_water` 获取详细错误信息。

### 数据不更新
* 确认 Token 状态传感器显示“有效”。
* 检查更新频率设置是否正确（如设置为每月 31 日，则无该日不更新）。



## 更新日志

### v1.0.0
* 🚀 自动获取 Token 功能，无需手动填写动态令牌
* ✨ 支持灵活的数据更新频率（小时/天/周/月）
* ✨ Token 状态监控传感器





