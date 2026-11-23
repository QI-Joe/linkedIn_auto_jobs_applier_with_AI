# JobsDB 与 LinkedIn 本地申请准备工具

两个平台共用本机职位档案。采集时先保存每张可识别的卡片，再补充详情。推荐读取历史记录，可按新的求职偏好反复排序。外部、未知或已申请的职位同样留档，申请材料只为确认的 JobsDB Quick Apply 或 LinkedIn Easy Apply 职位准备。当前命令行停在人工审阅。

## 采集一次，之后从历史推荐

默认数据库是 `data_folder/job_history.sqlite3`。各命令都接受 `--history` 指向同一个私有 SQLite 文件。数据库由 Python 标准库管理，采集与推荐分别运行。不同用户应使用各自的库。

1. **浏览器采集。** 安装下文的 Python 依赖与 Chrome，在本机 Chrome 专用用户目录中完成需要的登录，关闭占用该目录的浏览器。将命令里的示例地址替换为实际打开的搜索结果页。采集会打开该页当前可识别的职位卡片及同站详情；多页搜索可重复传入 `--url`。详情超时或身份不一致时，已读取的卡片仍在库中。使用 Selenium 时需要可用的 ChromeDriver 或能由 Selenium Manager 获取匹配驱动的环境。
2. **已有数据。** 有保存过的列表、详情或旧 JobsDB 每日日志时，用下方相应命令导入本机实际存在的文件，相应选项均可单独使用。旧日志混有翻页事件时只导入职位记录。无需为日常推荐重新复制网页元素。
3. **查看推荐。** 最后一条命令只需要结构化 CV、偏好和已有职位库，无需浏览器、简历附件或 Writer。打开终端输出的批次 JSON，在 `recommendations` 中查看排名、理由和 `onsite_eligible`。可选的 `--resume` 会为排名范围内符合站内申请条件的职位另存材料，此时需要 Writer 和 Poppler。

```text
python main.py collect --url "https://hk.jobsdb.com/ai-engineer-jobs" --browser-profile "data_folder/collection-profile"
python main.py collect --snapshot markdown/Jobsdb.md --snapshot markdown/Linkedin.md --detail markdown/webResource/jobsdb_element/Jobsdb_general_single_board.md
python main.py collect --legacy-log "job_apply_logs"
python main.py recommend --cv data_folder/cv.yaml --profile data_folder/preferences.yaml --top 5
```

`jobs` 表以平台和职位 ID 为键，记录首次、最近观察时间及合并后的字段。`observations` 保存各来源的不同版本，重读简略卡片不会抹掉已取得的详情。历史记录代表曾经看到的内容，申请前仍需核实职位是否开放。[采集入口](src/preparation/collect.py) · [职位档案](src/preparation/history.py)

查看已存的职位可运行 `python main.py history`。从清单取出实际的平台和 ID，再运行 `python main.py history --platform linkedin --job-id 12345` 查看该条完整记录。LinkedIn 详情披露的公司介绍保存在 `platform_specific_data.company_description`；JobsDB 旧日志的分段内容保存在 `platform_specific_data.sections`。缺少 ID 的可识别卡片按内容指纹留档，不进入申请。

LinkedIn 公开列表可直接读取公开职位和详情，未披露申请方式的职位先留档。JobsDB 如显示站点验证页，请先在本机正常浏览器中完成验证再采集。有关未来外站表单 Agent 的源码评估见[克隆与接入方案](markdown/external_application_agent_research.md)。

## 第一次在本地测试

先把**包含本次改动的项目版本**同步到电脑，在有 `main.py` 和 `requirement.txt` 的项目根目录打开终端。以下命令使用 Conda 和 Python 3.10。已有 `base28` 环境时可以跳过创建步骤。请使用单数的 `requirement.txt` 安装离线流程依赖。

```text
conda create -n base28 python=3.10 pip -y
conda activate base28
python -m pip install -r requirement.txt
```

### Ubuntu 服务器或桌面

Writer 将 Word 陈述实际排版为 PDF，Poppler 检查页数并读取末段文字。服务器可以无桌面运行。

```bash
sudo apt update
sudo apt install libreoffice-writer poppler-utils
soffice --version
pdfinfo -v
pdftotext -v
python checks/check_preparation.py
```

### Windows 64 位电脑

