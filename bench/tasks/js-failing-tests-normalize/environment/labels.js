function normalizeTag(tag) {
  if (typeof tag !== "string") {
    throw new TypeError("tag must be a string");
  }
  return tag.toLowerCase().split(/\s+/).join(' ');
}

module.exports = { normalizeTag };
