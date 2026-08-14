export default async (request, context) => {
  const railwayBase = (process.env.RAILWAY_API_URL || "").replace(/\/+$/, "");

  if (!railwayBase) {
    return new Response(
      JSON.stringify({
        error: "RAILWAY_API_URL belum diatur di Netlify Environment Variables."
      }),
      {
        status: 500,
        headers: { "content-type": "application/json; charset=utf-8" }
      }
    );
  }

  const incoming = new URL(request.url);
  const apiPath = incoming.pathname.replace(/^\/api/, "");
  const target = new URL(`${railwayBase}/api${apiPath}${incoming.search}`);

  const headers = new Headers(request.headers);
  headers.delete("host");

  const init = {
    method: request.method,
    headers,
    redirect: "follow"
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  try {
    const upstream = await fetch(target, init);
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders
    });
  } catch (error) {
    return new Response(
      JSON.stringify({
        error: "Gagal terhubung ke backend Railway.",
        detail: String(error?.message || error)
      }),
      {
        status: 502,
        headers: { "content-type": "application/json; charset=utf-8" }
      }
    );
  }
};
