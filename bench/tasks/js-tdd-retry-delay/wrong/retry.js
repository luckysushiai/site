function retryDelay(attempt, options) {
  if (!options || !Number.isInteger(options.baseMs) || options.baseMs < 0) {
    throw new TypeError("baseMs must be a non-negative integer");
  }
  if (!Number.isInteger(options.capMs) || options.capMs < options.baseMs) {
    throw new TypeError("capMs must be an integer >= baseMs");
  }
  if (typeof options.factor !== "number" || !Number.isFinite(options.factor) || options.factor < 1) {
    throw new TypeError("factor must be a finite number >= 1");
  }
  if (!Number.isInteger(attempt) || attempt < 1) {
    throw new TypeError("attempt must be an integer >= 1");
  }
  const raw = options.baseMs * Math.pow(options.factor, attempt - 1);
  const rounded = Math.floor(raw);
  return Math.min(options.capMs, rounded);
}

module.exports = { retryDelay };
