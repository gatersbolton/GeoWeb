from typing import Dict, Any

import pandas as pd

from ..core.progress import progress_messages, last_printed_percentage
from ..thirdparty.borehole_ellip import process_borehole_ellipticity


def run_borehole_calculation_with_progress(session_id: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """在单独线程中运行钻孔计算，支持进度回调（从 app.py 迁移，逻辑保持不变）"""

    def borehole_progress_callback(message, percentage):
        progress_messages[session_id] = {
            'message': message,
            'percentage': percentage,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        should_print = False
        if percentage is None:
            should_print = True
        else:
            last_pct = last_printed_percentage.get(session_id, -1)
            if (percentage - last_pct >= 20 or
                percentage == 100 or
                'Loading' in message or
                'Saving' in message or
                '完成' in message or
                '失败' in message):
                should_print = True
                last_printed_percentage[session_id] = percentage
        if should_print:
            print(f"进度更新 [{session_id[:8]}]: {message}")

    try:
        print(f"开始计算任务 [{session_id}]")
        progress_messages[session_id] = {
            'message': '开始计算钻孔椭圆度数据...',
            'percentage': 0,
            'timestamp': pd.Timestamp.now().isoformat()
        }

        kwargs['progress_callback'] = borehole_progress_callback
        result = process_borehole_ellipticity(**kwargs)

        if result['success']:
            progress_messages[session_id] = {
                'message': '计算完成!',
                'percentage': 100,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            print(f"计算完成 [{session_id[:8]}]")
        else:
            progress_messages[session_id] = {
                'message': '计算失败',
                'percentage': None,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            print(f"计算失败 [{session_id[:8]}]")

        if session_id in last_printed_percentage:
            del last_printed_percentage[session_id]

        return result

    except Exception as e:
        error_msg = f"计算失败: {str(e)}"
        progress_messages[session_id] = {
            'message': error_msg,
            'percentage': None,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        print(f"计算异常 [{session_id[:8]}]: {error_msg}")

        if session_id in last_printed_percentage:
            del last_printed_percentage[session_id]

        return {'success': False, 'message': str(e)}


