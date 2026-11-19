import { describe, expect, it, vi } from 'vitest';
import { createApi } from '../src/services/api';
import { createDemoSnapshot } from '../src/services/demo';

describe('typed API client', () => {
  it('uses contract paths and authenticates all requests except public health', async () => {
    const demo = createDemoSnapshot();
    const fetch = vi.fn().mockImplementation(async (path: string) => {
      const value = path.endsWith('/health?server_id=1')
        ? demo.health
        : path.endsWith('/server')
          ? demo.server
          : path.includes('/metrics')
            ? { items: demo.metrics, total: 96, limit: 100, offset: 0 }
            : { items: demo.incidents, total: 3, limit: 100, offset: 0 };
      return Response.json(value);
    });
    vi.stubGlobal('fetch', fetch);

    const result = await createApi('dummy-test-token').snapshot();

    expect(result.server.hostname).toBe('serverwatch-01');
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/server');
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/health?server_id=1');
    expect(fetch.mock.calls[2][0]).toBe('/api/v1/metrics?limit=100');
    expect(result.metrics).toEqual(demo.metrics);
    expect(result.incidents).toBeNull();
    expect(result.incidentTotal).toBeNull();
    for (const [path, options] of fetch.mock.calls) {
      expect(path).toMatch(/^\/api\/v1\//);
      expect(options.headers.get('Authorization')).toBe(
        path.endsWith('/health?server_id=1') ? null : 'Bearer dummy-test-token',
      );
    }
  });

  it('checks the configured server ID and never calls unimplemented incidents', async () => {
    const demo = createDemoSnapshot();
    const fetch = vi.fn().mockImplementation(async (path: string) => {
      if (path.endsWith('/server'))
        return Response.json({ ...demo.server, id: 7 });
      if (path.endsWith('/health?server_id=7'))
        return Response.json({ ...demo.health, server_id: 7 });
      if (path.endsWith('/metrics?limit=100'))
        return Response.json({ items: [], total: 0, limit: 100, offset: 0 });
      throw new Error('Unexpected route');
    });
    vi.stubGlobal('fetch', fetch);

    const result = await createApi('dummy-test-token').snapshot();

    expect(result.server.id).toBe(7);
    expect(result.metrics).toEqual([]);
    expect(result.incidents).toBeNull();
    expect(fetch.mock.calls.some(([path]) => path.includes('/incidents'))).toBe(
      false,
    );
  });

  it('surfaces a metrics dependency failure instead of manufacturing empty data', async () => {
    const demo = createDemoSnapshot();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (path: string) => {
        if (path.endsWith('/server')) return Response.json(demo.server);
        if (path.includes('/health?')) return Response.json(demo.health);
        return new Response('dummy-sensitive-database-error', { status: 503 });
      }),
    );

    await expect(
      createApi('dummy-test-token').snapshot(),
    ).rejects.toMatchObject({
      status: 503,
      message: 'The server is temporarily unavailable. Try again shortly.',
    });
  });

  it('displays the public storage failure reason on a failed delete', async () => {
    const message = 'PostgreSQL storage has not been configured for this API.';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: { code: 'service_unavailable', message, details: [] },
          },
          { status: 503 },
        ),
      ),
    );
    await expect(createApi('test').deleteIncident('record')).rejects.toThrow(
      message,
    );
  });

  it('displays a sanitized API response-schema failure', async () => {
    const message = 'The server response did not match the endpoint schema.';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: { code: 'internal_error', message, details: [] },
          },
          { status: 500 },
        ),
      ),
    );
    await expect(createApi('test').deleteIncident('record')).rejects.toThrow(
      message,
    );
  });

  it('rejects invalid metric measurements before rendering', async () => {
    const demo = createDemoSnapshot();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (path: string) => {
        if (path.endsWith('/server')) return Response.json(demo.server);
        if (path.includes('/health?')) return Response.json(demo.health);
        return Response.json({
          items: [{ ...demo.metrics[0], cpu_percent: 101 }],
          total: 1,
          limit: 100,
          offset: 0,
        });
      }),
    );

    await expect(createApi('dummy-test-token').snapshot()).rejects.toThrow(
      'expected contract',
    );
  });

  it('rejects a health report for a different server', async () => {
    const demo = createDemoSnapshot();
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation(async (path: string) =>
          Response.json(
            path.endsWith('/server')
              ? demo.server
              : { ...demo.health, server_id: 99 },
          ),
        ),
    );

    await expect(createApi('dummy-test-token').snapshot()).rejects.toThrow(
      'expected contract',
    );
  });

  it('handles an unhealthy 503 response without treating it as healthy', async () => {
    const demo = createDemoSnapshot();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (path: string) => {
        if (path.endsWith('/health?server_id=1'))
          return Response.json(
            {
              ...demo.health,
              status: 'unhealthy',
              checks: { server: 'up', database: 'down' },
            },
            { status: 503 },
          );
        if (path.endsWith('/server')) return Response.json(demo.server);
        return Response.json({ items: [], total: 0, limit: 100, offset: 0 });
      }),
    );

    const result = await createApi('dummy-test-token').snapshot();
    expect(result.health.status).toBe('unhealthy');
    expect(result.health.checks.database).toBe('down');
  });

  it.each([401, 403, 404, 422, 500, 503])(
    'surfaces HTTP %s failures without raw server details',
    async (status) => {
      vi.stubGlobal(
        'fetch',
        vi
          .fn()
          .mockResolvedValue(
            new Response('dummy-sensitive-server-message', { status }),
          ),
      );
      const error = await createApi('dummy-test-token')
        .deleteIncident('record-id')
        .catch((failure: unknown) => failure);

      expect(error).toMatchObject({ status });
      expect((error as Error).message).not.toContain('dummy-sensitive');
    },
  );

  it('shows the reason and field from a structured API validation error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: {
              code: 'validation_error',
              message: 'Request validation failed.',
              details: [
                { field: 'path.incident_id', message: 'Use a valid UUID.' },
              ],
            },
          },
          { status: 422 },
        ),
      ),
    );
    await expect(createApi('test').deleteIncident('bad')).rejects.toThrow(
      'Request validation failed. path.incident_id: Use a valid UUID.',
    );
  });

  it('does not try to parse an empty 204 delete response', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetch);

    await expect(
      createApi('dummy-test-token').deleteIncident('record-id'),
    ).resolves.toBeUndefined();
    expect(fetch.mock.calls[0][1].method).toBe('DELETE');
  });

  it('reports network failures without exposing exception text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('dummy-sensitive-network-error')),
    );
    await expect(
      createApi('dummy-test-token').deleteIncident('record-id'),
    ).rejects.toThrow('Cannot reach the API.');
  });

  it('rejects malformed JSON and invalid response shapes safely', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation(
          async () => new Response('not json', { status: 200 }),
        ),
    );
    await expect(createApi('dummy-test-token').snapshot()).rejects.toThrow(
      'unreadable response',
    );

    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async () => Response.json({})),
    );
    await expect(createApi('dummy-test-token').snapshot()).rejects.toThrow(
      'expected contract',
    );
  });

  it('rejects invalid token formatting without exposing the token', async () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    await expect(
      createApi('dummy\nsensitive-token').deleteIncident('record-id'),
    ).rejects.toThrow('without whitespace');
    expect(fetch).not.toHaveBeenCalled();
  });

  it('uses POST for creation and PATCH for updates', async () => {
    const record = createDemoSnapshot().incidents[0];
    const fetch = vi.fn().mockImplementation(async () => Response.json(record));
    vi.stubGlobal('fetch', fetch);
    const api = createApi('dummy-test-token');
    await api.createIncident({
      title: record.title,
      description: record.description,
      severity: record.severity,
      occurred_at: record.occurred_at,
    });
    await api.updateIncident(record.id, {
      title: record.title,
      description: record.description,
      severity: record.severity,
      status: 'resolved',
    });

    expect(fetch.mock.calls[0][1].method).toBe('POST');
    expect(fetch.mock.calls[1][1].method).toBe('PATCH');
    expect(fetch.mock.calls[0][1].headers.get('Content-Type')).toBe(
      'application/json',
    );
  });
});
