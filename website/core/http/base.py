import logging
import time
import requests
from datetime import datetime
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class BaseHttpClient:
    max_retries = 3
    backoff_seconds = 1

    def request(self, method, url, payload=None, headers=None, params=None, **kwargs):
        attempt = 0
        start = time.time()

        while attempt < self.max_retries:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=headers,
                    params=params,
                    **kwargs
                )
                self.log_request(method, url, payload, headers, response, start_time=start)
                response.raise_for_status()
                return response
            except RequestException as e:
                attempt += 1
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt >= self.max_retries:
                    self.log_request(method, url, payload, headers, response=None, start_time=start)
                    raise
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

    def log_request(self, method, url, payload, headers, response, start_time):
        duration = time.time() - start_time
        logger.info(
            f"[{datetime.now().isoformat()}] Outbound Request",
            extra={
                "method": method,
                "url": url,
                "payload": payload,
                "headers": headers,
                "response_status": getattr(response, "status_code", None),
                "response_body": getattr(response, "text", None),
                "duration_seconds": duration,
            }
        )