import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(
    0, os.path.abspath("../../../../..")
)  # Adds the parent directory to the system path

from litellm.llms.hosted_vllm.chat.transformation import HostedVLLMChatConfig
from litellm.utils import _fix_empty_parameters, _fix_schema_required_field


def test_hosted_vllm_chat_transformation_file_url():
    config = HostedVLLMChatConfig()
    video_url = "https://example.com/video.mp4"
    video_data = f"data:video/mp4;base64,{video_url}"
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "file",
                    "file": {
                        "file_data": video_data,
                    },
                }
            ],
        }
    ]
    transformed_response = config.transform_request(
        model="hosted_vllm/llama-3.1-70b-instruct",
        messages=messages,
        optional_params={},
        litellm_params={},
        headers={},
    )
    assert transformed_response["messages"] == [
        {
            "role": "user",
            "content": [{"type": "video_url", "video_url": {"url": video_data}}],
        }
    ]


def test_hosted_vllm_chat_transformation_with_audio_url():
    from litellm import completion

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "llama-3.1-70b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    mock_response.text = json.dumps(mock_response.json.return_value)
    mock_client.post.return_value = mock_response

    with patch(
        "litellm.llms.custom_httpx.llm_http_handler._get_httpx_client",
        return_value=mock_client,
    ):
        try:
            completion(
                model="hosted_vllm/llama-3.1-70b-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "audio_url",
                                "audio_url": {"url": "https://example.com/audio.mp3"},
                            },
                        ],
                    },
                ],
                api_base="https://test-vllm.example.com/v1",
            )
        except Exception:
            pass

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args[1]
        request_data = json.loads(call_kwargs["data"])
        assert request_data["messages"] == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio_url",
                        "audio_url": {"url": "https://example.com/audio.mp3"},
                    }
                ],
            }
        ]


def test_hosted_vllm_supports_reasoning_effort():
    config = HostedVLLMChatConfig()
    supported_params = config.get_supported_openai_params(
        model="hosted_vllm/gpt-oss-120b"
    )
    assert "reasoning_effort" in supported_params
    optional_params = config.map_openai_params(
        non_default_params={"reasoning_effort": "high"},
        optional_params={},
        model="hosted_vllm/gpt-oss-120b",
        drop_params=False,
    )
    assert optional_params["reasoning_effort"] == "high"


def test_hosted_vllm_supports_thinking():
    """
    Test that hosted_vllm supports the 'thinking' parameter.

    Anthropic-style thinking is converted to OpenAI-style reasoning_effort
    since vLLM is OpenAI-compatible.

    Related issue: https://github.com/BerriAI/litellm/issues/19761
    """
    config = HostedVLLMChatConfig()
    supported_params = config.get_supported_openai_params(
        model="hosted_vllm/GLM-4.6-FP8"
    )
    assert "thinking" in supported_params

    # Test thinking with low budget_tokens -> "minimal" (for < 2000)
    optional_params = config.map_openai_params(
        non_default_params={"thinking": {"type": "enabled", "budget_tokens": 1024}},
        optional_params={},
        model="hosted_vllm/GLM-4.6-FP8",
        drop_params=False,
    )
    assert "thinking" not in optional_params  # thinking should NOT be passed
    assert optional_params["reasoning_effort"] == "minimal"

    # Test thinking with high budget_tokens -> "high"
    optional_params = config.map_openai_params(
        non_default_params={"thinking": {"type": "enabled", "budget_tokens": 15000}},
        optional_params={},
        model="hosted_vllm/GLM-4.6-FP8",
        drop_params=False,
    )
    assert optional_params["reasoning_effort"] == "high"

    # Test that existing reasoning_effort is not overwritten
    optional_params = config.map_openai_params(
        non_default_params={
            "thinking": {"type": "enabled", "budget_tokens": 15000},
            "reasoning_effort": "low",
        },
        optional_params={},
        model="hosted_vllm/GLM-4.6-FP8",
        drop_params=False,
    )
    assert optional_params["reasoning_effort"] == "low"


def test_hosted_vllm_thinking_blocks_prepended_to_assistant_content():
    """
    Test that thinking_blocks on assistant messages are converted to content
    blocks prepended before the existing content.
    """
    config = HostedVLLMChatConfig()
    messages = [
        {
            "role": "user",
            "content": "Hello",
        },
        {
            "role": "assistant",
            "content": "Here is my answer.",
            "thinking_blocks": [
                {
                    "type": "thinking",
                    "thinking": "Let me reason about this...",
                    "signature": "abc123",
                }
            ],
        },
        {
            "role": "user",
            "content": "Follow up question",
        },
    ]
    transformed = config.transform_request(
        model="hosted_vllm/llama-3.1-70b-instruct",
        messages=messages,
        optional_params={},
        litellm_params={},
        headers={},
    )
    assistant_msg = transformed["messages"][1]
    assert assistant_msg["role"] == "assistant"
    assert isinstance(assistant_msg["content"], list)
    assert assistant_msg["content"][0] == {
        "type": "thinking",
        "thinking": "Let me reason about this...",
    }
    assert assistant_msg["content"][1] == {
        "type": "text",
        "text": "Here is my answer.",
    }
    assert "thinking_blocks" not in assistant_msg


