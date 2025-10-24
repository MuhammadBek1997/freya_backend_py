"""
Rate limiting middleware for payment endpoints
"""
import time
from typing import Dict, Any
from fastapi import Request, HTTPException, status
from collections import defaultdict, deque


class RateLimiter:
    """Rate limiter for API endpoints"""
    
    def __init__(self):
        # IP address va endpoint uchun so'rovlar tarixi
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        # Karta tokenizatsiyasi uchun maxsus limit
        self.card_token_requests: Dict[str, deque] = defaultdict(lambda: deque())
        
    def is_allowed(self, key: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
        """
        So'rov ruxsat etilganligini tekshirish
        
        Args:
            key: Unique identifier (IP + endpoint)
            max_requests: Maksimal so'rovlar soni
            window_seconds: Vaqt oynasi (soniyalarda)
        """
        now = time.time()
        requests = self.requests[key]
        
        # Eski so'rovlarni tozalash
        while requests and requests[0] < now - window_seconds:
            requests.popleft()
        
        # Limit tekshiruvi
        if len(requests) >= max_requests:
            return False
        
        # Yangi so'rovni qo'shish
        requests.append(now)
        return True
    
    def is_card_token_allowed(self, ip: str, max_requests: int = 3, window_seconds: int = 300) -> bool:
        """
        Karta tokenizatsiyasi uchun maxsus rate limiting
        
        Args:
            ip: IP address
            max_requests: Maksimal so'rovlar soni (3 ta 5 daqiqada)
            window_seconds: Vaqt oynasi (300 soniya = 5 daqiqa)
        """
        now = time.time()
        requests = self.card_token_requests[ip]
        
        # Eski so'rovlarni tozalash
        while requests and requests[0] < now - window_seconds:
            requests.popleft()
        
        # Limit tekshiruvi
        if len(requests) >= max_requests:
            return False
        
        # Yangi so'rovni qo'shish
        requests.append(now)
        return True
    
    def get_remaining_time(self, key: str, window_seconds: int = 60) -> int:
        """
        Keyingi so'rov uchun kutish vaqtini qaytarish
        """
        requests = self.requests[key]
        if not requests:
            return 0
        
        oldest_request = requests[0]
        remaining = window_seconds - (time.time() - oldest_request)
        return max(0, int(remaining))


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(request: Request, max_requests: int = 10, window_seconds: int = 60):
    """
    Rate limit tekshiruvi uchun dependency
    """
    client_ip = request.client.host
    endpoint = request.url.path
    key = f"{client_ip}:{endpoint}"
    
    if not rate_limiter.is_allowed(key, max_requests, window_seconds):
        remaining_time = rate_limiter.get_remaining_time(key, window_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Juda ko'p so'rov. {remaining_time} soniyadan keyin qayta urinib ko'ring.",
            headers={"Retry-After": str(remaining_time)}
        )


def check_card_token_rate_limit(request: Request):
    """
    Karta tokenizatsiyasi uchun maxsus rate limit tekshiruvi
    """
    client_ip = request.client.host
    
    if not rate_limiter.is_card_token_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Karta tokenizatsiyasi uchun juda ko'p so'rov. 5 daqiqadan keyin qayta urinib ko'ring.",
            headers={"Retry-After": "300"}
        )