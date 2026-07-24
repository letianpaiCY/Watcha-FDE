---
name: fde-mock-marketing-assets
description: 创建 FDE 共学营 CHA CUP 营销图片场景的模拟 VI 规则、单品数据、出图任务和品牌图片，并通过飞书 CLI 写入飞书文档、云盘和多维表格。用户要求生成营销图片、品牌物料、商品主图或视觉合规大作业素材时使用。
---

# FDE 营销图片 Mock

创建 1 篇 VI 规则文档、1 个含两张表的 Base、1 条商品记录、10 条原始出图任务，并上传产品图和 Logo。只提供原始业务材料，不生成营销图、问题标签、标准答案或 Eval。

## 工作流

1. 将包含本文件的目录记为 `SKILL_DIR`。
2. 根据操作系统选择可用的 Python 3 启动命令：macOS/Linux 优先 `python3`，Windows 优先 `py -3`，其次 `python`。
3. 用所选 Python 命令运行 `"$SKILL_DIR/scripts/preflight.py"`。
4. 按 [飞书环境处理](references/lark-setup.md) 处理预检结果；环境未就绪时不要继续。
5. 不询问商品、颜色、数量或目标目录，直接运行预览：

```text
<PYTHON> <SKILL_DIR>/scripts/create_feishu_resources.py --dry-run
```

6. 告诉用户将上传 2 个文件，并创建 1 篇文档、1 个 Base、2 张表和 11 条记录；不会修改或删除已有数据。请求一次写入确认。
7. 用户确认后运行：

```text
<PYTHON> <SKILL_DIR>/scripts/create_feishu_resources.py --yes
```

8. 返回 VI 文档、Base、产品图和 Logo 链接，并报告回读验证结果。

## 约束

- 不要生成商品营销图、示例成品或提示词。
- 不要输出每条任务的问题标签、预期结论、是否通过或测试答案。
- 不要替学员创建 Eval、计算准确率或决定验收结果。
- 不要要求用户提供目标文件夹、Base Token 或业务参数。
- 写入部分失败时，报告已创建资源和错误；不要自动删除任何飞书资源。
- 明确所有商品、活动、价格和品牌规则均为课程用模拟材料，不构成广告合规意见。

## 资源

- [飞书 CLI 安装与授权](references/lark-setup.md)
- [营销素材与数据结构](references/data-schema.md)
