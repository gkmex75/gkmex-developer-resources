const DEFAULT_BASE_URL = "https://gkmex.com";

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

export class GkmexClient {
  constructor(options = {}) {
    this.baseUrl = normalizedBaseUrl(options.baseUrl);
    this.fetch = options.fetch ?? globalThis.fetch;
  }

  async #requestJson(path, init = {}) {
    const url = typeof path === "string" ? new URL(path, this.baseUrl) : path;
    let response;
    try {
      response = await this.fetch(url, init);
    } catch (cause) {
      throw new GkmexError("Unable to reach Gkmex", { cause });
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.toLowerCase().includes("application/json")) {
      throw new GkmexError("Gkmex returned an unexpected response", {
        status: response.status,
      });
    }

    let payload;
    try {
      payload = await response.json();
    } catch (cause) {
      throw new GkmexError("Gkmex returned invalid JSON", {
        status: response.status,
        cause,
      });
    }

    if (!response.ok) {
      throw new GkmexError(
        typeof payload?.error === "string"
          ? payload.error
          : "Gkmex request failed with HTTP " + response.status,
        { status: response.status, details: payload },
      );
    }
    return payload;
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
    if (typeof id !== "string" || id.trim().length === 0) {
      throw new GkmexError("id must be a non-empty public crane ID");
    }
    return this.#requestJson(
      "api/v1/cranes/" + encodeURIComponent(String(id)),
      { headers: { accept: "application/json" } },
    );
  }

  async compareCranes(ids) {
    if (
      !Array.isArray(ids) ||
      ids.length < 2 ||
      ids.length > 5 ||
      ids.some((id) => typeof id !== "string" || id.trim().length === 0) ||
      new Set(ids).size !== ids.length
    ) {
      throw new GkmexError(
        "ids must contain two to five unique public crane IDs",
      );
    }

    const payload = await this.#requestJson("mcp", {
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

    if (payload?.error) {
      throw new GkmexError(
        payload.error.message ?? "Gkmex MCP request failed",
        { code: payload.error.code, details: payload.error.data },
      );
    }
    const comparison = payload?.result?.structuredContent;
    if (
      comparison === null ||
      typeof comparison !== "object" ||
      Array.isArray(comparison)
    ) {
      throw new GkmexError("Gkmex returned an unexpected MCP result");
    }
    return comparison;
  }
}
