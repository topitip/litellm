# Настройка SOCKS5 прокси для Anthropic

Это руководство описывает, как настроить использование SOCKS5 прокси для всех запросов к API Anthropic в LiteLLM.

## Переменные окружения

Для включения SOCKS5 прокси для Anthropic, установите следующие переменные окружения:

```bash
# Включить использование SOCKS5 прокси для Anthropic
LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC=true

# URL SOCKS5 прокси
LITELLM_SOCKS5_PROXY_URL=socks5://username:password@proxy_host:proxy_port
```

## Примеры конфигурации

### Базовая конфигурация

```bash
export LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC=true
export LITELLM_SOCKS5_PROXY_URL=socks5://proxy_user:rIdihHAC17kxkKPR@80.74.31.177:36943
```

### Конфигурация в docker-compose.yml

```yaml
version: '3.8'
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    environment:
      - LITELLM_USE_SOCKS5_PROXY_FOR_ANTHROPIC=true
      - LITELLM_SOCKS5_PROXY_URL=socks5://proxy_user:rIdihHAC17kxkKPR@80.74.31.177:36943
      - ANTHROPIC_API_KEY=your-anthropic-api-key
    ports:
      - "4000:4000"
```

## Поддерживаемые форматы прокси

LiteLLM поддерживает следующие форматы URL прокси:

- `socks5://username:password@host:port` - SOCKS5 с аутентификацией
- `socks5://host:port` - SOCKS5 без аутентификации
- `socks5h://username:password@host:port` - SOCKS5 с удаленным DNS

## Требования к зависимостям

Для работы SOCKS5 прокси необходимо установить дополнительные зависимости:

### Для асинхронных запросов (рекомендуется)

```bash
# Установка как опциональной зависимости LiteLLM
pip install 'litellm[proxy]'

# Или установка напрямую
pip install aiohttp_socks
```

### Для синхронных запросов

Синхронные запросы используют встроенную поддержку прокси в httpx, дополнительные зависимости не требуются.

## Проверка работы

После настройки вы можете проверить работу прокси следующим образом:

1. Убедитесь, что переменные окружения установлены правильно
2. Выполните тестовый запрос к Anthropic API через LiteLLM
3. Проверьте логи прокси-сервера на наличие запросов

## Устранение неполадок

### Проблемы с импортом aiohttp_socks

Если вы получаете ошибку импорта `aiohttp_socks`, установите пакет:

```bash
pip install aiohttp_socks
```

### Проблемы с подключением

1. Проверьте правильность URL прокси
2. Убедитесь, что прокси-сервер доступен и работает
3. Проверьте учетные данные прокси (если требуется аутентификация)
4. Убедитесь, что порт прокси открыт в брандмауэре

### Логирование

Для включения подробного логирования установите уровень логирования:

```bash
export LITELLM_LOG_LEVEL=DEBUG
```

## Безопасность

- Храните учетные данные прокси в защищенном месте
- Используйте зашифрованные переменные окружения в production
- Регулярно меняйте пароли прокси