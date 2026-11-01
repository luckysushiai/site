function formatMoney(cents, currency) {
  const amount = (cents / 100).toFixed(2);
  return currency + ' ' + amount;
}

function formatReceipt(order) {
  const header = order.id + ' receipt';
  const total = formatMoney(order.currency, order.totalCents);
  return header + '\n' + total;
}

module.exports = { formatMoney, formatReceipt };
