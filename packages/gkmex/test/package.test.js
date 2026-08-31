import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { readFile, stat } from "node:fs/promises";
import test from "node:test";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);
const packageDirectory = fileURLToPath(new URL("../", import.meta.url));

const expectedMetadata = {
  name: "gkmex",
  version: "1.0.0",
  description:
    "Zero-auth JavaScript SDK and CLI for the public Gkmex used-crane inventory.",
  type: "module",
  main: "./src/index.js",
  types: "./src/index.d.ts",
  exports: {
    ".": {
      types: "./src/index.d.ts",
      import: "./src/index.js",
    },
  },
  bin: { gkmex: "./bin/gkmex.js" },
  files: ["bin", "src", "README.md", "LICENSE"],
  scripts: {
    test: "node --test test/client.test.js test/cli.test.js test/package.test.js",
  },
  engines: { node: ">=20" },
  repository: {
    type: "git",
    url: "git+https://github.com/gkmex75/gkmex-developer-resources.git",
    directory: "packages/gkmex",
  },
  homepage: "https://gkmex.com/developers",
  bugs: {
    url: "https://github.com/gkmex75/gkmex-developer-resources/issues",
  },
  keywords: ["gkmex", "cranes", "sdk", "cli", "mcp", "inventory"],
  license: "MIT",
  publishConfig: { access: "public" },
};

const expectedDeclarations = `export type CraneType = "mobile" | "crawler";

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
`;

test("package metadata is the exact public SDK and CLI contract", async () => {
  const metadata = JSON.parse(
    await readFile(new URL("../package.json", import.meta.url), "utf8"),
  );

  assert.deepEqual(metadata, expectedMetadata);
  assert.equal(Object.hasOwn(metadata, "private"), false);
  assert.equal(Object.hasOwn(metadata, "dependencies"), false);
  assert.equal(Object.hasOwn(metadata, "devDependencies"), false);
});

test("TypeScript declarations match every exported runtime API", async () => {
  const declarations = await readFile(
    new URL("../src/index.d.ts", import.meta.url),
    "utf8",
  );

  assert.equal(declarations, expectedDeclarations);
});

test("README documents SDK, CLI, and the public-data boundaries", async () => {
  const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");
  const requiredPatterns = [
    /Node\.js 20 or newer/,
    /npm install gkmex/,
    /import \{ GkmexClient \} from "gkmex"/,
    /client\.listCranes/,
    /client\.getCrane/,
    /client\.compareCranes/,
    /npx gkmex list/,
    /npx gkmex get/,
    /npx gkmex compare/,
    /Every successful command prints JSON/,
    /Invalid usage exits 2/,
    /API or network errors exit 1/,
    /requires no account, sign-up, token, or API key/,
    /Every operation is read-only/,
    /null `price_eur` means POA, never zero/,
    /availability signal, not a reservation or final availability confirmation/,
    /public `url`/,
    /specifications, price, inspection, transport, and final availability/,
    /https:\/\/gkmex\.com\/developers/,
    /https:\/\/gkmex\.com\/openapi\.json/,
    /https:\/\/github\.com\/gkmex75\/gkmex-developer-resources/,
    /## License\n\nMIT/,
  ];

  for (const pattern of requiredPatterns) assert.match(readme, pattern);
  assert.doesNotMatch(readme, /published (?:on|to) npm/i);
});

test("package license exactly matches the repository MIT license", async () => {
  const [packageLicense, repositoryLicense] = await Promise.all([
    readFile(new URL("../LICENSE", import.meta.url), "utf8"),
    readFile(new URL("../../../LICENSE", import.meta.url), "utf8"),
  ]);

  assert.equal(packageLicense, repositoryLicense);
});

test("CLI source is executable", async () => {
  const executable = await stat(new URL("../bin/gkmex.js", import.meta.url));
  assert.equal(executable.mode & 0o777, 0o755);
});

test("npm pack contains only the seven public package files", async () => {
  const { stdout } = await execFileAsync(
    "npm",
    ["pack", "--dry-run", "--json"],
    { cwd: packageDirectory },
  );
  const result = JSON.parse(stdout);
  assert.equal(result.length, 1);

  const [packed] = result;
  assert.equal(packed.name, "gkmex");
  assert.equal(packed.version, "1.0.0");
  assert.equal(packed.entryCount, 7);
  assert.deepEqual(
    packed.files.map((file) => file.path).sort(),
    [
      "LICENSE",
      "README.md",
      "bin/gkmex.js",
      "package.json",
      "src/client.js",
      "src/index.d.ts",
      "src/index.js",
    ],
  );

  const cliEntry = packed.files.find((file) => file.path === "bin/gkmex.js");
  assert.ok(cliEntry);
  if (Object.hasOwn(cliEntry, "mode")) {
    assert.notEqual(cliEntry.mode & 0o111, 0);
  }
});
