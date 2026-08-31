const DEFAULT_BASE_URL = "https://gkmex.com";

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

  async listCranes(options = {}) {
    const url = new URL("/api/v1/cranes", this.baseUrl);
    for (const key of ["limit", "offset", "cursor", "brand", "type"]) {
      if (options[key] !== undefined) {
        url.searchParams.set(key, String(options[key]));
      }
    }
    const response = await this.fetch(url, {
      headers: { accept: "application/json" },
    });
    return response.json();
  }

  async getCrane(id) {
    const url = new URL(
      "/api/v1/cranes/" + encodeURIComponent(String(id)),
      this.baseUrl,
    );
    const response = await this.fetch(url, {
      headers: { accept: "application/json" },
    });
    return response.json();
  }
}
