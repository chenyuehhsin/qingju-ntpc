from __future__ import annotations

import os
from pathlib import Path
import sys
import types

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server import ai_service  # noqa: E402


class FakeResponse:
    output_text = "這是根據 evidence 的 LLM 說明。"


class InvalidResponse:
    output_text = ""


def install_fake_openai(response_class=FakeResponse, exc: Exception | None = None) -> None:
    class FakeResponses:
        def create(self, **_kwargs):
            if exc:
                raise exc
            return response_class()

    class FakeClient:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    module = types.ModuleType("openai")
    module.OpenAI = FakeClient
    sys.modules["openai"] = module


def clear_fake_openai() -> None:
    sys.modules.pop("openai", None)


def assert_openai_enabled_uses_llm_text() -> None:
    os.environ["OPENAI_API_KEY"] = "test-key"
    install_fake_openai()
    result = ai_service.assistant_response("哪區工作機會最多？")
    assert result["answer_source"] == "openai"
    assert result["answer"] == FakeResponse.output_text
    clear_fake_openai()


def assert_no_api_key_falls_back() -> None:
    os.environ.pop("OPENAI_API_KEY", None)
    result = ai_service.assistant_response("哪區工作機會最多？")
    assert result["answer_source"] == "deterministic_template"
    assert result["recommendations"]


def assert_timeout_falls_back() -> None:
    os.environ["OPENAI_API_KEY"] = "test-key"
    install_fake_openai(exc=TimeoutError("timeout"))
    result = ai_service.assistant_response("哪區工作機會最多？")
    assert result["answer_source"] == "deterministic_template"
    clear_fake_openai()


def assert_http_error_falls_back() -> None:
    os.environ["OPENAI_API_KEY"] = "test-key"
    install_fake_openai(exc=RuntimeError("500 server error"))
    result = ai_service.assistant_response("哪區工作機會最多？")
    assert result["answer_source"] == "deterministic_template"
    clear_fake_openai()


def assert_invalid_response_falls_back() -> None:
    os.environ["OPENAI_API_KEY"] = "test-key"
    install_fake_openai(response_class=InvalidResponse)
    result = ai_service.assistant_response("哪區工作機會最多？")
    assert result["answer_source"] == "deterministic_template"
    clear_fake_openai()


def main() -> int:
    original_key = os.environ.get("OPENAI_API_KEY")
    tests = [
        assert_openai_enabled_uses_llm_text,
        assert_no_api_key_falls_back,
        assert_timeout_falls_back,
        assert_http_error_falls_back,
        assert_invalid_response_falls_back,
    ]
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        clear_fake_openai()
        if original_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = original_key
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
