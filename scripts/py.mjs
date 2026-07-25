// Cross-platform Python launcher for the npm scripts.
//
// The repository is verified on Windows, Linux, and macOS. `python` exists on
// Windows and on CI runners provisioned by setup-python, but a stock macOS or
// Linux machine only has `python3`, and on macOS that is often still 3.9. The
// backend uses 3.10 syntax such as `isinstance(value, int | float)`, so an
// unversioned probe picks an interpreter that fails deep inside the call stack
// with a confusing TypeError. This launcher resolves an interpreter that
// actually satisfies the minimum instead.
//
// Usage:
//   node scripts/py.mjs <python arguments>
//   node scripts/py.mjs --env KEY=VALUE [--env KEY=VALUE ...] <python arguments>

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const MINIMUM_VERSION = [3, 10];

const REPOSITORY_ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");

// The documented setup installs requirements into a repository-local virtual
// environment, but npm scripts do not inherit an activated environment. Without
// this lookup the launcher picks a bare interpreter from PATH and every
// dependency import fails.
function virtualEnvironmentInterpreters() {
  const roots = [process.env.VIRTUAL_ENV, join(REPOSITORY_ROOT, ".venv"), join(REPOSITORY_ROOT, "venv")];
  const found = [];
  for (const root of roots) {
    if (!root) {
      continue;
    }
    for (const relative of ["bin/python", "Scripts/python.exe"]) {
      const candidate = join(root, relative);
      if (existsSync(candidate)) {
        found.push(candidate);
      }
    }
  }
  return found;
}

const args = process.argv.slice(2);
const childEnv = { ...process.env };

while (args[0] === "--env") {
  args.shift();
  const assignment = args.shift();
  const separatorIndex = assignment?.indexOf("=") ?? -1;

  if (separatorIndex <= 0) {
    console.error(
      "Usage error: --env must be followed by KEY=VALUE before Python arguments.",
    );
    process.exit(1);
  }

  childEnv[assignment.slice(0, separatorIndex)] = assignment.slice(
    separatorIndex + 1,
  );
}

// Explicit override first, then the project environment where dependencies
// actually live, then newest known minor versions, then the generic names.
// Ordering matters: `python3` is checked late because on macOS it is frequently
// the system 3.9.
const CANDIDATES = [
  process.env.LOOMSTEAD_PYTHON,
  ...virtualEnvironmentInterpreters(),
  "python3.13",
  "python3.12",
  "python3.11",
  "python3.10",
  "python3",
  "python",
].filter(Boolean);

function probe(candidate) {
  const result = spawnSync(candidate, ["--version"], { encoding: "utf8" });
  if (result.status !== 0) {
    return null;
  }
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  const match = output.match(/Python\s+(\d+)\.(\d+)/);
  if (!match) {
    return null;
  }
  return { major: Number(match[1]), minor: Number(match[2]) };
}

function satisfies(version) {
  const [major, minor] = MINIMUM_VERSION;
  return (
    version.major > major || (version.major === major && version.minor >= minor)
  );
}

const rejected = [];
let interpreter = null;

for (const candidate of CANDIDATES) {
  const version = probe(candidate);
  if (!version) {
    continue;
  }
  if (satisfies(version)) {
    interpreter = candidate;
    break;
  }
  rejected.push(`${candidate} (${version.major}.${version.minor})`);
}

if (!interpreter) {
  const required = MINIMUM_VERSION.join(".");
  console.error(`No Python >= ${required} found on PATH.`);
  if (rejected.length > 0) {
    console.error(`Interpreters found but too old: ${rejected.join(", ")}.`);
  }
  console.error(
    `Install Python ${required} or newer, or point LOOMSTEAD_PYTHON at a suitable interpreter.`,
  );
  process.exit(1);
}

const child = spawn(interpreter, args, {
  env: childEnv,
  stdio: "inherit",
});

child.on("error", (error) => {
  console.error(
    `Failed to start Python interpreter "${interpreter}": ${error.message}`,
  );
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.exit(1);
  }
  process.exit(code ?? 1);
});
