exports.handler = async function(event) {
  const railwayBase = (process.env.RAILWAY_API_URL || "").replace(/\/+$/, "");

  if (!railwayBase) {
    return {
      statusCode: 500,
      headers: { "content-type": "application/json; charset=utf-8" },
      body: JSON.stringify({
        error: "RAILWAY_API_URL belum diatur di Netlify Environment Variables."
      })
    };
  }

  const path = (event.queryStringParameters?.path || "").replace(/^\/+/, "");

  const originalQuery = { ...(event.queryStringParameters || {}) };
  delete originalQuery.path;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(originalQuery)) {
    if (value !== undefined && value !== null) {
      params.append(key, value);
    }
  }

  const query = params.toString();
  const target = `${railwayBase}/api/${path}${query ? `?${query}` : ""}`;

  const headers = { ...(event.headers || {}) };
  delete headers.host;
  delete headers.Host;

  const init = {
    method: event.httpMethod,
    headers,
    redirect: "follow"
  };

  if (!["GET", "HEAD"].includes(event.httpMethod) && event.body) {
    init.body = event.isBase64Encoded
      ? Buffer.from(event.body, "base64")
      : event.body;
  }

  try {
    const upstream = await fetch(target, init);
    const body = await upstream.text();

    const responseHeaders = {};
    upstream.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      if (!["content-encoding", "content-length", "transfer-encoding"].includes(lower)) {
        responseHeaders[key] = value;
      }
    });

    return {
      statusCode: upstream.status,
      headers: responseHeaders,
      body
    };
  } catch (error) {
    return {
      statusCode: 502,
      headers: { "content-type": "application/json; charset=utf-8" },
      body: JSON.stringify({
        error: "Gagal terhubung ke backend Railway.",
        detail: String(error?.message || error),
        target
      })
    };
  }
};
