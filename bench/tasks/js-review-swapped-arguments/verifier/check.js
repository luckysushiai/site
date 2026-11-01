// HIDDEN_VERIFIER_ONLY
const fs = require("fs");
const path = require("path");

const root = process.env.WORKDIR || "/app";
const here = process.env.VERIFIER_DIR || __dirname;
const expectedPath = path.join(here, "expected.json");
const expected = JSON.parse(fs.readFileSync(expectedPath, "utf8"));
const answerPath = path.join(root, "answer.json");

function fail(message) {
  console.error(message);
  process.exit(1);
}

if (!fs.existsSync(answerPath)) {
  fail("missing answer.json");
}

let got;
try {
  got = JSON.parse(fs.readFileSync(answerPath, "utf8"));
} catch (exc) {
  fail("answer.json is not JSON");
}

if (got === null || typeof got !== "object" || Array.isArray(got)) {
  fail("answer.json must be an object");
}
if (typeof got.line !== "number" || !Number.isInteger(got.line)) {
  fail("line must be an integer");
}
if (got.file !== expected.file) {
  fail("file does not match");
}
if (got.line !== expected.line) {
  fail("line does not match");
}
if (got.category !== expected.category) {
  fail("category does not match");
}
