const DEFAULT_BASE_URL = "https://gkmex.com";
const UNEXPECTED_MCP_RESULT = "Gkmex returned an unexpected MCP result";

export class GkmexError extends Error {
  constructor(message, options = {}) {
    super(
      message,
      options.cause === undefined ? undefined : { cause: options.cause },
    );
    this.name = "GkmexError";
    for (const key of ["status", "code", "details"]) {
      if (options[key] !== undefined) this[key] = options[key];
    }
  }
}

function normalizedBaseUrl(value) {
  const url = new URL(value ?? DEFAULT_BASE_URL);
  if (!url.pathname.endsWith("/")) {
    url.pathname += "/";
  }
  return url;
}

function mediaType(response) {
  return (response.headers.get("content-type") ?? "")
    .split(";", 1)[0]
    .trim()
    .toLowerCase();
}

function isJsonMediaType(value) {
  return (
    value === "application/json" ||
    /^application\/[^\s/;]+\+json$/.test(value)
  );
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isCanonicalPublicId(id) {
  return (
    typeof id === "string" &&
    id.length > 0 &&
    id === id.trim() &&
    id !== "." &&
    id !== ".."
  );
}

function httpError(response, payload) {
  return new GkmexError(
    typeof payload?.error === "string"
      ? payload.error
      : "Gkmex request failed with HTTP " + response.status,
    { status: response.status, details: payload },
  );
}

function envelopeKind(payload) {
  if (
    !isObject(payload) ||
    payload.jsonrpc !== "2.0" ||
    payload.id !== 1 ||
    Object.hasOwn(payload, "method")
  ) {
    return undefined;
  }
  const hasResult = Object.hasOwn(payload, "result");
  const hasError = Object.hasOwn(payload, "error");
  if (hasResult === hasError) return undefined;
  return hasError ? "error" : "result";
}

function validRpcError(payload) {
  if (envelopeKind(payload) !== "error" || !isObject(payload.error)) {
    return undefined;
  }
  if (
    !Number.isInteger(payload.error.code) ||
    typeof payload.error.message !== "string"
  ) {
    return undefined;
  }
  return payload.error;
}

function parseSseResponse(body) {
  const events = body.replace(/\r\n?/g, "\n").split(/\n\n+/);
  for (const event of events) {
    const data = [];
    for (const line of event.split("\n")) {
      if (line.startsWith(":")) continue;
      const separator = line.indexOf(":");
      const field = separator === -1 ? line : line.slice(0, separator);
      if (field !== "data") continue;
      let value = separator === -1 ? "" : line.slice(separator + 1);
      if (value.startsWith(" ")) value = value.slice(1);
      data.push(value);
    }
    if (data.length === 0) continue;

    let payload;
    try {
      payload = JSON.parse(data.join("\n"));
    } catch {
      return { malformed: true };
    }
    if (!isObject(payload) || payload.id !== 1) continue;

    const isServerRequest =
      Object.hasOwn(payload, "method") &&
      !Object.hasOwn(payload, "result") &&
      !Object.hasOwn(payload, "error");
    if (!isServerRequest) return { payload };
  }
  return {};
}

function comparisonFrom(payload, status) {
  if (envelopeKind(payload) !== "result" || !isObject(payload.result)) {
    throw new GkmexError(UNEXPECTED_MCP_RESULT);
  }

  if (payload.result.isError === true) {
    const firstText = Array.isArray(payload.result.content)
      ? payload.result.content.find(
          (item) =>
            isObject(item) &&
            item.type === "text" &&
            typeof item.text === "string" &&
            item.text,
        )?.text
      : undefined;
    throw new GkmexError(
      firstText ?? "Gkmex MCP tool returned an error",
      { status },
    );
  }

  const comparison = payload.result.structuredContent;
  if (
    !isObject(comparison) ||
    typeof comparison.updated_at !== "string" ||
    !Number.isInteger(comparison.count) ||
    !Array.isArray(comparison.data) ||
    comparison.count !== comparison.data.length
  ) {
    throw new GkmexError(UNEXPECTED_MCP_RESULT);
  }
  return comparison;
}

export class GkmexClient {
  constructor(options = {}) {
    this.baseUrl = normalizedBaseUrl(options.baseUrl);
    this.fetch = options.fetch ?? globalThis.fetch;
  }

  async #request(path, init = {}) {
    const url = typeof path === "string" ? new URL(path, this.baseUrl) : path;
    try {
      return await this.fetch(url, init);
    } catch (cause) {
      throw new GkmexError("Unable to reach Gkmex", { cause });
    }
  }

  async #decodeJson(response) {
    try {
      return { payload: await response.json() };
    } catch (cause) {
      return { cause };
    }
  }

  async #requestJson(path, init = {}) {
    const response = await this.#request(path, init);
    if (!isJsonMediaType(mediaType(response))) {
      throw new GkmexError("Gkmex returned an unexpected response", {
        status: response.status,
      });
    }

    const decoded = await this.#decodeJson(response);
    if (decoded.cause) {
      throw new GkmexError("Gkmex returned invalid JSON", {
        status: response.status,
        cause: decoded.cause,
      });
    }
    if (!response.ok) throw httpError(response, decoded.payload);
    return decoded.payload;
  }

  async listCranes(options = {}) {
    const url = new URL("api/v1/cranes", this.baseUrl);
    for (const key of ["limit", "offset", "cursor", "brand", "type"]) {
      if (options[key] !== undefined) {
        url.searchParams.set(key, String(options[key]));
      }
    }
    return this.#requestJson(url, {
      headers: { accept: "application/json" },
    });
  }

  async getCrane(id) {
    if (!isCanonicalPublicId(id)) {
      throw new GkmexError("id must be a non-empty public crane ID");
    }
    return this.#requestJson("api/v1/cranes/" + encodeURIComponent(id), {
      headers: { accept: "application/json" },
    });
  }

  async compareCranes(ids) {
    if (
      !Array.isArray(ids) ||
      ids.length < 2 ||
      ids.length > 5 ||
      ids.some((id) => !isCanonicalPublicId(id)) ||
      new Set(ids).size !== ids.length
    ) {
      throw new GkmexError(
        "ids must contain two to five unique public crane IDs",
      );
    }

    const response = await this.#request("mcp", {
      method: "POST",
      headers: {
        accept: "application/json, text/event-stream",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "compare_cranes",
          arguments: { ids },
        },
      }),
    });

    const type = mediaType(response);
    let payload;
    if (isJsonMediaType(type)) {
      const decoded = await this.#decodeJson(response);
      if (decoded.cause) {
        if (!response.ok) throw httpError(response);
        throw new GkmexError("Gkmex returned invalid JSON", {
          status: response.status,
          cause: decoded.cause,
        });
      }
      payload = decoded.payload;
    } else if (type === "text/event-stream") {
      let body;
      try {
        body = await response.text();
      } catch (cause) {
        throw new GkmexError("Unable to reach Gkmex", { cause });
      }
      const decoded = parseSseResponse(body);
      if (decoded.malformed || decoded.payload === undefined) {
        if (!response.ok) throw httpError(response);
        throw new GkmexError(UNEXPECTED_MCP_RESULT);
      }
      payload = decoded.payload;
    } else {
      if (!response.ok) throw httpError(response);
      throw new GkmexError("Gkmex returned an unexpected response", {
        status: response.status,
      });
    }

    const rpcError = validRpcError(payload);
    if (rpcError) {
      throw new GkmexError(rpcError.message, {
        status: response.status,
        code: rpcError.code,
        details: rpcError.data,
      });
    }
    if (!response.ok) throw httpError(response, payload);
    return comparisonFrom(payload, response.status);
  }
}