在可使用 Conda 的 PowerShell 中激活上述环境，用 conda-forge 安装 Poppler。安装含 Writer 的 Windows 版 LibreOffice 后，设置下方的路径。自定义安装位置时将第一行改为实际路径。[LibreOffice 下载](https://www.libreoffice.org/download/download-libreoffice/) · [Windows 命令行入口](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html) · [conda-forge 的 Poppler 包](https://anaconda.org/conda-forge/poppler)

```powershell
$office = "C:\Program Files\LibreOffice\program\soffice.com"
conda install -n base28 -c conda-forge poppler -y
& $office --version
pdfinfo -v
pdftotext -v
python checks/check_preparation.py --office "$office"
```

### `checks/` 检查什么

[验收脚本](checks/check_preparation.py) 从 [虚构网页样本](checks/fixtures/) 读取 HTML，在临时目录创建虚构简历、求职偏好和答案，然后调用实际入口 `main.py`。本节验收需要本机有 checks/ 脚本、测试样本和上述依赖。生产采集和历史推荐独立于该目录。请用普通 Python 模式运行，脚本依赖断言。

| 运行场景 | 通过时应观察到的行为 |
| --- | --- |
| JobsDB，已确认 7 个答案 | 生成 1 份材料，演练到第 4 步。审阅页的附件信息仍需人工核对。 |
| JobsDB，移除 1 个答案后重跑 | 另存 1 个版本，在第 2 步暂停。原简历和上一版材料保持完整。 |
| LinkedIn，每日候选上限 20、优先 5 | 最多列出 5 个推荐职位，跳过已申请职位；只为具备站内申请资格的候选生成材料。 |
| 每份材料 | 核对简历副本、文件哈希、职位与陈述的对应关系、导出 PDF 的实际页数，以及记录中的 `submitted: false`。 |

成功时，最后一行是 **`离线验收通过`**。默认退出后清理临时材料。想打开生成的 Word、PDF 或 JSON 时，在命令末尾加 `--output "data_folder/check-output"`。Ubuntu 24.04 已通过虚构样本和工作区现有网页样本两套验收，原生 Windows 的运行结果尚待实机验证。

## 使用自己的材料

从历史推荐需要 CV 和偏好两份 YAML；演练申请或生成材料时再提供简历原件。示例使用本机的 `data_folder/`，YAML 用 UTF-8 保存。网页可以继续使用随附的虚构样本。

| 输入 | 需要准备的内容 |
| --- | --- |
| `--resume` | 可读取的简历原件，PDF 或 DOCX 均可。程序复制原件到每个职位的版本目录。 |
| `--cv` | 结构化履历 YAML。至少写一条可引用的 `projects[].description` 或 `experience_details[].key_responsibilities`。程序据此生成英文个人陈述，建议提供可直接引用的英文经历。 |
| `--profile` | 求职偏好和本人确认的答案 YAML。题干按网页原文填写，多选题用列表。薪资、工作权、语言等答案应由本人确认。缺少答案时可先查看暂停原因。 |

### 网页样本何时用到

开发时，保存的 HTML 用于定位页面元素和回归测试。已有样本也可作为一次性导入来源。运行推荐时会从历史库取数；要补充新的职位，可运行浏览器采集或再导入一份列表。仅在复现某个页面解析问题时需要对应网页片段。

| 离线模式 | 该模式读取的网页数据 |
| --- | --- |
| JobsDB 单职位演练 | 一份含标题、公司、描述和 Quick Apply 链接的详情 HTML，以及同一职位的四步页面片段。步骤目录内每步各有一个以 `step1.md` 至 `step4.md` 结尾的文件。 |
| LinkedIn 职位推荐 | 搜索页快照首行为页面 URL，第二行起为复制的元素 HTML。选中职位的 ID 来自 URL 的 `currentJobId`。导入时可选的 Easy Apply 样本目录包含 `easy_apply_step1.md` 至 `easy_apply_step4.md`；第 3 步片段仅能验证提交文字。 |

评分与排序由 `evaluate()` 和 `daily_ranking()` 完成。批次 JSON 的 `recommendations` 列出优先职位，`results` 记录成功生成的材料包。JobsDB 单职位演练对传入的详情单独核验。[推荐入口](prepare_jobs.py) · [匹配与排序](src/preparation/matching.py)

### 个人文件示例

最小的 `data_folder/cv.yaml` 示例。使用时替换为真实经历。

```yaml
projects:
  - name: Search evaluation
    description: I built a Python tool to evaluate search results.
```

最小的 `data_folder/preferences.yaml` 示例。空答案可用于测试人工确认流程。

```yaml
positions: ["Engineer"]
locations: ["Hong Kong"]
skills: ["Python"]
answers: {}
applied: {}
```

先将原简历放在 `data_folder/resume.pdf`，再用随附样本运行下面任一条命令。在 Windows 的同一 PowerShell 会话中，每条材料准备命令末尾加上 `--office "$office"`。之后可把 `--detail`、`--steps`、`--snapshot` 换成本机的其他样本。

```text
python main.py jobsdb --detail checks/fixtures/webResource/jobsdb_element/Jobsdb_general_single_board.md --steps checks/fixtures/webResource/jobsdb_element --cv data_folder/cv.yaml --profile data_folder/preferences.yaml --resume data_folder/resume.pdf
python main.py recommend --snapshot checks/fixtures/Linkedin.md --easy-apply-steps checks/fixtures/webResource/linkedin_element --target 20 --top 5 --cv data_folder/cv.yaml --profile data_folder/preferences.yaml --resume data_folder/resume.pdf
```

运行后先打开终端打印的批次 JSON，按 `packages` 的相对路径进入 `data_folder/output/<日期>/<平台>/<职位ID>/v-…/`。其中 `manifest.json` 记录职位、版本、材料哈希和待确认项，`answers.json` 记录问答，`Personal Statement.docx` 可编辑，旁边的 PDF 可检查最终排版。每次重跑会生成新版本。

## 本地出错后如何在服务器复现

1. 在两端切换到含同一修改的代码版本，用 `git rev-parse --short HEAD` 和 `git status --short` 核对提交和未提交改动。同步代码时包含 `checks/check_preparation.py` 与 `checks/fixtures/`。每台机器单独安装依赖。
2. 先在两端运行各自的虚构样本验收。若都通过，再复测具体网页。当前工作区已有原始样本，使用 `python checks/check_preparation.py --samples markdown`（Windows 加 `--office "$office"`）。此验收的题目、数量和页面标记针对这组固定样本。其他职位请用上节的 `main.py` 命令检查。忽略的 `markdown/` 数据不会随普通 Git 克隆同步。
3. 回报问题时附上系统、`python --version`、Writer 和 Poppler 的版本、使用的子命令、完整错误类型和失败步骤。路径中的用户名可替换成占位符。如果只有某个网页失败，提供能复现的最小脱敏元素。原简历、答案、Cookie、带个人信息的原页或完整输出目录留在本机。
4. 收到服务器修复后，本地同步同一版本，先重跑虚构样本，再重跑先前失败的命令。若报告中有 `needs_confirmation`，先看 `issues` 和未确认题目；验收用例本身也会验证这种预期暂停。

| 现象 | 排查入口 |
| --- | --- |
| 提示模块缺失 | 确认 `conda activate base28` 后执行 `python -m pip install -r requirement.txt`。 |
| 找不到 Writer、`pdfinfo` 或 `pdftotext` | 在同一终端逐项执行上面的版本检查。Windows 检查 `--office` 路径和激活的 Conda 环境。 |
| 找不到网页样本 | 检查当前目录、实际文件名大小写（如 `Linkedin.md`）和 `--samples` 路径。可先用随附样本复测。 |
| 陈述超过一页或末段不完整 | 用相同 Writer 版本和字体复现，检查引用的经历长度。缩短履历中对应段落后重新生成并打开 PDF。 |

旧版浏览器自动化和 AIHawk 的配置方式见[原版文档](docs/original_linkedin_aihawk_readme.md)。工作区中的 `markdown/project_design_and_v1_status.md` 和 `markdown/application_preparation_progress.md` 分别记录设计梳理与后续离线实现进展。

<details>
<summary>维护参考：早期组件、部署说明与历史路线图</summary>

以下内容保留旧版命令、依赖及当时的支持情况。当前离线入口的环境和验收步骤见上文。

## 🧩 **Project Components**

This tool consists of modular components designed for scalability and maintainability:

| Component | Description | Status |
|-----------|-------------|--------|
| **🤖 Automation Engine** | Core job application automation across platforms | ✅ Active |
| **📊 Logging System** | Multi-threaded JSON logging for application tracking | ✅ Active |
| **🔮 AI Integration** | GPT-powered form filling and document selection | ✅ Active |
| **📄 Document Management** | Dynamic resume/cover letter generation | ✅ Active |

---

## 📖 **Legacy Documentation**

Looking for the original LinkedIn AIHawk documentation? 
👉 **[View Original Documentation](docs/original_linkedin_aihawk_readme.md)**

The original comprehensive guide contains detailed setup instructions, troubleshooting, and feature explanations from the LinkedIn-focused version of this project.

---

## ⚙️ **Quick Setup Guide**

### Prerequisites
- **Python 3.9+** installed on your system
- **Windows OS** (for Word document processing)
- **Microsoft Word** (for cover letter generation)
- **Google Chrome** browser

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/feder-cr/linkedIn_auto_jobs_applier_with_AI.git
   cd linkedIn_auto_jobs_applier_with_AI
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

### Required Configuration Files

Prepare these files in your data folder before running:

| File | Purpose | Location |
|------|---------|----------|
| `secrets.yaml` | API keys and credentials | `data_folder/secrets.yaml` |
| `config.yaml` | Job search parameters | `data_folder/config.yaml` |
| `plain_text_resume.yaml` | Your resume data | `data_folder/plain_text_resume.yaml` |

---

## 📁 **Document Management Setup**

### 1. Resume and Cover Letter Templates

Create organized document templates in `document_folder/`:

```
document_folder/
├── [Resume_Name].pdf              # Multiple resume variants
├── A1-Cover Letter -- [Type].docx # Cover letter templates
└── submitted/                     # Generated documents
```

### 2. Configure Document Types in `strings.py`

Update the `DOCUMENT_STYLE` mapping in [`src/utils/strings.py`](src/utils/strings.py):

```python
DOCUMENT_STYLE = {
    "A": ["Resume_Filename", "Document_Description"],
    "B": ["Software_Engineer_Resume", "Software Engineer"],
    "C": ["AI_Research_Resume", "AI Research Specialist"],
    # Add more document types as needed
}
```

### 3. Additional Required Files

| File | Purpose | Example |
|------|---------|---------|
| `env/cover_letter_last_job.json` | Job history tracking | Auto-generated |
| `logs/` directory | Application logs | Auto-created |

---

## 🔧 **Environment Setup**

### Virtual Environment (Recommended)

Create an isolated Python environment:

```bash
# Create virtual environment
python -m venv job_automation_env

# Activate (Windows)
job_automation_env\Scripts\activate

# Activate (Linux/Mac)  
source job_automation_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import selenium, langchain_openai; print('Dependencies installed successfully!')"
```

### Required Environment Variables

Create `.env` file (optional):
```bash
OPENAI_API_KEY=your_openai_api_key
LOG_LEVEL=INFO
CHROME_DRIVER_PATH=auto  # Auto-download ChromeDriver
```

---

## 📊 **Roadmap & Future Updates**

### 🎯 **Current Focus (v1.0)**
- ✅ JobsDB automation fully functional
- ✅ Multi-threaded logging system
- ✅ AI-powered form filling
- ✅ Document management system

### 🔮 **Coming Soon (v1.1)**
- 🔄 **LinkedIn Support Restoration** - Updated automation for LinkedIn platform
- 🎨 **Web Frontend Dashboard** - Beautiful interface for result viewing and management
- 🔔 **Smart Job Recommendations** - AI-powered job matching and priority notifications
- 📈 **Advanced Analytics** - Success rate tracking and optimization suggestions

### 🌟 **Future Vision (v2.0+)**
- Multi-platform expansion (Indeed, Glassdoor, etc.)
- Machine learning for application optimization
- Integration with calendar and interview scheduling
- Mobile app companion

---

## 🙏 **Acknowledgments**

Special thanks to:
- **Original AIHawk Community** for the foundation and inspiration
- **Contributors** who helped evolve this project from LinkedIn-only to multi-platform
- **Open Source Libraries** that make this automation possible
- **Beta Testers** providing valuable feedback on JobsDB automation

---

## 📞 **Support & Community**

- **🐛 Issues & Bugs**: [GitHub Issues](https://github.com/feder-cr/linkedIn_auto_jobs_applier_with_AI/issues)
- **💬 Community Support**: [Telegram Group](https://t.me/AIhawkCommunity)
- **📖 Documentation**: [Docs Folder](docs/)
- **🎥 Video Tutorials**: [Setup Guide](https://youtu.be/gdW9wogHEUM)

---

<div align="center">
  <sub>Built with ❤️ for job seekers worldwide | Star ⭐ this repo if it helps you land your dream job!</sub>
</div>

---

## 📖 **Legacy Documentation**

Looking for the original LinkedIn AIHawk documentation? 
👉 **[View Original Documentation](docs/original_linkedin_aihawk_readme.md)**

The original comprehensive guide contains detailed setup instructions, troubleshooting, and feature explanations from the LinkedIn-focused version of this project.

## Features

1. **Intelligent Job Search Automation**
   - Customizable search criteria
   - Continuous scanning for new openings
   - Smart filtering to exclude irrelevant listings

2. **Rapid and Efficient Application Submission**
   - One-click applications using LinkedIn's "Easy Apply" feature
   - Form auto-fill using your profile information
   - Automatic document attachment (resume, cover letter)

3. **AI-Powered Personalization**
   - Dynamic response generation for employer-specific questions
   - Tone and style matching to fit company culture
   - Keyword optimization for improved application relevance

4. **Volume Management with Quality**
   - Bulk application capability
   - Quality control measures
   - Detailed application tracking

5. **Intelligent Filtering and Blacklisting**
   - Company blacklist to avoid unwanted employers
   - Title filtering to focus on relevant positions

6. **Dynamic Resume Generation**
   - Automatically creates tailored resumes for each application
   - Customizes resume content based on job requirements

7. **Secure Data Handling**
   - Manages sensitive information securely using YAML files

## Installation

**Please watch this video to set up your LinkedIn_AIHawk: [How to set up LinkedIn_AIHawk](https://youtu.be/gdW9wogHEUM) - https://youtu.be/gdW9wogHEUM**
0. **Confirmed succesfull runs OSs & Python**: Python 3.10, 3.11.9(64b), 3.12.5(64b) . Windows 10, Ubuntu 22
1. **Download and Install Python:**

   Ensure you have the last Python version  installed. If not, download and install it from Python's official website. For detailed instructions, refer to the tutorials:

   - [How to Install Python on Windows](https://www.geeksforgeeks.org/how-to-install-python-on-windows/)
   - [How to Install Python on Linux](https://www.geeksforgeeks.org/how-to-install-python-on-linux/)
   - [How to Download and Install Python on macOS](https://www.geeksforgeeks.org/how-to-download-and-install-python-latest-version-on-macos-mac-os-x/)

2. **Download and Install Google Chrome:**
   - Download and install the latest version of Google Chrome in its default location from the [official website](https://www.google.com/chrome).

3. **Clone the repository:**
   ```bash
   git clone https://github.com/feder-cr/LinkedIn_AIHawk_automatic_job_application
   cd LinkedIn_AIHawk_automatic_job_application
   ```

4. **Activate virtual environment:**
   ```bash
   python3 -m venv virtual
   ```

   ```bash
   source virtual/bin/activate
   ```

5. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### 1. secrets.yaml

This file contains sensitive information. Never share or commit this file to version control.

- `email: [Your LinkedIn email]`
  - Replace with your LinkedIn account email address
- `password: [Your LinkedIn password]`
  - Replace with your LinkedIn account password
- `openai_api_key: [Your OpenAI API key]`
  - Replace with your OpenAI API key for GPT integration
  - To obtain an API key, follow the tutorial at: https://medium.com/@lorenzozar/how-to-get-your-own-openai-api-key-f4d44e60c327
  - Note: You need to add credit to your OpenAI account to use the API. You can add credit by visiting the [OpenAI billing dashboard](https://platform.openai.com/account/billing).



### 2. config.yaml

This file defines your job search parameters and bot behavior. Each section contains options that you can customize:

- `remote: [true/false]`
  - Set to `true` to include remote jobs, `false` to exclude them

- `experienceLevel:`
  - Set desired experience levels to `true`, others to `false`

- `jobTypes:`
  - Set desired job types to `true`, others to `false`

- `date:`
  - Choose one time range for job postings by setting it to `true`, others to `false`


- `positions:`
  - List job titles you're interested in, one per line
  - Example:
    ```yaml
    positions:
      - Software Developer
      - Data Scientist
    ```

- `locations:`
  - List locations you want to search in, one per line
  - Example:
    ```yaml
    locations:
      - Italy
      - London
    ```

- `distance: [number]`
  - Set the radius for your job search in miles
  - Example: `distance: 50`

- `companyBlacklist:`
  - List companies you want to exclude from your search, one per line
  - Example:
    ```yaml
    companyBlacklist:
      - Company X
      - Company Y
    ```

- `titleBlacklist:`
  - List keywords in job titles you want to avoid, one per line
  - Example:
    ```yaml
    titleBlacklist:
      - Sales
      - Marketing
    ```

### 3. plain_text_resume.yaml

This file contains your resume information in a structured format. Fill it out with your personal details, education, work experience, and skills. This information is used to auto-fill application forms and generate customized resumes.

Each section has specific fields to fill out:

- `personal_information:`
  - This section contains basic personal details to identify yourself and provide contact information.
    - **name**: Your first name.
    - **surname**: Your last name or family name.
    - **date_of_birth**: Your birth date in the format DD/MM/YYYY.
    - **country**: The country where you currently reside.
    - **city**: The city where you currently live.
    - **address**: Your full address, including street and number.
    - **phone_prefix**: The international dialing code for your phone number (e.g., +1 for the USA, +44 for the UK).
    - **phone**: Your phone number without the international prefix.
    - **email**: Your primary email address.
    - **github**: URL to your GitHub profile, if applicable.
    - **linkedin**: URL to your LinkedIn profile, if applicable.
  - Example
  ```yaml
  personal_information:
    name: "Jane"
    surname: "Doe"
    date_of_birth: "01/01/1990"
    country: "USA"
    city: "New York"
    address: "123 Main St"
    phone_prefix: "+1"
    phone: "5551234567"
    email: "jane.doe@example.com"
    github: "https://github.com/janedoe"
    linkedin: "https://www.linkedin.com/in/janedoe/"
  ```

- `education_details:`
  - This section outlines your academic background, including degrees earned and relevant coursework.
    - **degree**: The type of degree obtained (e.g., Bachelor's Degree, Master's Degree).
    - **university**: The name of the university or institution where you studied.
    - **final_evaluation_grade**: Your Grade Point Average or equivalent measure of academic performance.
    - **start_date**: The start year of your studies.
    - **graduation_year**: The year you graduated.
    - **field_of_study**: The major or focus area of your studies.
    - **exam**: A list of courses or subjects taken along with their respective grades.

  - Example:
  ```yaml
  education_details:
    - education_level: "Bachelor's Degree"
      institution: "University of Example"
      field_of_study: "Software Engineering"
      final_evaluation_grade: "4/4"
      start_date: "2021"
      year_of_completion: "2023"
      exam:
        Algorithms: "A"
        Data Structures: "B+"
        Database Systems: "A"
        Operating Systems: "A-"
        Web Development: "B"
  ```

- `experience_details:`
  - This section details your work experience, including job roles, companies, and key responsibilities.
    - **position**: Your job title or role.
    - **company**: The name of the company or organization where you worked.
    - **employment_period**: The timeframe during which you were employed in the role (e.g., MM/YYYY - MM/YYYY).
    - **location**: The city and country where the company is located.
    - **industry**: The industry or field in which the company operates.
    - **key_responsibilities**: A list of major responsibilities or duties you had in the role.
    - **skills_acquired**: Skills or expertise gained through this role.

  - Example:
  ```yaml
  experience_details:
    - position: "Software Developer"
      company: "Tech Innovations Inc."
      employment_period: "06/2021 - Present"
      location: "San Francisco, CA"
      industry: "Technology"
      key_responsibilities:
        - "Developed web applications using React and Node.js"
        - "Collaborated with cross-functional teams to design and implement new features"
        - "Troubleshot and resolved complex software issues"
      skills_acquired:
        - "React"
        - "Node.js"
        - "Software Troubleshooting"
  ```

- `projects:`
  - Include notable projects you have worked on, including personal or professional projects.
    - **name**: The name or title of the project.
    - **description**: A brief summary of what the project involves or its purpose.
    - **link**: URL to the project, if available (e.g., GitHub repository, website).

   - Example:
    ```yaml
    projects:
      - name: "Weather App"
        description: "A web application that provides real-time weather information using a third-party API."
        link: "https://github.com/janedoe/weather-app"
      - name: "Task Manager"
        description: "A task management tool with features for tracking and prioritizing tasks."
        link: "https://github.com/janedoe/task-manager"
    ```

- `achievements:`
  - Highlight notable accomplishments or awards you have received.
    - **name**: The title or name of the achievement.
    - **description**: A brief explanation of the achievement and its significance.

  - Example:
  ```yaml
  achievements:
    - name: "Employee of the Month"
      description: "Recognized for exceptional performance and contributions to the team."
    - name: "Hackathon Winner"
      description: "Won first place in a national hackathon competition."
  ```

- `certifications:`
  - Include any professional certifications you have earned.
      - name: "PMP"  
      description: "Certification for project management professionals, issued by the Project Management Institute (PMI)"

  - Example:
  ```yaml
  certifications:
    - "Certified Scrum Master"
    - "AWS Certified Solutions Architect"
  ```

- `languages:`
  - Detail the languages you speak and your proficiency level in each.
    - **language**: The name of the language.
    - **proficiency**: Your level of proficiency (e.g., Native, Fluent, Intermediate).

  - Example:
  ```yaml
  languages:
    - language: "English"
      proficiency: "Fluent"
    - language: "Spanish"
      proficiency: "Intermediate"
  ```

- `interests:`

  - Mention your professional or personal interests that may be relevant to your career.
    - **interest**: A list of interests or hobbies.

  - Example:
  ```yaml
  interests:
    - "Machine Learning"
    - "Cybersecurity"
    - "Open Source Projects"
    - "Digital Marketing"
    - "Entrepreneurship"
  ```

- `availability:`
  - State your current availability or notice period.
    - **notice_period**: The amount of time required before you can start a new role (e.g., "2 weeks", "1 month").

  - Example:
  ```yaml
  availability:
    notice_period: "2 weeks"
  ```

- `salary_expectations:`
  - Provide your expected salary range.
    - **salary_range_usd**: The salary range you are expecting, expressed in USD.

  - Example:
  ```yaml
  salary_expectations:
    salary_range_usd: "80000 - 100000"
  ```

- `self_identification:`
  - Provide information related to personal identity, including gender and pronouns.
    - **gender**: Your gender identity.
    - **pronouns**: The pronouns you use (e.g., He/Him, She/Her, They/Them).
    - **veteran**: Your status as a veteran (e.g., Yes, No).
    - **disability**: Whether you have a disability (e.g., Yes, No).
    - **ethnicity**: Your ethnicity.

  - Example:
  ```yaml
  self_identification:
    gender: "Female"
    pronouns: "She/Her"
    veteran: "No"
    disability: "No"
    ethnicity: "Asian"
  ```

- `legal_authorization:`
  - Indicate your legal ability to work in various locations.
    - **eu_work_authorization**: Whether you are authorized to work in the European Union (Yes/No).
    - **us_work_authorization**: Whether you are authorized to work in the United States (Yes/No).
    - **requires_us_visa**: Whether you require a visa to work in the US (Yes/No).
    - **requires_us_sponsorship**: Whether you require sponsorship to work in the US (Yes/No).
    - **requires_eu_visa**: Whether you require a visa to work in the EU (Yes/No).
    - **legally_allowed_to_work_in_eu**: Whether you are legally allowed to work in the EU (Yes/No).
    - **legally_allowed_to_work_in_us**: Whether you are legally allowed to work in the US (Yes/No).
    - **requires_eu_sponsorship**: Whether you require sponsorship to work in the EU (Yes/No).

  - Example:
     ```yaml
     legal_authorization:
       eu_work_authorization: "Yes"
       us_work_authorization: "No"
       requires_us_visa: "Yes"
       requires_us_sponsorship: "Yes"
       requires_eu_visa: "No"
       legally_allowed_to_work_in_eu: "Yes"
       legally_allowed_to_work_in_us: "No"
       requires_eu_sponsorship: "No"
     ```

- `work_preferences:`
  - Specify your preferences for work arrangements and conditions.
    - **remote_work**: Whether you are open to remote work (Yes/No).
    - **in_person_work**: Whether you are open to in-person work (Yes/No).
    - **open_to_relocation**: Whether you are willing to relocate for a job (Yes/No).
    - **willing_to_complete_assessments**: Whether you are willing to complete job assessments (Yes/No).
    - **willing_to_undergo_drug_tests**: Whether you are willing to undergo drug testing (Yes/No).
    - **willing_to_undergo_background_checks**: Whether you are willing to undergo background checks (Yes/No).

  - Example:
  ```yaml
  work_preferences:
    remote_work: "Yes"
    in_person_work: "No"
    open_to_relocation: "Yes"
    willing_to_complete_assessments: "Yes"
    willing_to_undergo_drug_tests: "No"
    willing_to_undergo_background_checks: "Yes"
  ```

### PLUS. data_folder_example

The `e` folder contains a working example of how the files necessary for the bot's operation should be structured and filled out. This folder serves as a practical reference to help you correctly set up your work environment for the LinkedIn job search bot.

#### Contents

Inside this folder, you'll find example versions of the key files:

- `secrets.yaml`
- `config.yaml`
- `plain_text_resume.yaml`

These files are already populated with fictitious but realistic data. They show you the correct format and type of information to enter in each file.

#### Usage

Using this folder as a guide can be particularly helpful for:

1. Understanding the correct structure of each configuration file
2. Seeing examples of valid data for each field
3. Having a reference point while filling out your personal files


## Usage
0. **LinkedIn language**
   To ensure the bot works, your LinkedIn language must be set to English.
   
2. **Data Folder:**
   Ensure that your data_folder contains the following files:
   - `secrets.yaml`
   - `config.yaml`
   - `plain_text_resume.yaml`

3. **Run the Bot:**

   LinkedIn_AIHawk offers flexibility in how it handles your pdf resume:

- **Dynamic Resume Generation:**
  If you don't use the `--resume` option, the bot will automatically generate a unique resume for each application. This feature uses the information from your `plain_text_resume.yaml` file and tailors it to each specific job application, potentially increasing your chances of success by customizing your resume for each position.
   ```bash
   python main.py
   ```
- **Using a Specific Resume:**
  If you want to use a specific PDF resume for all applications, place your resume PDF in the `data_folder` directory and run the bot with the `--resume` option:
  ```bash
  python main.py --resume /path/to/your/resume.pdf
  ```

## Documentation

TODO ):

## Troubleshooting

- **Carefully read logs and output :** Most of the errors are verbosely reflected just watch the output and try to find the root couse. 
- **If nothing works by unknown reason:**  Use tested OS. Reboot and/or update OS.  Use new clean venv. Try update Python to the tested version.  
- **ChromeDriver Issues:** Ensure ChromeDriver is compatible with your installed Chrome version.
- **Missing Files:** Verify that all necessary files are present in the data folder.
- **Invalid YAML:** Check your YAML files for syntax errors . Try to use external YAML validators e.g. https://www.yamllint.com/
- **OpenAI endpoint isues**: Try to check possible limits\blocking at their side 
  
If you encounter any issues, you can open an issue on [GitHub](https://github.com/feder-cr/linkedIn_auto_jobs_applier_with_AI/issues).
  Please add valuable details to the subject and to the description. If you need new feature then please reflect this.  
  I'll be more than happy to assist you!

## Conclusion

LinkedIn_AIHawk provides a significant advantage in the modern job market by automating and enhancing the job application process. With features like dynamic resume generation and AI-powered personalization, it offers unparalleled flexibility and efficiency. Whether you're a job seeker aiming to maximize your chances of landing a job, a recruiter looking to streamline application submissions, or a career advisor seeking to offer better services, LinkedIn_AIHawk is an invaluable resource. By leveraging cutting-edge automation and artificial intelligence, this tool not only saves time but also significantly increases the effectiveness and quality of job applications in today's competitive landscape.

## Contributors

- [feder-cr](https://github.com/feder-cr) - Creator and Lead Developer

LinkedIn_AIHawk is still in beta, and your feedback, suggestions, and contributions are highly valued. Feel free to open issues, suggest enhancements, or submit pull requests to help improve the project. Let's work together to make LinkedIn_AIHawk an even more powerful tool for job seekers worldwide.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer
LinkedIn_AIHawk is developed for educational purposes only. The creator does not assume any responsibility for its use. Users should ensure they comply with LinkedIn's terms of service, any applicable laws and regulations, and ethical considerations when using this tool. The use of automated tools for job applications may have implications on user accounts, and caution is advised.

</details>
