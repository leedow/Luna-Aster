"""
流式文本切片工具。

实现思路：
- 逐段接收 LLM 的增量输出文本；
- 根据句末标点或自定义分隔符进行切片；
- 仅在识别到完整切片时返回结果，未形成切片时返回空列表；
- 支持在最后调用 flush() 输出剩余内容。
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple


DEFAULT_DELIMITERS = "。！？!?；;，,.;\n"


class StreamingTextSlicer:
    """
    增量文本切片器。

    Attributes:
        keep_delimiter: 是否在切片文本中保留分隔符。
        delimiters: 用于切分文本的分隔符字符串。
        min_chunk_len: 触发切片的最小有效长度（去除首尾空白后）。
        max_chunk_len: 当缓冲区长度超过该值时强制切片，None 表示不限制。
    """

    def __init__(
        self,
        *,
        delimiters: Optional[str] = None,
        keep_delimiter: bool = True,
        min_chunk_len: int = 1,
        max_chunk_len: Optional[int] = None,
    ) -> None:
        self.keep_delimiter = keep_delimiter
        self.min_chunk_len = max(min_chunk_len, 0)
        self.max_chunk_len = max_chunk_len if max_chunk_len and max_chunk_len > 0 else None
        self._buffer: List[str] = []

        delimiter_chars = delimiters or DEFAULT_DELIMITERS
        # 构建正则：匹配任意单个分隔符
        # 使用捕获组，以便根据 keep_delimiter 决定是否保留
        escaped = "".join(re.escape(ch) for ch in delimiter_chars)
        self._delimiter_pattern = re.compile(f"[{escaped}]")

    def feed(self, text: str) -> List[str]:
        """
        追加文本并返回新生成的切片。

        Args:
            text: 新增的 LLM 输出文本。

        Returns:
            列表，包含本次调用产生的切片；若未形成新切片，则返回空列表。
        """
        if not text:
            return []

        self._buffer.append(text)
        combined = "".join(self._buffer)

        slices: List[str] = []
        remaining = combined

        while True:
            match = self._delimiter_pattern.search(remaining)
            if not match:
                break

            end_index = match.end()
            raw_chunk = remaining[:end_index]

            if not self.keep_delimiter:
                raw_chunk = remaining[: match.start()]

            chunk = raw_chunk.strip()

            if len(chunk) >= self.min_chunk_len:
                slices.append(chunk)

            # 无论是否生成切片，都要截断已处理的部分
            remaining = remaining[end_index:]

        if self.max_chunk_len:
            forced_slices, remaining = self._slice_by_length(remaining)
            slices.extend(forced_slices)

        self._buffer = [remaining] if remaining else []

        return slices

    def flush(self, *, discard_partial: bool = False) -> List[str]:
        """
        输出当前缓冲区剩余文本。

        Args:
            discard_partial: 为 True 时，如果剩余文本长度小于 min_chunk_len 则丢弃。

        Returns:
            列表，包含剩余文本；若缓冲区为空或被丢弃则返回空列表。
        """
        if not self._buffer:
            return []

        combined = "".join(self._buffer).strip()
        self._buffer.clear()

        if not combined:
            return []

        if self.max_chunk_len and len(combined) > self.max_chunk_len:
            slices, remaining = self._slice_by_length(combined)
            valid_chunks = [chunk for chunk in slices if len(chunk) >= self.min_chunk_len]

            remaining_stripped = remaining.strip()
            if remaining_stripped:
                if not (discard_partial and len(remaining_stripped) < self.min_chunk_len):
                    valid_chunks.append(remaining_stripped)

            return valid_chunks

        if discard_partial and len(combined) < self.min_chunk_len:
            return []

        return [combined]

    def clear(self) -> None:
        """清空缓冲区。"""
        self._buffer.clear()

    def _slice_by_length(self, text: str) -> Tuple[List[str], str]:
        """
        按最大长度进行强制切片。

        Returns:
            (chunks, remaining)
        """
        if not self.max_chunk_len:
            return [], text

        chunks: List[str] = []
        remaining = text

        while len(remaining) > self.max_chunk_len:
            chunk = remaining[: self.max_chunk_len]
            chunk = chunk.strip()
            if len(chunk) >= self.min_chunk_len:
                chunks.append(chunk)
            remaining = remaining[self.max_chunk_len :]

        return chunks, remaining

