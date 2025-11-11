from __future__ import annotations

from typing import Dict, Any, Optional

import io
import os
import sys
import pandas as pd

from ..core.progress import progress_messages, last_printed_percentage
from ..thirdparty.stressinv import invert_global, invert_depthwise


class _StdoutInterceptor(io.StringIO):
    """Intercept stdout lines, forward to original and notify progress via callback."""

    def __init__(self, on_line):
        super().__init__()
        self.on_line = on_line
        self._buffer = ""
        self._orig_write = None

    def bind_original(self, original_write):
        self._orig_write = original_write

    def write(self, s):
        # forward to original stdout
        if self._orig_write:
            self._orig_write(s)
        # accumulate and parse lines
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            try:
                self.on_line(line)
            except Exception:
                pass
        return len(s)


def run_stressinv_with_progress(session_id: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    在单独线程中运行地应力反演，实时解析算法打印的日志并汇报进度。

    kwargs:
      - mode: 'global' | 'depthwise'
      - input_path: CSV 路径
      - output_dir: 输出目录
      - dz: float (depthwise)
      - sample_stride: int (global)
    """
    def set_progress(message: str, percentage: Optional[float] = None):
        progress_messages[session_id] = {
            'message': message,
            'percentage': percentage,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        # 限制打印频率
        should_print = False
        if percentage is None:
            should_print = True
        else:
            last_pct = last_printed_percentage.get(session_id, -1)
            if (percentage - last_pct >= 5) or percentage in (0, 100):
                should_print = True
                last_printed_percentage[session_id] = percentage
        if should_print:
            print(f"[StressInv][{session_id[:8]}] {message}")

    mode = kwargs.get('mode', 'global')
    input_path = kwargs['input_path']
    output_dir = kwargs['output_dir']
    os.makedirs(output_dir, exist_ok=True)

    set_progress("开始地应力反演...", 0)

    # 解析打印行，更新进度
    def on_line(line: str):
        # 例: [GlobalInv] Iter 3 | step=20.000° | candidates=1280 | samples=3049
        if "[GlobalInv] Iter " in line:
            try:
                part = line.split("Iter")[1].strip()
                iter_idx = int(part.split("|")[0].strip())
                # 全局反演固定最多约 12 次迭代（由区间 45 -> ... -> 0.52）
                pct = min(99.0, iter_idx / 12.0 * 100.0)
                set_progress(f"全局反演：第 {iter_idx}/≈12 次迭代", pct)
            except Exception:
                set_progress("全局反演进行中...", None)
        # 例: Progress: 5/42
        elif line.strip().startswith("Progress:"):
            try:
                p = line.split(":")[1].strip()
                cur, total = p.split("/")
                cur, total = int(cur), int(total)
                pct = min(99.0, cur / max(1, total) * 100.0)
                set_progress(f"分段反演：窗口 {cur}/{total}", pct)
            except Exception:
                set_progress("分段反演进行中...", None)

    # 劫持 stdout
    interceptor = _StdoutInterceptor(on_line=on_line)
    orig_stdout_write = sys.stdout.write
    interceptor.bind_original(orig_stdout_write)

    try:
        sys.stdout.write = interceptor.write  # type: ignore
        if mode == 'global':
            mat_name = 'EllipseStressInv_py.mat'
            output_mat = os.path.join(output_dir, mat_name)
            out = invert_global(
                input_filename=input_path,
                output_filename=output_mat,
                sample_stride=int(kwargs.get('sample_stride', 1)) if kwargs.get('sample_stride') else 1
            )
            output_json = os.path.splitext(output_mat)[0] + '.json'
            set_progress("全局反演完成，正在保存结果...", 99.0)
            result = {
                'success': True,
                'mode': 'global',
                'files': {'mat': output_mat, 'json': output_json},
                'out': out
            }
        else:
            dz = float(kwargs.get('dz', 25.0))
            mat_name = f'EllipseStressInv_win{int(dz)}m_py.mat'
            output_mat = os.path.join(output_dir, mat_name)
            out_list = invert_depthwise(
                input_filename=input_path,
                output_filename=output_mat,
                dz=dz
            )
            output_json = os.path.splitext(output_mat)[0] + '.json'
            set_progress("分段反演完成，正在保存结果...", 99.0)
            result = {
                'success': True,
                'mode': 'depthwise',
                'dz': dz,
                'files': {'mat': output_mat, 'json': output_json},
                'out': out_list
            }

        set_progress("计算完成！", 100.0)
        return result

    except Exception as e:
        set_progress(f"计算异常: {str(e)}", None)
        return {'success': False, 'message': str(e)}

    finally:
        # 恢复 stdout
        try:
            sys.stdout.write = orig_stdout_write  # type: ignore
        except Exception:
            pass
        if session_id in last_printed_percentage:
            del last_printed_percentage[session_id]


