// HIDDEN_VERIFIER_ONLY
function normalizeTag(tag) {
  if (typeof tag !== "string") {
    throw new TypeError("tag must be a string");
  }
  const trimmed = tag.trim().toLowerCase();
  if (trimmed === "") {
    return "";
  }
  return trimmed.split(/\s+/).join(' ');
}

module.exports = { normalizeTag };
