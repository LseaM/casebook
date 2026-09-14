from __future__ import annotations

import re


SUPPORTED_LANGUAGES = {"en", "zh-CN"}


def normalize_language(value: object) -> str:
    """Normalize public language values while keeping English as the default."""
    text = str(value or "").strip().lower().replace("_", "-")
    return "zh-CN" if text in {"zh", "zh-cn", "cn"} else "en"


def localize_report_html(html: str, language: str) -> str:
    """Translate Casebook-owned report chrome without changing case content."""
    if normalize_language(language) != "zh-CN":
        return html
    replacements = {
        '<html lang="en">': '<html lang="zh-CN">',
        "Casebook Test Report - ": "Casebook 测试报告 - ",
        "Casebook · Test Quality Brief": "Casebook · 测试质量简报",
        ">Test Execution Brief<": ">测试执行简报<",
        "A concise view of execution health, delivery risk, unresolved cases, and detailed evidence for ": "测试计划执行健康度、交付风险、未解决问题和详细证据概览：",
        ">Executed<": ">已执行<", ">Plan Overview<": ">计划概览<",
        ">Execution Summary<": ">执行汇总<", ">Quality Signals<": ">质量信号<",
        ">Execution Distribution<": ">执行结果分布<", ">Failed / Blocked Priority<": ">失败 / 阻塞优先级<",
        ">Attention Required<": ">需要关注<", ">Execution Details<": ">执行详情<",
        ">All Test Cases<": ">全部测试用例<", ">Case<": ">用例<", ">Title<": ">标题<",
        ">Priority<": ">优先级<", ">Result<": ">结果<", ">No records<": ">暂无记录<",
        "Execution identity, ownership, scope, and timing.": "执行标识、负责人、范围和时间信息。",
        "Current result totals across the selected plan scope.": "当前测试计划范围内的执行结果汇总。",
        "Result distribution and priority concentration for unresolved risk.": "执行结果分布及未解决风险的优先级分布。",
        "Cases most likely to affect release confidence.": "最可能影响发布信心的用例。",
        "Expand a case to review its execution evidence.": "展开用例查看执行证据。",
        'label: "Pass Rate"': 'label: "通过率"', 'label: "Issues"': 'label: "问题"',
        'aria-label="Expand execution details"': 'aria-label="展开执行详情"',
        ">Total Cases<": ">用例总数<", ">Passed<": ">通过<", ">Failed<": ">失败<",
        ">Blocked<": ">阻塞<", ">Deferred<": ">延期<", ">Untested<": ">未测试<",
        ">Failed Cases<": ">失败用例<", ">Blocked Cases<": ">阻塞用例<",
        ">File<": ">文件<", ">Notes<": ">备注<", ">Actual Result<": ">实际结果<",
        ">Defects<": ">缺陷<", ">Screenshots<": ">截图<", ">Executed At<": ">执行时间<",
        ">Plan ID<": ">计划 ID<", ">Plan Name<": ">计划名称<", ">Status<": ">状态<",
        ">Mode<": ">模式<", ">Source Plan<": ">来源计划<", ">Case Scope<": ">用例范围<",
        ">Scope<": ">范围<", ">Environment<": ">测试环境<", ">Tester<": ">测试人员<",
        ">Started At<": ">开始时间<", ">Completed At<": ">完成时间<",
        ">In Progress<": ">进行中<", ">Completed<": ">已完成<", ">Full run<": ">全量执行<",
        ">Retest failed/blocked/deferred<": ">重测失败、阻塞或延期用例<",
        ">Test case<": ">测试用例<", ">Generated ": ">生成时间：", "Generated: ": "生成时间：",
        '"label": "Passed"': '"label": "通过"', '"label": "Failed"': '"label": "失败"',
        '"label": "Blocked"': '"label": "阻塞"', '"label": "Deferred"': '"label": "延期"',
        '"label": "Untested"': '"label": "未测试"',
        ">passed<": ">通过<", ">failed<": ">失败<", ">blocked<": ">阻塞<",
        ">deferred<": ">延期<", ">untested<": ">未测试<",
    }
    for source, target in replacements.items():
        html = html.replace(source, target)
    html = re.sub(r">(\d+) cases<", r">\1 条用例<", html)
    html = re.sub(r">(\d+) of (\d+) executed<", r">已执行 \1 / \2<", html)
    html = re.sub(
        r"No failed or blocked cases are currently open\. Current pass rate is ([\d.]+)%\.",
        r"当前没有失败或阻塞用例，通过率为 \1%。",
        html,
    )
    html = re.sub(
        r"(\d+) failed or blocked cases require attention; (\d+) are P0 priority\. Current pass rate is ([\d.]+)%\.",
        r"有 \1 条失败或阻塞用例需要关注，其中 \2 条为 P0，通过率为 \3%。",
        html,
    )
    return html


def localize_export_html(html: str, language: str) -> str:
    """Translate standalone export controls while preserving exported case text."""
    if normalize_language(language) != "zh-CN":
        return html
    replacements = {
        '<html lang="en">': '<html lang="zh-CN">', "Casebook Export - ": "Casebook 用例导出 - ",
        "Portable review workspace": "便携式用例评审工作台", "TEST CASE REVIEW": "测试用例评审",
        "Review controls": "评审控件", "Search cases": "搜索用例", "Priority filter": "优先级筛选",
        "Tag filter": "标签筛选", "Review mark filter": "评审标记筛选",
        ">All review states<": ">全部评审状态<", ">Marked only<": ">仅已标记<", ">Unmarked only<": ">仅未标记<",
        ">Expand all<": ">全部展开<", ">Collapse all<": ">全部收起<", ">Export review notes<": ">导出评审备注<",
        ">No cases match the current filters.<": ">没有符合当前筛选条件的用例。<", '"Generated: "': '"生成时间："',
        '"All priorities ("': '"全部优先级 ("', '"All tags"': '"全部标签"',
        ', "Files", "files"': ', "文件", "files"', ', "Cases", "cases"': ', "用例", "cases"',
        ', "Marked", "marked"': ', "已标记", "marked"', ', "Notes", "notes"': ', "备注", "notes"',
        '>Title<': '>标题<', '>Priority<': '>优先级<', '>Type<': '>类型<', '>Tags<': '>标签<', '>Actions<': '>操作<',
        '>Review<': '>评审<', '>Mark<': '>标记<', '>Auto<': '>自动化<',
        'placeholder="Describe what should be updated"': 'placeholder="描述需要更新的内容"',
        'detailList("Preconditions"': 'detailList("前置条件"', 'detailList("Steps"': 'detailList("步骤"',
        'detailList("Expected Results"': 'detailList("预期结果"',
        'title === "Preconditions"': 'title === "前置条件"',
        '<li class="empty-detail">None</li>': '<li class="empty-detail">无</li>',
        '"Owner: "': '"负责人："', '"Reviewed: "': '"评审日期："',
        '"priorities: "': '"优先级："', '"tags: "': '"标签："',
    }
    for source, target in replacements.items():
        html = html.replace(source, target)
    html = html.replace("} cases", "} 条用例")
    return html
