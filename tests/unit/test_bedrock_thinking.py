from app.core.bedrock import ThinkingStreamFilter, strip_thinking_text


def test_strip_thinking_text_removes_block():
    raw = "Hello <think>secret</think> world"
    assert strip_thinking_text(raw) == "Hello  world"


def test_thinking_stream_filter_strips_mid_stream():
    filt = ThinkingStreamFilter()
    parts = [
        filt.push("Before "),
        filt.push("<think>"),
        filt.push("hidden reasoning"),
        filt.push("</think>"),
        filt.push(" after"),
        filt.finish(),
    ]
    assert "".join(parts) == "Before  after"
