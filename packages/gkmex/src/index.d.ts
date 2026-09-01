export type CraneType = "mobile" | "crawler";

export interface Crane {
  id: string;
  brand: string;
  model: string;
  year?: number | null;
  capacity?: string;
  type?: CraneType;
  location?: string;
  price_eur: number | null;
  image?: string;
  url: string;
  [key: string]: unknown;
}

export interface InventoryResponse {
  updated_at: string;
  count: number;
  total?: number;
  limit?: number;
  offset?: number;
  next_cursor?: string | null;
  data: Crane[];
}

export interface ComparisonResponse {
  updated_at: string;
  count: number;
  data: Crane[];
}

export interface ListCranesOptions {
  limit?: number;
  offset?: number;
  cursor?: string;
  brand?: string;
  type?: CraneType;
}

export interface GkmexClientOptions {
  baseUrl?: string;
  fetch?: typeof globalThis.fetch;
}

export interface GkmexErrorOptions {
  status?: number;
  code?: number;
  details?: unknown;
  cause?: unknown;
}

export class GkmexError extends Error {
  status?: number;
  code?: number;
  details?: unknown;
  constructor(message: string, options?: GkmexErrorOptions);
}

export class GkmexClient {
  constructor(options?: GkmexClientOptions);
  listCranes(options?: ListCranesOptions): Promise<InventoryResponse>;
  getCrane(id: string): Promise<Crane>;
  compareCranes(ids: string[]): Promise<ComparisonResponse>;
}
