"""
Rate limiting middleware for API protection
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time


class RateLimiter:
    """Simple in-memory rate limiter (for production, use Redis)"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed
        
        Returns:
            (is_allowed, remaining_requests)
        """
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False, 0
        
        # Add current request
        self.requests[client_id].append(now)
        remaining = self.requests_per_minute - len(self.requests[client_id])
        
        return True, remaining
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Use IP address or user ID if authenticated
        if hasattr(request.state, 'user') and request.state.user:
            return f"user_{request.state.user.id}"
        return f"ip_{request.client.host}"


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/docs", "/openapi.json", "/"]:
        return await call_next(request)
    
    client_id = rate_limiter.get_client_id(request)
    is_allowed, remaining = rate_limiter.is_allowed(client_id)
    
    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "retry_after": 60
            },
            headers={"X-RateLimit-Remaining": "0", "Retry-After": "60"}
        )
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
    
    return response
