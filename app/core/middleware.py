import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log Request
        logger.info(f"Incoming Request: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Log Response
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Response: {response.status_code} "
                f"Duration: {process_time:.2f}ms"
            )
            
            return response
        except Exception as e:
            # Log Exception (Middleware level catch, though main exception handler should catch it too)
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Request Failed: {request.method} {request.url.path} "
                f"Duration: {process_time:.2f}ms Error: {str(e)}"
            )
            raise e
