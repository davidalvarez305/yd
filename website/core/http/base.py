import logging
import time
import requests
from datetime import datetime
from requests.exceptions import RequestException
from core.models import HTTPLog

logger = logging.getLogger(__name__)

class BaseHttpClient:
    max_retries = 3
    backoff_seconds = 1

    def request(self, method, url, payload=None, headers=None, params=None, **kwargs):
        attempt = 0
        start = time.time()
        last_exception = None

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
                response.raise_for_status()
                self.log_request(method, url, payload, headers, params, response, start, retries=attempt)
                return response
            except RequestException as e:
                last_exception = e
                attempt += 1
                logger.warning(f"Attempt {attempt} failed: {e}")

                if attempt >= self.max_retries:
                    self.log_request(
                        method, url, payload, headers, params,
                        response=None,
                        start_time=start,
                        error=str(e),
                        retries=attempt
                    )
                    raise
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

    def log_request(self, method, url, payload, headers, params, response, start_time, error=None, retries=0):
        duration = time.time() - start_time
        status_code = getattr(response, "status_code", None)

        try:
            response_json = response.json() if response else None
        except Exception:
            response_json = getattr(response, "text", None)

        HTTPLog.objects.create(
            method=method,
            url=url,
            query_params=params,
            payload=payload,
            headers=headers,
            response=response_json,
            status_code=status_code or 500,
            error={"message": error} if error else None,
            duration_seconds=round(duration, 3),
            retries=retries,
            service_name=self.__class__.__name__
        )

        logger.info(
            f"[{datetime.now().isoformat()}] HTTP {method.upper()} to {url} "
            f"(status={status_code}, retries={retries}, duration={duration:.2f}s)"
        )