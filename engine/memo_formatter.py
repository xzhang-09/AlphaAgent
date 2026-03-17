from __future__ import annotations

from schemas.memo import MemoContent, MemoSection


class MemoFormatter:
    def render_markdown(self, memo: MemoContent) -> str:
        sections = [
            self._render_section(memo.company),
            self._render_section(memo.why_now),
            self._render_section(memo.key_drivers),
            self._render_section(memo.sector_context),
            self._render_section(memo.macro_context),
            self._render_section(memo.fundamental_analysis),
            self._render_section(memo.valuation_analysis),
            self._render_section(memo.bull_case),
            self._render_section(memo.bear_case),
            self._render_section(memo.catalysts),
            self._render_section(memo.risks),
            self._render_section(memo.conclusion),
        ]
        return "\n\n".join([f"# {memo.title}"] + [section for section in sections if section.strip()])

    @staticmethod
    def _render_section(section: MemoSection) -> str:
        lines = [f"## {section.heading}"]
        if section.summary:
            lines.append(section.summary)
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        return "\n".join(lines)
