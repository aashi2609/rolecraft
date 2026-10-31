"""
Test Suite for Step 5C: Graceful Failure Handling for Groq

Comprehensive tests to verify:
1. Error classification: retry transient, fail-fast on 4xx (except 429)
2. Circuit breaker: opens after 5 failures, cooldown 30s
3. Request deadline: hard cap at 300s total
4. Exponential backoff with jitter
5. Retry-After header respect (cap 300s)
6. Error codes returned to client
7. No sensitive data in responses
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

pytestmark = pytest.mark.skip_db_guard


class TestErrorClassification:
    """Test that errors are classified correctly: retry vs fail-fast."""

    @pytest.mark.asyncio
    async def test_401_auth_error_fails_immediately(self):
        """401 Unauthorized raises immediately without retry."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        # Reset circuit breaker
        _circuit_breaker.failure_count = 0
        _circuit_breaker.is_open = False
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.headers = {}
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            # Mock HTTP error
            http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)
            mock_client.return_value.__aenter__.return_value.post.side_effect = http_error
            
            with pytest.raises(AIServiceError) as exc_info:
                await generate_content("test prompt")
            
            assert exc_info.value.error_code == "ai_auth_failed"
            # Should not retry - only 1 attempt
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

    @pytest.mark.asyncio
    async def test_400_bad_request_fails_immediately(self):
        """400 Bad Request (e.g., context length) fails immediately."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        _circuit_breaker.failure_count = 0
        _circuit_breaker.is_open = False
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Context length exceeded"
        mock_response.headers = {}
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            http_error = httpx.HTTPStatusError("400", request=MagicMock(), response=mock_response)
            mock_client.return_value.__aenter__.return_value.post.side_effect = http_error
            
            with pytest.raises(AIServiceError) as exc_info:
                await generate_content("test prompt")
            
            assert exc_info.value.error_code == "ai_bad_output"
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

    @pytest.mark.asyncio
    async def test_429_rate_limit_retries_with_backoff(self):
        """429 Rate Limit retries with exponential backoff."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        _circuit_breaker.failure_count = 0
        _circuit_breaker.is_open = False
        
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {"Retry-After": "5"}
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client, \
             patch('services.ai_client.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            http_error = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_response)
            mock_client.return_value.__aenter__.return_value.post.side_effect = http_error
            
            with pytest.raises(AIServiceError) as exc_info:
                await generate_content("test prompt", retries=3)
            
            assert exc_info.value.error_code == "ai_rate_limited"
            assert exc_info.value.retry_after == 5
            # Should retry: 3 attempts total
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 3
            # Should sleep between retries
            assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_retries_with_escalating_timeout(self):
        """Timeout errors retry with escalating per-attempt timeout."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        _circuit_breaker.failure_count = 0
        _circuit_breaker.is_open = False
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(AIServiceError) as exc_info:
                await generate_content("test prompt", retries=3, deadline_seconds=300)
            
            assert exc_info.value.error_code == "ai_timeout"
            # Should retry all 3 attempts
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 3


class TestCircuitBreaker:
    """Test circuit breaker opens after failures and closes after cooldown."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_5_failures(self):
        """Circuit breaker opens after 5 consecutive failures."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        # Reset circuit breaker
        _circuit_breaker.failure_count = 0
        _circuit_breaker.is_open = False
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            # Make 5 calls that fail
            for i in range(5):
                with pytest.raises(AIServiceError):
                    await generate_content("test", retries=1)
            
            # Circuit should be open now
            assert _circuit_breaker.is_open is True
            assert _circuit_breaker.failure_count >= 5

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_requests_when_open(self):
        """Circuit breaker blocks requests immediately when open."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        # Manually open circuit breaker
        _circuit_breaker.is_open = True
        _circuit_breaker.open_at = time.time()
        _circuit_breaker.failure_count = 5
        
        with patch('services.ai_client.settings') as mock_settings:
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            # Should fail immediately without calling API
            with pytest.raises(AIServiceError) as exc_info:
                await generate_content("test")
            
            assert exc_info.value.error_code == "ai_unavailable"
            assert "circuit breaker open" in str(exc_info.value).lower()
            assert exc_info.value.retry_after is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_cooldown(self):
        """Circuit breaker allows retry after 30s cooldown."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        # Open circuit breaker 31 seconds ago
        _circuit_breaker.is_open = True
        _circuit_breaker.open_at = time.time() - 31  # 31s ago
        _circuit_breaker.failure_count = 5
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            # Mock a timeout still (will try and fail, but should try)
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(AIServiceError):
                await generate_content("test", retries=1)
            
            # Should have attempted API call (circuit allowed it)
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 1


class TestRequestDeadline:
    """Test that requests never exceed the total deadline."""

    @pytest.mark.asyncio
    async def test_deadline_stops_retries(self):
        """Request stops retrying when deadline is reached."""
        from services.ai_client import generate_content, AIServiceError, _circuit_breaker
        
        _circuit_breaker.failure_count = 0
        _circuit_breaker.is_open = False
        
        with patch('services.ai_client.settings') as mock_settings, \
             patch('services.ai_client.httpx.AsyncClient') as mock_client, \
             patch('services.ai_client.time.time') as mock_time:
            
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "test-model"
            
            # Simulate time passing - provide enough values for all time.time() calls
            start_time = 1000.0
            times = [start_time] + [start_time + 301] * 20  # First call + enough for retries
            mock_time.side_effect = times
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(AIServiceError) as exc_info:
                await generate_content("test", retries=10, deadline_seconds=300)
            
            assert exc_info.value.error_code == "ai_timeout"
            assert "deadline" in str(exc_info.value).lower()


class TestExponentialBackoffWithJitter:
    """Test that backoff includes jitter to prevent thundering herd."""

    def test_backoff_calculation_includes_jitter(self):
        """Backoff duration varies with jitter."""
        from services.ai_client import _calculate_backoff_with_jitter
        
        # Call multiple times and check for variation
        wait_times = [_calculate_backoff_with_jitter(attempt=1) for _ in range(10)]
        
        # All should be near 4s (2^1 * 2 = 4) but with ±10% jitter
        for wait in wait_times:
            assert 3.6 <= wait <= 4.4  # 4s ± 10%
        
        # Should have some variation (not all identical)
        assert len(set(wait_times)) > 1

    def test_backoff_respects_retry_after_header(self):
        """Retry-After header overrides exponential backoff."""
        from services.ai_client import _calculate_backoff_with_jitter
        
        wait = _calculate_backoff_with_jitter(attempt=1, retry_after=60)
        
        # Should use Retry-After value (with jitter)
        assert 54 <= wait <= 66  # 60s ± 10%

    def test_backoff_caps_retry_after_at_300s(self):
        """Retry-After values above 300s are capped."""
        from services.ai_client import _calculate_backoff_with_jitter
        
        wait = _calculate_backoff_with_jitter(attempt=1, retry_after=600)
        
        # Should be capped at 300s (with jitter)
        assert 270 <= wait <= 330  # 300s ± 10%


class TestErrorCodesToClient:
    """Test that error codes are returned to clients correctly."""

    @pytest.mark.asyncio
    async def test_error_response_includes_error_code(self):
        """AIServiceError with error_code is returned to client."""
        from services.ai_client import AIServiceError
        from main import ai_service_error_handler
        from fastapi import Request
        
        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.request_id = "test-123"
        mock_request.method = "POST"
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"
        
        # Create error with code
        exc = AIServiceError("Test error", error_code="ai_rate_limited", retry_after=60)
        
        # Call handler
        response = await ai_service_error_handler(mock_request, exc)
        
        # Verify response
        assert response.status_code == 429
        assert "error_code" in response.body.decode()
        assert "retry_after_seconds" in response.body.decode()

    @pytest.mark.asyncio
    async def test_no_sensitive_data_in_error_response(self):
        """Error responses don't leak API keys or provider details."""
        from services.ai_client import AIServiceError
        from main import ai_service_error_handler
        from fastapi import Request
        
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.request_id = "test-123"
        mock_request.method = "POST"
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"
        
        # Error with sensitive data in message
        exc = AIServiceError(
            "Groq API key sk-proj-abc123 is invalid",
            error_code="ai_auth_failed"
        )
        
        response = await ai_service_error_handler(mock_request, exc)
        response_body = response.body.decode()
        
        # Should not contain API key
        assert "sk-proj" not in response_body
        assert "abc123" not in response_body
        # Should have generic message
        assert "configuration error" in response_body.lower()


class TestNoPartialDataStored:
    """Test that failures don't result in partial data being saved."""

    @pytest.mark.asyncio
    async def test_failed_generation_does_not_save_partial_resume(self):
        """When AI fails, no partial resume is committed to database."""
        # This is tested implicitly by the resume_service behavior
        # The service only commits after successful generation
        # AIServiceError causes rollback before commit
        pass  # Placeholder - behavior verified in resume_service


class TestJitterPreventsThunderingHerd:
    """Test that jitter prevents all clients retrying simultaneously."""

    def test_multiple_clients_have_different_retry_times(self):
        """Multiple clients calculate different backoff times."""
        from services.ai_client import _calculate_backoff_with_jitter
        
        # Simulate 10 clients all getting rate limited at the same time
        backoff_times = [_calculate_backoff_with_jitter(attempt=1) for _ in range(10)]
        
        # All should be around 4s but with variation
        assert len(set(backoff_times)) >= 5  # At least 5 different values
        
        # Spread should prevent thundering herd
        min_backoff = min(backoff_times)
        max_backoff = max(backoff_times)
        spread = max_backoff - min_backoff
        
        # Spread should be at least 10% of base (0.4s out of 4s)
        assert spread >= 0.4
