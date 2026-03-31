"""
Тест для проверки работы SOCKS5 прокси с Anthropic API
"""

import os
from unittest.mock import patch


def str_to_bool(value: str) -> bool:
    """Простая реализация str_to_bool для тестов"""
    return value.lower() in ("true", "1", "yes", "on")


def should_use_socks5_proxy_for_anthropic(url: str) -> bool:
    """
    Determine if SOCKS5 proxy should be used for Anthropic requests.
    
    Checks if:
    1. LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC environment variable is set to "True"
    2. The URL is for the Anthropic API (api.anthropic.com)
    
    Args:
        url: The request URL
        
    Returns:
        bool: True if SOCKS5 proxy should be used, False otherwise
    """
    # Check if SOCKS5 proxy is enabled for Anthropic
    use_socks5_proxy = str_to_bool(
        os.getenv("LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC", "False")
    )
    
    # Check if this is an Anthropic API request
    is_anthropic_request = "api.anthropic.com" in url
    
    return use_socks5_proxy and is_anthropic_request


def test_should_use_socks5_proxy_for_anthropic():
    """Тест функции should_use_socks5_proxy_for_anthropic"""
    
    # Тест 1: Переменная окружения не установлена, URL Anthropic
    with patch.dict(os.environ, {}, clear=True):
        assert should_use_socks5_proxy_for_anthropic("https://api.anthropic.com/v1/messages") == False
    
    # Тест 2: Переменная окружения установлена в False, URL Anthropic
    with patch.dict(os.environ, {"LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC": "False"}):
        assert should_use_socks5_proxy_for_anthropic("https://api.anthropic.com/v1/messages") == False
    
    # Тест 3: Переменная окружения установлена в True, URL Anthropic
    with patch.dict(os.environ, {"LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC": "True"}):
        assert should_use_socks5_proxy_for_anthropic("https://api.anthropic.com/v1/messages") == True
    
    # Тест 4: Переменная окружения установлена в True, URL не Anthropic
    with patch.dict(os.environ, {"LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC": "True"}):
        assert should_use_socks5_proxy_for_anthropic("https://api.openai.com/v1/chat/completions") == False
    
    # Тест 5: Переменная окружения установлена в 1 (как True), URL Anthropic
    with patch.dict(os.environ, {"LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC": "1"}):
        assert should_use_socks5_proxy_for_anthropic("https://api.anthropic.com/v1/messages") == True
    
    print("Все тесты прошли успешно!")


if __name__ == "__main__":
    test_should_use_socks5_proxy_for_anthropic()