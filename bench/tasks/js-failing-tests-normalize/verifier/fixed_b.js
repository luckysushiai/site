// HIDDEN_VERIFIER_ONLY
function normalizeTag(tag) {
  if (typeof tag !== "string") {
    throw new TypeError("tag must be a string");
  }
  return tag.trim().toLowerCase().replace(/\s+/g, ' ').trim();
}

module.exports = { normalizeTag };
