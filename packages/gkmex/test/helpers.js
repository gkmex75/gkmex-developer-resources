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
  let handlerError;
  const pendingHandlers = new Set();
  const server = createServer((request, response) => {
    const pending = Promise.resolve()
      .then(() => handler(request, response))
      .catch((error) => {
        handlerError ??= error;
        response.destroy();
      })
      .finally(() => pendingHandlers.delete(pending));
    pendingHandlers.add(pending);
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  const baseUrl = "http://127.0.0.1:" + address.port;
  try {
    let result;
    let runError;
    try {
      result = await run(baseUrl);
    } catch (error) {
      runError = error;
    }
    await Promise.all(pendingHandlers);
    if (handlerError) throw handlerError;
    if (runError) throw runError;
    return result;
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
      server.closeAllConnections();
    });
  }
}
