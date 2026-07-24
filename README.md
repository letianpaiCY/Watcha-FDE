# Watcha FDE Mock Skills

观猹 FDE 共学营大作业的四套独立 Mock 数据 Skill。学员只需安装自己选择的场景。

## 安装前提

先确认本机可以运行 Node.js 和 `npx`：

```bash
node --version
npx --version
```

## 分场景安装

### 企业知识库

```bash
npx skills add letianpaiCY/Watcha-FDE --skill fde-mock-knowledge-base -g
```

安装后对 Agent 说：

```text
使用 fde-mock-knowledge-base 创建制造业知识库材料
```

制造业可以替换为美妆零售或医药行业。

### 会议决策与任务跟踪

```bash
npx skills add letianpaiCY/Watcha-FDE --skill fde-mock-meeting-transcripts -g
```

安装后对 Agent 说：

```text
使用 fde-mock-meeting-transcripts 创建会议字幕材料
```

### 企业报销预审

```bash
npx skills add letianpaiCY/Watcha-FDE --skill fde-mock-expense-tickets -g
```

安装后对 Agent 说：

```text
使用 fde-mock-expense-tickets 创建报销模拟数据
```

### CHA CUP 营销图片

```bash
npx skills add letianpaiCY/Watcha-FDE --skill fde-mock-marketing-assets -g
```

安装后对 Agent 说：

```text
使用 fde-mock-marketing-assets 创建 CHA CUP 营销图片项目材料
```

该 Skill 创建一篇 VI 与审核规则文档、一个含商品资料和出图任务的多维表格，并上传产品母图和透明 Logo。它不会替学员生成营销图或验收答案。

## 安装飞书 CLI

Skill 会先检测飞书 CLI。未安装时，经用户确认后执行官方安装命令：

```bash
npx @larksuite/cli@latest install
```

Skill 只在写入前请求一次确认，并直接在用户的飞书文档库中创建新资源，不修改或删除已有数据。

## 数据边界

- 所有企业、人员、会议、报销和业务内容均为课程用脱敏模拟材料。
- Mock Skill 只提供原始业务材料，不提供测试集、预期答案或验收结论。
- 行业知识文档依据公开来源整理并保留链接，不复制报告全文。

## 构建离线数据包

运行：

```bash
python3 scripts/build_download_packages.py
```

脚本在本地 `dist/` 生成会议、报销和 CHA CUP 营销图片三个 ZIP。说明、字幕、制度和 VI 规范均为 UTF-8 Markdown，文件名统一使用 ASCII；结构化数据保留 CSV，图片保留 PNG。`dist/` 不提交 GitHub；知识库离线包暂不生成。
