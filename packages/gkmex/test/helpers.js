import { createServer } from "node:http";
import { once } from "node:events";

export function sendJson(response, status, value) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(value));
}

export async function readJson(request) {
  let body = "";
  request.setEncoding("utf8");
  for await (const chunk of request) body += chunk;
  return JSON.parse(body);
}

export async function withServer(handler, run) {
  const server = createServer(handler);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  const baseUrl = "http://127.0.0.1:" + address.port;
  try {
    return await run(baseUrl);
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }
}
