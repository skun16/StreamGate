import json


def sse_event(data: dict) -> str:
    """
    将 dict 转成 SSE 格式。
    """

    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
