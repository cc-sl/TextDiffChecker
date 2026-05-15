#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TextHighlightDiff — 文本高亮对比工具
======================================
精准对比两段文本的差异，以颜色高亮标注：
  🔴 红色 — 原文多出的内容（对比文本中不存在）
  🔵 蓝色 — 原文缺少的内容（对比文本中存在而原文没有）
  🟡 黄色 — 两边内容不一致（字符不匹配）

纯 Python + tkinter 实现，无第三方依赖，可直接运行。
"""

import tkinter as tk
import difflib


class TextHighlightDiff:
    """文本高亮对比工具主类"""

    def __init__(self, root):
        """初始化应用程序窗口与界面"""
        self.root = root
        self.root.title("TextHighlightDiff — 文本高亮对比工具")
        # 设置窗口初始大小与最小尺寸
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # ── 自定义配色方案 ──
        self.C_DEL   = "#FF4D4D"    # 红色：原文多出
        self.C_INS   = "#4DA6FF"    # 蓝色：原文缺少
        self.C_REP   = "#FFD700"    # 黄色：内容不一致
        self.C_BG    = "#F0F2F5"    # 页面背景
        self.C_HEAD  = "#2C3E50"    # 标题栏深灰蓝

        # 同步滚动防重入标志
        self._syncing = False

        # 构建所有 UI 组件
        self._build_ui()
        # 窗口居中显示
        self._center_window()

    # ================================================================
    #  界面构建
    # ================================================================
    def _build_ui(self):
        """构建完整的图形界面"""

        # ──────────── 顶部标题栏 ────────────
        hdr = tk.Frame(self.root, bg=self.C_HEAD, height=46)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)  # 固定高度，不被子组件撑开
        tk.Label(
            hdr,
            text="  TextHighlightDiff  —  文本高亮对比工具",
            font=("Arial", 14, "bold"),
            fg="white", bg=self.C_HEAD
        ).pack(side=tk.LEFT, padx=12)

        # ──────────── 中部：左右两个文本区 ────────────
        body = tk.Frame(self.root, bg=self.C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # 左侧：原文
        left_frame = tk.Frame(body, bg=self.C_BG)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        tk.Label(
            left_frame, text="原文",
            font=("Arial", 12, "bold"),
            fg=self.C_HEAD, bg=self.C_BG
        ).pack(anchor=tk.W)

        self.left_text = tk.Text(
            left_frame, wrap=tk.WORD,
            font=("Consolas", 11),
            undo=True, relief=tk.GROOVE, bd=2, padx=4, pady=4
        )
        self.left_sb = tk.Scrollbar(left_frame, command=self.left_text.yview)
        # yscrollcommand 使用自定义回调，以支持同步滚动
        self.left_text.configure(yscrollcommand=self._left_scroll_cmd)
        self.left_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_text.pack(fill=tk.BOTH, expand=True)

        # 右侧：对比文本
        right_frame = tk.Frame(body, bg=self.C_BG)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        tk.Label(
            right_frame, text="对比文本",
            font=("Arial", 12, "bold"),
            fg=self.C_HEAD, bg=self.C_BG
        ).pack(anchor=tk.W)

        self.right_text = tk.Text(
            right_frame, wrap=tk.WORD,
            font=("Consolas", 11),
            undo=True, relief=tk.GROOVE, bd=2, padx=4, pady=4
        )
        self.right_sb = tk.Scrollbar(right_frame, command=self.right_text.yview)
        self.right_text.configure(yscrollcommand=self._right_scroll_cmd)
        self.right_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_text.pack(fill=tk.BOTH, expand=True)

        # ── 为两个文本框配置高亮 tag 样式 ──
        for widget in (self.left_text, self.right_text):
            widget.tag_configure("delete",  background=self.C_DEL)   # 红
            widget.tag_configure("insert",  background=self.C_INS)   # 蓝
            widget.tag_configure("replace", background=self.C_REP)   # 黄

        # ──────────── 按钮与图例行 ────────────
        bar = tk.Frame(self.root, bg=self.C_BG)
        bar.pack(fill=tk.X, padx=10, pady=4)

        # "开始对比" 按钮
        tk.Button(
            bar, text="🔍 开始对比",
            font=("Arial", 11, "bold"),
            bg=self.C_HEAD, fg="white",
            activebackground="#3D566E", activeforeground="white",
            relief=tk.FLAT, padx=18, pady=4, cursor="hand2",
            command=self.compare
        ).pack(side=tk.LEFT, padx=(0, 8))

        # "清空" 按钮
        tk.Button(
            bar, text="✖ 清空",
            font=("Arial", 11, "bold"),
            bg="#C0392B", fg="white",
            activebackground="#E74C3C", activeforeground="white",
            relief=tk.FLAT, padx=18, pady=4, cursor="hand2",
            command=self.clear
        ).pack(side=tk.LEFT)

        # 颜色图例说明
        legend_frame = tk.Frame(bar, bg=self.C_BG)
        legend_frame.pack(side=tk.RIGHT)
        for desc, color in [
            ("■ 原文多出（红）", self.C_DEL),
            ("■ 原文缺少（蓝）", self.C_INS),
            ("■ 内容不符（黄）", self.C_REP),
        ]:
            tk.Label(
                legend_frame, text=desc,
                font=("Arial", 10), fg=color, bg=self.C_BG
            ).pack(side=tk.LEFT, padx=10)

        # ──────────── 底部统计区 ────────────
        stat_frame = tk.LabelFrame(
            self.root, text="  差异统计  ",
            font=("Arial", 11, "bold"),
            fg=self.C_HEAD, bg=self.C_BG,
            relief=tk.GROOVE, bd=2
        )
        stat_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.stat_text = tk.Text(
            stat_frame, height=8,
            font=("Consolas", 10),
            wrap=tk.WORD, state=tk.DISABLED,
            bg="#FAFAFA", relief=tk.FLAT, padx=6, pady=4
        )
        stat_sb = tk.Scrollbar(stat_frame, command=self.stat_text.yview)
        self.stat_text.configure(yscrollcommand=stat_sb.set)
        stat_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.stat_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 统计区文字 tag 样式（用于彩色区分各类差异）
        self.stat_text.tag_configure(
            "del", foreground=self.C_DEL, font=("Consolas", 10, "bold"))
        self.stat_text.tag_configure(
            "ins", foreground=self.C_INS, font=("Consolas", 10, "bold"))
        self.stat_text.tag_configure(
            "rep", foreground="#D4AC0D", font=("Consolas", 10, "bold"))
        self.stat_text.tag_configure(
            "hdr", font=("Consolas", 10, "bold"))

    # ================================================================
    #  同步滚动
    # ================================================================
    def _left_scroll_cmd(self, first, last):
        """
        左侧文本框的 yscrollcommand 回调。
        更新左侧滚动条位置，并同步滚动右侧文本框（防止循环触发）。
        """
        self.left_sb.set(first, last)
        if not self._syncing:
            self._syncing = True
            self.right_text.yview_moveto(first)
            self.right_sb.set(first, last)
            self._syncing = False

    def _right_scroll_cmd(self, first, last):
        """
        右侧文本框的 yscrollcommand 回调。
        更新右侧滚动条位置，并同步滚动左侧文本框（防止循环触发）。
        """
        self.right_sb.set(first, last)
        if not self._syncing:
            self._syncing = True
            self.left_text.yview_moveto(first)
            self.left_sb.set(first, last)
            self._syncing = False

    # ================================================================
    #  窗口居中
    # ================================================================
    def _center_window(self):
        """将窗口在屏幕中央显示"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"+{x}+{y}")

    # ================================================================
    #  核心对比逻辑
    # ================================================================
    def compare(self):
        """
        执行文本对比并高亮差异，同时生成统计报告。

        比对流程：
          1. 获取左右文本内容
          2. 清除旧的高亮标记
          3. 预建偏移量→Text索引的映射表（只需遍历一次，高效查表）
          4. 使用 difflib.SequenceMatcher 进行字符级精确比对
          5. 根据操作码 (opcodes) 分类标注差异
          6. 输出统计报告
        """
        # 获取文本内容（"end-1c" 去掉 tkinter 自动追加的末尾换行）
        left_content  = self.left_text.get("1.0", "end-1c")
        right_content = self.right_text.get("1.0", "end-1c")

        # 清除上一次对比遗留的高亮标记
        for tag_name in ("delete", "insert", "replace"):
            self.left_text.tag_remove(tag_name, "1.0", tk.END)
            self.right_text.tag_remove(tag_name, "1.0", tk.END)

        # 两边均为空时，给出提示
        if not left_content and not right_content:
            self._set_stat("  两段文本均为空，请输入内容后再对比。")
            return

        # 预先构建偏移量→Text索引的映射表，避免重复遍历文本
        lmap = self._build_index_map(self.left_text)
        rmap = self._build_index_map(self.right_text)

        # 使用 difflib.SequenceMatcher 进行字符级精确比对
        # autojunk=False：不做"垃圾字符"过滤，确保比对结果完全精确
        sm = difflib.SequenceMatcher(None, left_content, right_content,
                                      autojunk=False)
        opcodes = sm.get_opcodes()

        # 统计计数
        del_count = 0   # 原文多出字符数
        ins_count = 0   # 原文缺少字符数
        rep_count = 0   # 内容不一致字符数

        # 详细差异记录（用于统计区逐条展示）
        del_details = []  # (起始偏移, 结束偏移, 具体文本)
        ins_details = []  # (起始偏移, 结束偏移, 具体文本)
        rep_details = []  # (左起, 左止, 右起, 右止, 左文本, 右文本)

        # 遍历所有差异操作码
        for tag, i1, i2, j1, j2 in opcodes:

            if tag == "equal":
                # 完全相同，无需处理
                continue

            elif tag == "delete":
                # ── 原文有，对比文本没有 → 原文"多出" → 标红色 ──
                span = left_content[i1:i2]
                self.left_text.tag_add("delete", lmap[i1], lmap[i2])
                del_count += len(span)
                del_details.append((i1, i2, span))

            elif tag == "insert":
                # ── 对比文本有，原文没有 → 原文"缺少" → 标蓝色 ──
                span = right_content[j1:j2]
                self.right_text.tag_add("insert", rmap[j1], rmap[j2])
                ins_count += len(span)
                ins_details.append((j1, j2, span))

            elif tag == "replace":
                # ── 两边内容不同 → "内容不一致" → 两边均标黄色 ──
                left_span  = left_content[i1:i2]
                right_span = right_content[j1:j2]
                self.left_text.tag_add("replace", lmap[i1], lmap[i2])
                self.right_text.tag_add("replace", rmap[j1], rmap[j2])
                rep_count += max(len(left_span), len(right_span))
                rep_details.append((i1, i2, j1, j2, left_span, right_span))

        # 生成并显示差异统计报告
        self._show_report(del_count, ins_count, rep_count,
                          del_details, ins_details, rep_details)

    # ================================================================
    #  辅助方法
    # ================================================================
    @staticmethod
    def _build_index_map(widget):
        """
        将字符串偏移量映射为 tkinter Text 的 "行.列" 索引。

        原理：
          - tkinter Text 使用 "行号.列号" 定位字符（行号从1开始，列号从0开始）
          - difflib 返回的偏移量基于纯字符串（从0开始）
          - 此函数只需遍历一次文本，将所有偏移量预先转换为 Text 索引存入列表
          - 后续通过 mapping[offset] 直接查表，无需重复遍历

        返回：
          list[str] — 长度为 len(content)+1，mapping[i] 即偏移 i 对应的 Text 索引
        """
        content = widget.get("1.0", "end-1c")
        mapping = []
        line, col = 1, 0
        for ch in content:
            mapping.append(f"{line}.{col}")
            if ch == "\n":
                line += 1
                col = 0
            else:
                col += 1
        # 追加文本末尾位置（用于范围的结束偏移，exclusive）
        mapping.append(f"{line}.{col}")
        return mapping

    def _set_stat(self, text):
        """在统计区设置纯文本内容"""
        self.stat_text.configure(state=tk.NORMAL)
        self.stat_text.delete("1.0", tk.END)
        self.stat_text.insert(tk.END, text)
        self.stat_text.configure(state=tk.DISABLED)

    # ================================================================
    #  差异统计报告
    # ================================================================
    def _show_report(self, del_n, ins_n, rep_n,
                     del_d, ins_d, rep_d):
        """
        在底部统计区输出详细的差异报告。

        参数：
          del_n / ins_n / rep_n — 各类差异的字符计数
          del_d — 原文多出详情列表 [(起始偏移, 结束偏移, 具体文本), ...]
          ins_d — 原文缺少详情列表
          rep_d — 内容不一致详情列表 [(左起, 左止, 右起, 右止, 左文, 右文), ...]
        """
        self.stat_text.configure(state=tk.NORMAL)
        self.stat_text.delete("1.0", tk.END)

        total = del_n + ins_n + rep_n

        if total == 0:
            # 无差异
            self.stat_text.insert(
                tk.END, "  ✅ 两段文本完全一致，无任何差异！\n", "hdr")
            self.stat_text.configure(state=tk.DISABLED)
            return

        # ── 第一部分：差异总览 ──
        self.stat_text.insert(tk.END, "  差异总览：共 ", "hdr")
        self.stat_text.insert(tk.END, f"{total} 处", "hdr")
        self.stat_text.insert(tk.END, " 差异  —  ")
        self.stat_text.insert(tk.END, f"原文多出 {del_n} 字", "del")
        self.stat_text.insert(tk.END, "  |  ")
        self.stat_text.insert(tk.END, f"原文缺少 {ins_n} 字", "ins")
        self.stat_text.insert(tk.END, "  |  ")
        self.stat_text.insert(tk.END, f"内容不符 {rep_n} 字", "rep")
        self.stat_text.insert(tk.END, "\n")
        self.stat_text.insert(
            tk.END, "  " + "─" * 60 + "\n")

        # ── 第二部分：原文多出（红色）逐条展示 ──
        if del_d:
            self.stat_text.insert(
                tk.END, "  🔴 原文多出（建议删除）：\n", "del")
            for start, end, span in del_d:
                # 将换行符替换为可见的 \n 标记
                display = span.replace("\n", "\\n")
                self.stat_text.insert(
                    tk.END,
                    f"      · 字符位置 {start}~{end-1}：「{display}」\n")

        # ── 第三部分：原文缺少（蓝色）逐条展示 ──
        if ins_d:
            self.stat_text.insert(
                tk.END, "  🔵 原文缺少（建议补充）：\n", "ins")
            for start, end, span in ins_d:
                display = span.replace("\n", "\\n")
                self.stat_text.insert(
                    tk.END,
                    f"      · 字符位置 {start}~{end-1}：「{display}」\n")

        # ── 第四部分：内容不一致（黄色）逐条展示 ──
        if rep_d:
            self.stat_text.insert(
                tk.END, "  🟡 内容不一致：\n", "rep")
            for li1, li2, ri1, ri2, lspan, rspan in rep_d:
                dl = lspan.replace("\n", "\\n")
                dr = rspan.replace("\n", "\\n")
                self.stat_text.insert(
                    tk.END,
                    f"      · 位置 {li1}~{li2-1}：原文「{dl}」"
                    f" → 对比文本「{dr}」\n")

        self.stat_text.configure(state=tk.DISABLED)

    # ================================================================
    #  清空功能
    # ================================================================
    def clear(self):
        """清空所有文本输入和统计结果，恢复初始状态"""
        self.left_text.delete("1.0", tk.END)
        self.right_text.delete("1.0", tk.END)
        self._set_stat("")


# ──────────────────────────────────────────────
#  程序入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = TextHighlightDiff(root)
    root.mainloop()
