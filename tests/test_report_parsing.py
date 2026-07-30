"""Unit tests for the tolerant SUMMARY / RECOMMENDED_NEXT_STEP parser."""
from fraud_crew.crew.report_parsing import parse_writer_output


def test_parses_both_labeled_sections():
    raw = "SUMMARY: hello world\nRECOMMENDED_NEXT_STEP: do the thing"
    summary, next_step = parse_writer_output(raw, fallback_next_step="fallback")
    assert summary == "hello world"
    assert next_step == "do the thing"


def test_falls_back_to_whole_text_and_default_next_step_when_unlabeled():
    raw = "just some free text with no labels at all"
    summary, next_step = parse_writer_output(raw, fallback_next_step="fallback next step")
    assert summary == raw
    assert next_step == "fallback next step"


def test_multiline_summary_is_captured_up_to_next_step_label():
    raw = "SUMMARY: line one\nline two\nRECOMMENDED_NEXT_STEP: escalate"
    summary, next_step = parse_writer_output(raw, fallback_next_step="fallback")
    assert "line one" in summary and "line two" in summary
    assert next_step == "escalate"
