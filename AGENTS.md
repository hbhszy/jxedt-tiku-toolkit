# AGENTS.md - 驾校一点通题库工程智能体协作指南

> 本文件是本项目（驾校一点通题库逆向提取、解密清洗与智能备考系统）的核心架构规范与 Agent 协作指南。所有自动化 Agent、开发者在执行维护、更新、二次开发时应严格遵循本规范。

---

## 一、 项目背景与架构概览

本项目针对《驾校一点通》桌面客户端（基于 Electron + Vue + SQLite）进行题库资源的逆向提取、解密还原、结构化清洗与备考衍生工具开发。

### 1. 技术栈
* **核心语言**：Python 3.10+（主环境 Python 3.14+）
* **数据处理与导出**：SQLite3、Pandas、OpenPyXL、python-docx
* **文档与渲染**：Headless Edge / Chrome (`--headless=new --print-to-pdf`)、Markdown
* **前端交付物**：纯原生 HTML5 + CSS3 + Vanilla ES6（零外部 CDN 依赖，纯单文件离线运行）

### 2. 核心目录与文件地图
```text
D:\Program Files (x86)\jxedt\
├── app\node_modules\bak\question_banks\
│   └── xc.db                               # [数据源] 云端下载的最新题库（小车 xc，明文考题，含全网错率与视频链接）
├── resources\app\db\
│   └── jxedt_user.db                       # [数据源] 原厂内置数据库（全车型3.5万题，含官方详解，XOR加密）
├── resources\app\dist\electron\
│   └── renderer.js                         # [业务源] 软件核心渲染与逻辑代码（包含解密函数与抽题算法）
├── tiku_pipeline.py                        # [核心脚本] 题库全自动解密、提取、清洗与多格式导出流水线
├── 题库提取与更新全流程方案.md             # [方案文档] 详细逆向方案与字段规格文档
├── 题库导出\                               # [全局导出] 全量题库（含各车型、全省市合订版）
├── 科目一_无锡备考冲刺包\                   # [学员交付物] 针对无锡考区科目一的高效冲刺专用文件夹
│   ├── 00_【请先读我】无锡科目一备考通关指南.txt
│   ├── 01_【离线刷题神器】无锡科目一_易错题智能刷题器(双击直接练).html
│   ├── 02_【考前必背手册】科目一核心速记口诀与必背考点.pdf
│   ├── 02_【考前必背手册】科目一核心速记口诀与必背考点.docx
│   ├── 03_【无锡考区必考】视频快处与急救特产题(74题).xlsx
│   ├── 04_【精选提分题表】全网高频易错题集(767题).xlsx
│   └── 05_【全量题库备查】无锡全考题对照表(2413题).xlsx
├── AGENTS.md                               # 本协作规范
└── CLAUDE.md                               # Claude 路由与运行指南
```

---

## 二、 核心逆向解密标准（Cryptographic Specs）

原厂数据库 `jxedt_user.db` 对文本字段采用流式循环异或加密，Agent 在读取解析字段时必须通过以下标准实现还原：

```python
SECRET_KEY = b"jxedt_pc_client_secret"

def decrypt_val(val):
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, (bytes, bytearray)):
        out = bytearray(len(val))
        for i in range(len(val)):
            out[i] = val[i] ^ SECRET_KEY[i % len(SECRET_KEY)]
        try:
            return out.decode("utf-8")
        except UnicodeDecodeError:
            return out.decode("gb18030", errors="ignore")
    return str(val)
```

---

## 三、 数据模型与城市过滤规则

### 1. `web_note` 关键字段
* `ID`: 题目唯一主键
* `kemu`: `1` (科目一), `2` (科目二常识), `4` (科目四)
* `Type`: `1` (判断题), `2` (单选题), `3` (多选题)
* `AnswerTrue`: 答案编码（`1`~`4` -> A~D；多选为组合如 `124` -> ABD）
* `error_rate`: 全网学员真实答错率（浮点数 0.0 ~ 1.0）
* `cityid`: `0` 为全国通用题；`>0` 为各省市代码

### 2. 城市题目过滤算法
客户端呈现给考生的题量由“全国通用题”加上“省市地方题”合并构成：
```sql
SELECT * FROM web_note
WHERE kemu = :kemu
  AND (',' || gs || ',') LIKE '%,' || :car_type || ',%'
  AND (category IS NULL OR category IN (0, 1, 2))
  AND cityid IN (0, :province_id, :city_id)
ORDER BY CAST(strTppe AS INT) ASC, ID ASC;
```
* **无锡考区参数**：`car_type = 'xc'`, `province_id = 25` (江苏省), `city_id = 182` (无锡市)。
  * 全国题 2,339 + 地方题 74 = **2,413 题**。

---

## 四、 常用 Agent 任务指令

### 1. 题库全自动更新流水线
当客户端下载了新版本题库包后，执行：
```powershell
python "D:\Program Files (x86)\jxedt\tiku_pipeline.py"
```
* **提取摩托车**：`python tiku_pipeline.py --car mtc`
* **提取货车**：`python tiku_pipeline.py --car hc`

### 2. 重新编译生成离线刷题器（HTML）
```powershell
python "C:\Users\Zhanying\.gemini\antigravity\brain\a30f0404-5717-421f-b69b-e500636a3228\scratch\deploy_categorized_apps.py"
```

### 3. 生成高清 PDF 考点手册
```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="D:\Program Files (x86)\jxedt\科目一_无锡备考冲刺包\02_【考前必背手册】科目一核心速记口诀与必背考点.pdf" "C:\Users\Zhanying\.gemini\antigravity\brain\a30f0404-5717-421f-b69b-e500636a3228\scratch\mnemonic_handbook.html"
```

---

## 五、 开发与交付约束（Guidelines for Agents）

1. **零外部依赖原则**：
   * 导出的离线交互式 HTML 刷题器必须保持**单文件自包含（Self-Contained）**，禁止引入外部 JS/CSS 库（如 CDN vue、bootstrap），确保双击在任何离线电脑或移动端均能秒开。
2. **编码统一标准**：
   * 所有导出的 CSV 必须使用 `utf-8-sig`（带 BOM），确保 Microsoft Excel 与 WPS 打开不出现乱码。
   * JSON 与 Python 源码统一使用 `utf-8`。
3. **保护原厂可执行程序**：
   * 严禁修改或破坏 `resources.pak`、`jxedt.exe` 及相关动态链接库（DLL），所有分析与提取工作只针对数据库及纯文本资源进行。