def test_fix_schema_required_field_empty_dict():
    """
    Test that _fix_schema_required_field converts required: {} to required: [].

    VLLM rejects tool schemas where 'required' is not an array.
    """
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "required": {},
    }
    result = _fix_schema_required_field(schema)
    assert result["required"] == []


def test_fix_schema_required_field_nested():
    """
    Test that _fix_schema_required_field fixes nested required fields.
    """
    schema = {
        "type": "object",
        "properties": {
            "address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                },
                "required": {},
            },
        },
        "required": ["address"],
    }
    result = _fix_schema_required_field(schema)
    assert result["required"] == ["address"]
    assert result["properties"]["address"]["required"] == []


def test_fix_schema_required_field_valid_array_unchanged():
    """
    Test that _fix_schema_required_field leaves valid required arrays untouched.
    """
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "required": ["name"],
    }
    result = _fix_schema_required_field(schema)
    assert result["required"] == ["name"]


def test_fix_empty_parameters_empty_dict():
    """
    Test that _fix_empty_parameters converts parameters: {} to a valid schema.

    Cloud.ru/foundation-models rejects parameters: {} and requires at minimum:
        {"type": "object", "properties": {}}
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {},
            },
        }
    ]
    result = _fix_empty_parameters(tools)
    params = result[0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"] == {}


def test_fix_empty_parameters_none():
    """
    Test that _fix_empty_parameters handles parameters: None.
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool",
            },
        }
    ]
    result = _fix_empty_parameters(tools)
    params = result[0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"] == {}


def test_fix_empty_parameters_missing_type_or_properties():
    """
    Test that _fix_empty_parameters adds missing 'type' and 'properties' keys.
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "parameters": {
                    "required": ["foo"],
                },
            },
        }
    ]
    result = _fix_empty_parameters(tools)
    params = result[0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"] == {}
    assert params["required"] == ["foo"]


def test_fix_empty_parameters_valid_unchanged():
    """
    Test that _fix_empty_parameters leaves valid parameters untouched.
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    result = _fix_empty_parameters(tools)
    params = result[0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"] == {"location": {"type": "string"}}
    assert params["required"] == ["location"]


def test_hosted_vllm_tools_required_field_fixed():
    """
    Test that hosted_vllm transformation fixes invalid required fields in tools.
    """
    config = HostedVLLMChatConfig()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": {},
                },
            },
        }
    ]
    result = config.map_openai_params(
        non_default_params={"tools": tools},
        optional_params={},
        model="hosted_vllm/test-model",
        drop_params=False,
    )
    required_field = result["tools"][0]["function"]["parameters"]["required"]
    assert isinstance(required_field, list)
    assert required_field == []


def test_hosted_vllm_tools_empty_parameters_fixed():
    """
    Test that hosted_vllm transformation fixes empty parameters: {} in tools.

    Reproduces the error:
    "Tool 0 function has invalid 'parameters' schema: {} is not of type 'array'"
    from Cloud.ru/foundation-models backend.
    """
    config = HostedVLLMChatConfig()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "do_something",
                "description": "Does something",
                "parameters": {},
            },
        }
    ]
    result = config.transform_request(
        model="hosted_vllm/test-model",
        messages=[{"role": "user", "content": "Hello"}],
        optional_params={"tools": tools},
        litellm_params={},
        headers={},
    )
    params = result["tools"][0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"] == {}


def test_hosted_vllm_thinking_blocks_with_list_content():
    """
    Test thinking_blocks prepended when assistant content is already a list.
    """
    config = HostedVLLMChatConfig()
    messages = [
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Response text"}],
            "thinking_blocks": [
                {
                    "type": "thinking",
                    "thinking": "Step 1 reasoning",
                    "signature": "sig1",
                },
                {
                    "type": "thinking",
                    "thinking": "Step 2 reasoning",
                    "signature": "sig2",
                },
            ],
        },
    ]
    transformed = config.transform_request(
        model="hosted_vllm/llama-3.1-70b-instruct",
        messages=messages,
        optional_params={},
        litellm_params={},
        headers={},
    )
    assistant_msg = transformed["messages"][0]
    assert len(assistant_msg["content"]) == 3
    assert assistant_msg["content"][0] == {
        "type": "thinking",
        "thinking": "Step 1 reasoning",
    }
    assert assistant_msg["content"][1] == {
        "type": "thinking",
        "thinking": "Step 2 reasoning",
    }
    assert assistant_msg["content"][2] == {"type": "text", "text": "Response text"}
    assert "thinking_blocks" not in assistant_msg
