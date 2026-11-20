import type {
  Incident,
  IncidentInput,
  IncidentUpdate,
  Snapshot,
} from '../types';
import { isHealth, isIncident, isMetric, isPage, isServer } from './contracts';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Use same-origin /api requests, proxied to FastAPI by Vite in development.
 * The caller keeps the token in React memory; no browser storage or VITE_* secret
 * is used. Never attach credentials to health checks or arbitrary remote URLs.
 */
export function createApi(token: string, adminToken = '') {
  async function request<T>(
    path: string,
    options: RequestInit = {},
    publicEndpoint = false,
    credential = token,
  ): Promise<T> {
    if (/\s/.test(credential))
      throw new ApiError(401, 'Use a bearer token without whitespace.');
    const headers = new Headers(options.headers);
    headers.set('Accept', 'application/json');
    if (options.body) headers.set('Content-Type', 'application/json');
    if (!publicEndpoint && credential)
      headers.set('Authorization', `Bearer ${credential}`);

    let response: Response;
    try {
      response = await fetch(`/api/v1${path}`, {
        ...options,
        headers,
        signal: options.signal ?? AbortSignal.timeout(10_000),
        cache: 'no-store',
      });
    } catch {
      throw new ApiError(
        0,
        'Cannot reach the API. Check the connection and try again.',
      );
    }

    if (publicEndpoint && response.status === 503) {
      // Readiness failure is a valid health document, not an empty success.
      const health = await readJson<unknown>(response);
      if (!isHealth(health) || health.status !== 'unhealthy') {
        throw new ApiError(503, 'The API returned an invalid health response.');
      }
      return health as T;
    }
    if (!response.ok) {
      const messages: Record<number, string> = {
        400: 'The request could not be read. Check the input and try again.',
        401: 'Your session is not authorized. Connect with a valid bearer token.',
        403: 'Your account does not have permission for this action.',
        404: 'This API route or record is not available yet.',
        405: 'This route does not support the requested HTTP method.',
        415: 'This endpoint requires a JSON request body.',
        500: 'An internal server failure interrupted request processing.',
        409: 'This record conflicts with an existing record. Refresh and try again.',
        422: 'Some fields are invalid. Check your input and try again.',
        503: 'The server is temporarily unavailable. Try again shortly.',
      };
      // A proxy may send HTML. Only use public messages from an API error envelope.
      const reason = await publicErrorMessage(response);
      throw new ApiError(
        response.status,
        reason ??
          messages[response.status] ??
          'The request failed. Please try again.',
      );
    }
    if (response.status === 204) return undefined as T;
    return readJson<T>(response);
  }

  return {
    async snapshot(): Promise<Snapshot> {
      const server = await request<unknown>('/server');
      if (!isServer(server)) {
        throw new ApiError(
          502,
          'The API returned data that does not match the expected contract.',
        );
      }
      // Select the same configured server instead of assuming its ID is 1.
      const [health, metrics, incidents] = await Promise.all([
        request<unknown>(`/health?server_id=${server.id}`, {}, true),
        request<unknown>('/metrics?limit=100'),
        request<unknown>('/incidents?limit=100').catch(() => null),
      ]);
      if (
        !isHealth(health) ||
        health.server_id !== server.id ||
        !isPage(metrics, isMetric)
      ) {
        throw new ApiError(
          502,
          'The API returned data that does not match the expected contract.',
        );
      }
      const incidentPage = isPage(incidents, isIncident) ? incidents : null;
      let history = metrics.items;
      const oldest = history.at(-1);
      if (oldest && metrics.total > history.length && history.length === 100) {
        // Anchor the next page to the last timestamp so fresh inserts cannot shift it.
        const end = encodeURIComponent(oldest.collected_at);
        const older = await request<unknown>(
          `/metrics?limit=100&offset=1&end=${end}`,
        ).catch(() => null);
        if (isPage(older, isMetric)) history = [...history, ...older.items];
      }
      return {
        health,
        server,
        metrics: history,
        incidents: incidentPage?.items ?? null,
        incidentTotal: incidentPage?.total ?? null,
      };
    },
    createIncident: (input: IncidentInput) =>
      incidentResponse(
        request<unknown>(
          '/incidents',
          {
            method: 'POST',
            body: JSON.stringify(input),
          },
          false,
          adminToken,
        ),
      ),
    updateIncident: (id: string, input: IncidentUpdate) =>
      incidentResponse(
        request<unknown>(
          `/incidents/${encodeURIComponent(id)}`,
          {
            method: 'PATCH',
            body: JSON.stringify(input),
          },
          false,
          adminToken,
        ),
      ),
    deleteIncident: (id: string) =>
      request<void>(
        `/incidents/${encodeURIComponent(id)}`,
        {
          method: 'DELETE',
        },
        false,
        adminToken,
      ),
  };
}

async function publicErrorMessage(
  response: Response,
): Promise<string | undefined> {
  if (
    response.status < 400 ||
    (response.status >= 500 && ![500, 503].includes(response.status)) ||
    response.headers.get('content-type')?.split(';')[0].trim() !==
      'application/json'
  )
    return;
  const payload = await response.json().catch(() => undefined);
  const error = payload?.error;
  if (
    typeof error?.code !== 'string' ||
    (response.status === 500 && error.code !== 'internal_error') ||
    (response.status === 503 && error.code !== 'service_unavailable') ||
    typeof error.message !== 'string' ||
    !Array.isArray(error.details)
  )
    return;
  const reasons: string[] = [];
  for (const detail of error.details) {
    if (typeof detail?.field !== 'string' || typeof detail.message !== 'string')
      return;
    reasons.push(`${detail.field}: ${detail.message}`);
  }
  return [error.message, ...reasons].join(' ');
}

async function incidentResponse(pending: Promise<unknown>): Promise<Incident> {
  const value = await pending;
  if (!isIncident(value))
    throw new ApiError(502, 'The API returned an invalid incident record.');
  return value;
}

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      response.status,
      'The API returned an unreadable response.',
    );
  }
}
