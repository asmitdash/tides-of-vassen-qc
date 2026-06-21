import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8787';

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/');
  const url = `${BACKEND_URL}/${path}`;

  try {
    const headers: HeadersInit = {};
    req.headers.forEach((value, key) => {
      if (key !== 'host' && key !== 'connection') {
        headers[key] = value;
      }
    });

    const options: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      const body = await req.text();
      if (body) {
        options.body = body;
      }
    }

    const response = await fetch(url, options);

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/event-stream')) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new NextResponse(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend request failed' },
      { status: 502 }
    );
  }
}

export async function GET(req: NextRequest, context: { params: { path: string[] } }) {
  return handler(req, context);
}

export async function POST(req: NextRequest, context: { params: { path: string[] } }) {
  return handler(req, context);
}

export async function PUT(req: NextRequest, context: { params: { path: string[] } }) {
  return handler(req, context);
}

export async function DELETE(req: NextRequest, context: { params: { path: string[] } }) {
  return handler(req, context);
}
