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
export function createApi(token: string) {
  async function request<T>(
    path: string,
    options: RequestInit = {},
    publicEndpoint = false,
  ): Promise<T> {
    if (/\s/.test(token))
      throw new ApiError(401, 'Use a bearer token without whitespace.');
    const headers = new Headers(options.headers);
    headers.set('Accept', 'application/json');
    if (options.body) headers.set('Content-Type', 'application/json');
    if (!publicEndpoint && token)
      headers.set('Authorization', `Bearer ${token}`);

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
        409: 'This record conflicts with an existing record. Refresh and try again.',
        422: 'Some fields are invalid. Check your input and try again.',
        503: 'The server is temporarily unavailable. Try again shortly.',
      };
      // Do not display raw server text, HTML, credentials, or internal errors.
      throw new ApiError(
        response.status,
        messages[response.status] ?? 'The request failed. Please try again.',
      );
    }
    if (response.status === 204) return undefined as T;
    return readJson<T>(response);
  }

  return {
    async snapshot(): Promise<Snapshot> {
      const [health, server, metrics, incidents] = await Promise.all([
        request<unknown>('/health?server_id=1', {}, true),
        request<unknown>('/server'),
        request<unknown>('/metrics?limit=100'),
        request<unknown>('/incidents?limit=100'),
      ]);
      if (
        !isHealth(health) ||
        !isServer(server) ||
        !isPage(metrics, isMetric) ||
        !isPage(incidents, isIncident)
      ) {
        throw new ApiError(
          502,
          'The API returned data that does not match the expected contract.',
        );
      }
      return {
        health,
        server,
        metrics: metrics.items,
        incidents: incidents.items,
        incidentTotal: incidents.total,
      };
    },
    createIncident: (input: IncidentInput) =>
      incidentResponse(
        request<unknown>('/incidents', {
          method: 'POST',
          body: JSON.stringify(input),
        }),
      ),
    updateIncident: (id: string, input: IncidentUpdate) =>
      incidentResponse(
        request<unknown>(`/incidents/${encodeURIComponent(id)}`, {
          method: 'PATCH',
          body: JSON.stringify(input),
        }),
      ),
    deleteIncident: (id: string) =>
      request<void>(`/incidents/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      }),
  };
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
