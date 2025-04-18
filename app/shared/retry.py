"""
Retry module for handling transient failures.

Provides decorators and utilities for automatically retrying
operations that may fail due to transient issues.
"""
import time
import logging
import functools
import random
from typing import Callable, Any, Dict, List, Optional, Type, Union, Tuple
import inspect
import asyncio

logger = logging.getLogger("retry")

def retry(
    max_tries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    jitter: bool = True,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Retry decorator with exponential backoff for regular functions
    
    Args:
        max_tries: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier (e.g. value of 2 will double the delay each retry)
        exceptions: Exception(s) that trigger a retry
        jitter: Whether to add randomness to the delay
        on_retry: Function to call on retry
    
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_tries, delay
            
            for i in range(max_tries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Last attempt failed with allowed exception
                    if i + 1 == max_tries:
                        raise
                    
                    # Calculate next delay
                    sleep = mdelay
                    if jitter:
                        sleep = sleep * (1 + random.random() * 0.1)
                    
                    # Call on_retry function if provided
                    if on_retry:
                        on_retry(e, i + 1, sleep)
                    
                    # Log retry
                    logger.warning(
                        f"Retrying {func.__name__} ({i+1}/{max_tries}) in {sleep:.2f}s after error: {str(e)}"
                    )
                    
                    # Wait before next attempt
                    time.sleep(sleep)
                    
                    # Increase delay for next time
                    mdelay *= backoff
            
            # Should never reach here, but just in case
            return func(*args, **kwargs)
        return wrapper
    return decorator

def async_retry(
    max_tries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    jitter: bool = True,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Retry decorator with exponential backoff for async functions
    
    Args:
        max_tries: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier (e.g. value of 2 will double the delay each retry)
        exceptions: Exception(s) that trigger a retry
        jitter: Whether to add randomness to the delay
        on_retry: Function to call on retry
    
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            mtries, mdelay = max_tries, delay
            
            for i in range(max_tries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    # Last attempt failed with allowed exception
                    if i + 1 == max_tries:
                        raise
                    
                    # Calculate next delay
                    sleep = mdelay
                    if jitter:
                        sleep = sleep * (1 + random.random() * 0.1)
                    
                    # Call on_retry function if provided
                    if on_retry:
                        on_retry(e, i + 1, sleep)
                    
                    # Log retry
                    logger.warning(
                        f"Retrying {func.__name__} ({i+1}/{max_tries}) in {sleep:.2f}s after error: {str(e)}"
                    )
                    
                    # Wait before next attempt
                    await asyncio.sleep(sleep)
                    
                    # Increase delay for next time
                    mdelay *= backoff
            
            # Should never reach here, but just in case
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class RetryableError(Exception):
    """Base exception class for errors that can be retried"""
    pass

class NetworkError(RetryableError):
    """Network-related errors that can be retried"""
    pass

class TemporaryServiceError(RetryableError):
    """Temporary service errors that can be retried"""
    pass

def is_retryable_exception(exception: Exception) -> bool:
    """
    Determine if an exception should be retried
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if exception should be retried
    """
    # Check for our custom retryable exceptions
    if isinstance(exception, RetryableError):
        return True
        
    # Check for common network-related exceptions
    exception_str = str(exception).lower()
    network_errors = [
        'timeout', 'connection', 'socket', 'network', 
        'temporary', 'retry', 'reset', 'closed', 'broken pipe',
        'floodwaiterror', 'too many requests', 'rate limit',
        'server error', 'service unavailable'
    ]
    
    if any(err in exception_str for err in network_errors):
        return True
    
    # Check for common HTTP status codes that are retryable
    status_codes = ['429', '500', '502', '503', '504']
    if any(code in exception_str for code in status_codes):
        return True
        
    return False