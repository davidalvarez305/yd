import time
import requests
from datetime import datetime, date
from core.models import HTTPLog
from core.logger import logger

class BaseHttpClient:
    def request(self, method, url, payload=None, headers=None, params=None, **kwargs):
        start = time.time()

        response = requests.request(
            method=method,
            url=url,
            json=self._safe_serialize(payload),
            headers=headers,
            params=params,
            **kwargs
        )

        try:
            if not response.content:
                data = {'data': None}
            elif 'application/json' in response.headers.get('Content-Type', ''):
                data = response.json()
        except Exception as e:
            logger.error(f"Failed to decode JSON from {url}: {e}", exc_info=True)
            data = {'data': response.text or None}

        error = data.get('error')

        self.log_request(
            method=method,
            url=url,
            payload=payload,
            headers=headers,
            params=params,
            response=data,
            start_time=start,
            error=error
        )

        return response

    def log_request(self, method, url, payload, headers, params, response, start_time, error=None, retries=0):
        duration = time.time() - start_time
        status_code = getattr(response, "status_code", None)

        try:
            log = HTTPLog(
                method=method,
                url=url,
                query_params=self._safe_serialize(params),
                payload=self._safe_serialize(payload),
                headers=self._safe_serialize(headers),
                response=self._safe_serialize(response),
                status_code=status_code or 500,
                error={"message": error} if error else None,
                duration_seconds=round(duration, 3),
                retries=retries,
                service_name=self.__class__.__name__
            )

            log.save()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception('Failed to save HTTP log to DB.')

    def _safe_serialize(self, value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: self._safe_serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._safe_serialize(v) for v in value]
        return value