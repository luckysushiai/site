#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
export ROOT
node <<'JS'
const fs = require("fs");
const path = require("path");
const answer = {
  file: "receipt.js",
  line: 8,
  category: "swapped-arguments",
};
fs.writeFileSync(
  path.join(process.env.ROOT, "answer.json"),
  JSON.stringify(answer) + "\n",
);
JS
