#!/usr/bin/env node

import { readFile } from "node:fs/promises";

import { GkmexClient, GkmexError } from "../src/index.js";

const usage = `Usage:
  gkmex list [--brand <brand>] [--type <mobile|crawler>] [--limit <1-100>] [--offset <n>] [--cursor <token>]
  gkmex get <public-id>
  gkmex compare <public-id> <public-id> [public-id ...]
  gkmex --help
  gkmex --version
`;

class UsageError extends Error {}

function failUsage(message) {
  throw new UsageError(message);
}

function isCanonicalToken(value) {
  return value.length > 0 && value === value.trim();
}

function isCanonicalPublicId(value) {
  return isCanonicalToken(value) && value !== "." && value !== "..";
}

function decimalInteger(value, label) {
  if (!/^\d+$/.test(value)) failUsage(label + " must be a decimal integer");
  const number = Number(value);
  if (!Number.isSafeInteger(number)) failUsage(label + " must be a safe integer");
  return number;
}

function parseListOptions(args) {
  const names = new Map([
    ["--brand", "brand"],
    ["--type", "type"],
    ["--limit", "limit"],
    ["--offset", "offset"],
    ["--cursor", "cursor"],
  ]);
  const seen = new Set();
  const options = {};

  for (let index = 0; index < args.length; index += 2) {
    const flag = args[index];
    const key = names.get(flag);
    if (key === undefined) failUsage("Unknown list option: " + flag);
    if (seen.has(flag)) failUsage("Duplicate list option: " + flag);
    seen.add(flag);

    const value = args[index + 1];
    if (value === undefined || value.startsWith("--")) {
      failUsage("Missing value for " + flag);
    }

    if (key === "limit") {
      const number = decimalInteger(value, "limit");
      if (number < 1 || number > 100) failUsage("limit must be between 1 and 100");
      options.limit = number;
    } else if (key === "offset") {
      options.offset = decimalInteger(value, "offset");
    } else if (key === "type") {
      if (value !== "mobile" && value !== "crawler") {
        failUsage("type must be mobile or crawler");
      }
      options.type = value;
    } else {
      if (!isCanonicalToken(value)) {
        failUsage(key + " must be a non-empty canonical token");
      }
      options[key] = value;
    }
  }

  return options;
}

function client() {
  return new GkmexClient(
    process.env.GKMEX_BASE_URL === undefined
      ? {}
      : { baseUrl: process.env.GKMEX_BASE_URL },
  );
}

async function execute(args) {
  if (args.length === 1 && args[0] === "--help") {
    process.stdout.write(usage);
    return;
  }
  if (args.length === 1 && args[0] === "--version") {
    const packageJson = JSON.parse(
      await readFile(new URL("../package.json", import.meta.url), "utf8"),
    );
    process.stdout.write(packageJson.version + "\n");
    return;
  }

  const [command, ...commandArgs] = args;
  if (command === undefined) failUsage("A command is required");

  let result;
  if (command === "list") {
    const options = parseListOptions(commandArgs);
    result = await client().listCranes(options);
  } else if (command === "get") {
    if (commandArgs.some((value) => value.startsWith("--"))) {
      failUsage("Unknown get option: " + commandArgs.find((value) => value.startsWith("--")));
    }
    if (commandArgs.length !== 1) failUsage("get requires exactly one public ID");
    if (!isCanonicalPublicId(commandArgs[0])) {
      failUsage("get requires a canonical public ID");
    }
    result = await client().getCrane(commandArgs[0]);
  } else if (command === "compare") {
    const option = commandArgs.find((value) => value.startsWith("--"));
    if (option !== undefined) failUsage("Unknown compare option: " + option);
    if (commandArgs.length < 2 || commandArgs.length > 5) {
      failUsage("compare requires two to five public IDs");
    }
    if (
      commandArgs.some((value) => !isCanonicalPublicId(value)) ||
      new Set(commandArgs).size !== commandArgs.length
    ) {
      failUsage("compare requires unique canonical public IDs");
    }
    result = await client().compareCranes(commandArgs);
  } else {
    failUsage("Unknown command: " + command);
  }

  process.stdout.write(JSON.stringify(result, null, 2) + "\n");
}

try {
  await execute(process.argv.slice(2));
} catch (error) {
  if (error instanceof UsageError) {
    process.stderr.write(error.message + "\n\n" + usage);
    process.exitCode = 2;
  } else if (error instanceof GkmexError) {
    process.stderr.write(error.message + "\n");
    process.exitCode = 1;
  } else {
    process.stderr.write("Unexpected Gkmex CLI failure\n");
    process.exitCode = 1;
  }
}
