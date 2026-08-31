import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { readJson, sendJson, withServer } from "./helpers.js";

const packageDirectory = fileURLToPath(new URL("../", import.meta.url));
const cliPath = fileURLToPath(new URL("../bin/gkmex.js", import.meta.url));
const usage = `Usage:
  gkmex list [--brand <brand>] [--type <mobile|crawler>] [--limit <1-100>] [--offset <n>] [--cursor <token>]
  gkmex get <public-id>
  gkmex compare <public-id> <public-id> [public-id ...]
  gkmex --help
  gkmex --version
`;

function runCli(
  args,
  { baseUrl, closeStdout = false, env = {}, timeoutMs = 5000 } = {},
) {
  return new Promise((resolve, reject) => {
    const childEnv = { ...process.env, ...env };
    if (baseUrl === undefined && !Object.hasOwn(env, "GKMEX_BASE_URL")) {
      delete childEnv.GKMEX_BASE_URL;
    } else if (baseUrl !== undefined) {
      childEnv.GKMEX_BASE_URL = baseUrl;
    }

    const child = spawn(process.execPath, [cliPath, ...args], {
      cwd: packageDirectory,
      env: childEnv,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    let timedOut = false;
    let timeout;
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");

    const onStdout = (chunk) => {
      stdout += chunk;
    };
    const onStderr = (chunk) => {
      stderr += chunk;
    };
    const cleanup = () => {
      clearTimeout(timeout);
      child.removeListener("error", onError);
      child.removeListener("close", onClose);
      child.stdout.removeListener("data", onStdout);
      child.stderr.removeListener("data", onStderr);
    };
    const settle = (callback, value) => {
      if (settled) return;
      settled = true;
      cleanup();
      callback(value);
    };
    const timeoutError = () => new Error(
      "Gkmex CLI timed out after " + timeoutMs + " ms",
    );
    function onError(error) {
      settle(reject, timedOut ? timeoutError() : error);
    }
    function onClose(code, signal) {
      if (timedOut) {
        settle(reject, timeoutError());
      } else {
        settle(resolve, { code, signal, stdout, stderr });
      }
    }

    child.stdout.on("data", onStdout);
    child.stderr.on("data", onStderr);
    child.once("error", onError);
    child.once("close", onClose);
    timeout = setTimeout(() => {
      if (settled) return;
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);
    if (closeStdout) child.stdout.destroy();
  });
}

function assertSuccess(actual, expected) {
  assert.equal(actual.code, 0);
  assert.equal(actual.signal, null);
  assert.equal(actual.stderr, "");
  assert.equal(actual.stdout, JSON.stringify(expected, null, 2) + "\n");
}

test("list forwards filters in any flag order and prints deterministic JSON", async () => {
  const expected = {
    updated_at: "2026-08-31",
    count: 1,
    total: 1,
    limit: 2,
    offset: 1,
    next_cursor: null,
    data: [
      {
        id: "crane-1",
        brand: "Liebherr & Co",
        type: "mobile",
        price_eur: null,
        url: "https://gkmex.com/en/crane/crane-1",
      },
    ],
  };

  await withServer((request, response) => {
    assert.equal(request.method, "GET");
    assert.equal(request.headers.accept, "application/json");
    assert.equal(
      request.url,
      "/api/v1/cranes?limit=2&offset=1&cursor=next%2Fpage&brand=Liebherr+%26+Co&type=mobile",
    );
    sendJson(response, 200, expected);
  }, async (baseUrl) => {
    const result = await runCli(
      [
        "list",
        "--type",
        "mobile",
        "--brand",
        "Liebherr & Co",
        "--cursor",
        "next/page",
        "--offset",
        "1",
        "--limit",
        "2",
      ],
      { baseUrl },
    );

    assertSuccess(result, expected);
    assert.match(result.stdout, /"price_eur": null/);
  });
});

test("get prints the public crane JSON returned by the SDK", async () => {
  const expected = {
    id: "id/with space",
    brand: "Demag",
    model: "CC 2800",
    price_eur: null,
    url: "https://gkmex.com/en/crane/id%2Fwith%20space",
  };

  await withServer((request, response) => {
    assert.equal(request.method, "GET");
    assert.equal(request.url, "/api/v1/cranes/id%2Fwith%20space");
    sendJson(response, 200, expected);
  }, async (baseUrl) => {
    assertSuccess(await runCli(["get", "id/with space"], { baseUrl }), expected);
  });
});

test("compare selects requested cranes from MCP inventory and prints JSON", async () => {
  const inventory = {
    updated_at: "2026-08-31",
    count: 3,
    data: [
      {
        id: "crane-extra",
        price_eur: 99000,
        url: "https://gkmex.com/en/crane/crane-extra",
      },
      {
        id: "crane-1",
        price_eur: 175000,
        url: "https://gkmex.com/en/crane/crane-1",
      },
      {
        id: "crane-2",
        price_eur: null,
        url: "https://gkmex.com/en/crane/crane-2",
      },
    ],
  };
  const expected = {
    updated_at: inventory.updated_at,
    count: 2,
    data: [inventory.data[2], inventory.data[1]],
  };

  await withServer(async (request, response) => {
    assert.equal(request.method, "POST");
    assert.equal(request.url, "/mcp");
    assert.equal(request.headers["content-type"], "application/json");
    assert.equal(
      request.headers.accept,
      "application/json, text/event-stream",
    );
    assert.deepEqual(await readJson(request), {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "list_cranes",
        arguments: {},
      },
    });
    sendJson(response, 200, {
      jsonrpc: "2.0",
      id: 1,
      result: { structuredContent: inventory },
    });
  }, async (baseUrl) => {
    assertSuccess(
      await runCli(["compare", "crane-2", "crane-1"], { baseUrl }),
      expected,
    );
  });
});

test("top-level help and version succeed without constructing a network client", async (t) => {
  const env = { GKMEX_BASE_URL: "not a valid URL" };

  await t.test("help", async () => {
    const result = await runCli(["--help"], { env });
    assert.deepEqual(result, {
      code: 0,
      signal: null,
      stdout: usage,
      stderr: "",
    });
  });

  await t.test("version comes from package.json", async () => {
    const result = await runCli(["--version"], { env });
    assert.deepEqual(result, {
      code: 0,
      signal: null,
      stdout: "1.0.0\n",
      stderr: "",
    });
  });
});

test("invalid usage is rejected before any SDK request", async (t) => {
  const cases = [
    ["no command", []],
    ["unknown command", ["search"]],
    ["help with extra args", ["--help", "extra"]],
    ["version with extra args", ["--version", "extra"]],
    ["list command-local help", ["list", "--help"]],
    ["list unknown flag", ["list", "--unknown", "x"]],
    ["list missing flag value", ["list", "--brand"]],
    ["list flag used as value", ["list", "--brand", "--type", "mobile"]],
    ["list duplicate flag", ["list", "--brand", "A", "--brand", "B"]],
    ["list positional junk", ["list", "junk", "value"]],
    ["list odd option count", ["list", "--brand", "A", "--limit"]],
    ["limit zero", ["list", "--limit", "0"]],
    ["limit over 100", ["list", "--limit", "101"]],
    ["limit sign", ["list", "--limit", "+1"]],
    ["limit decimal", ["list", "--limit", "1.5"]],
    ["limit unsafe integer", ["list", "--limit", "9007199254740992"]],
    ["limit empty", ["list", "--limit", ""]],
    ["offset negative", ["list", "--offset", "-1"]],
    ["offset sign", ["list", "--offset", "+1"]],
    ["offset decimal", ["list", "--offset", "1.5"]],
    ["offset unsafe integer", ["list", "--offset", "9007199254740992"]],
    ["offset empty", ["list", "--offset", ""]],
    ["invalid type", ["list", "--type", "tower"]],
    ["empty brand", ["list", "--brand", ""]],
    ["leading brand whitespace", ["list", "--brand", " Liebherr"]],
    ["trailing brand whitespace", ["list", "--brand", "Liebherr "]],
    ["empty cursor", ["list", "--cursor", ""]],
    ["leading cursor whitespace", ["list", "--cursor", " next"]],
    ["trailing cursor whitespace", ["list", "--cursor", "next "]],
    ["get missing ID", ["get"]],
    ["get extra ID", ["get", "crane-1", "crane-2"]],
    ["get command-local help", ["get", "--help"]],
    ["get empty ID", ["get", ""]],
    ["get leading whitespace", ["get", " crane-1"]],
    ["get trailing whitespace", ["get", "crane-1 "]],
    ["get dot segment", ["get", "."]],
    ["get parent segment", ["get", ".."]],
    ["compare fewer than two", ["compare", "crane-1"]],
    [
      "compare more than five",
      ["compare", "a", "b", "c", "d", "e", "f"],
    ],
    ["compare duplicates", ["compare", "crane-1", "crane-1"]],
    ["compare command-local help", ["compare", "--help", "crane-1"]],
    ["compare empty ID", ["compare", "crane-1", ""]],
    ["compare leading whitespace", ["compare", "crane-1", " crane-2"]],
    ["compare trailing whitespace", ["compare", "crane-1", "crane-2 "]],
    ["compare dot segment", ["compare", "crane-1", "."]],
    ["compare parent segment", ["compare", "crane-1", ".."]],
  ];
  let serverHits = 0;

  await withServer((_request, response) => {
    serverHits += 1;
    sendJson(response, 500, { error: "invalid input reached the server" });
  }, async (baseUrl) => {
    for (const [name, args] of cases) {
      await t.test(name, async () => {
        const result = await runCli(args, { baseUrl });
        assert.equal(result.code, 2);
        assert.equal(result.signal, null);
        assert.equal(result.stdout, "");
        const separator = result.stderr.indexOf("\n\n");
        assert.ok(separator > 0, "stderr must start with a concise reason");
        assert.equal(result.stderr.slice(separator + 2), usage);
        assert.doesNotMatch(result.stderr, /\b(?:Error|at)\b|\.js:\d+/);
      });
    }
  });

  assert.equal(serverHits, 0);
});

test("list usage validation happens before client construction", async () => {
  const result = await runCli(["list", "--limit", "0"], {
    env: { GKMEX_BASE_URL: "not a valid URL" },
  });
  assert.equal(result.code, 2);
  assert.equal(result.stdout, "");
  assert.equal(result.stderr.slice(result.stderr.indexOf("\n\n") + 2), usage);
});

test("API failures print only the stable SDK message", async () => {
  await withServer((_request, response) => {
    sendJson(response, 503, { error: "Crane service unavailable" });
  }, async (baseUrl) => {
    const result = await runCli(["get", "crane-1"], { baseUrl });
    assert.deepEqual(result, {
      code: 1,
      signal: null,
      stdout: "",
      stderr: "Crane service unavailable\n",
    });
  });
});

test("network failures print only the stable SDK message", async () => {
  const result = await runCli(["get", "crane-1"], {
    baseUrl: "http://127.0.0.1:1",
  });
  assert.deepEqual(result, {
    code: 1,
    signal: null,
    stdout: "",
    stderr: "Unable to reach Gkmex\n",
  });
});

test("unexpected failures do not leak stacks or internal messages", async () => {
  const result = await runCli(["get", "crane-1"], {
    baseUrl: "not a valid URL",
  });
  assert.deepEqual(result, {
    code: 1,
    signal: null,
    stdout: "",
    stderr: "Unexpected Gkmex CLI failure\n",
  });
});

test("a closed stdout pipeline exits quietly", async () => {
  const largeResult = {
    data: Array.from({ length: 4096 }, (_, index) => ({
      id: "crane-" + index,
      description: "x".repeat(512),
      price_eur: null,
    })),
  };

  await withServer((_request, response) => {
    sendJson(response, 200, largeResult);
  }, async (baseUrl) => {
    const result = await runCli(["list"], { baseUrl, closeStdout: true });
    assert.deepEqual(result, {
      code: 0,
      signal: null,
      stdout: "",
      stderr: "",
    });
  });
});

test("runCli times out and kills a stuck child process", async () => {
  let connectionClosed = false;

  await withServer((_request, response) => new Promise((resolve) => {
    const fallback = setTimeout(() => {
      response.destroy();
      resolve();
    }, 1200);
    response.once("close", () => {
      clearTimeout(fallback);
      connectionClosed = true;
      resolve();
    });
  }), async (baseUrl) => {
    await assert.rejects(
      runCli(["list"], { baseUrl, timeoutMs: 250 }),
      (error) => {
        assert.equal(error.message, "Gkmex CLI timed out after 250 ms");
        return true;
      },
    );
  });

  assert.equal(connectionClosed, true);
});
