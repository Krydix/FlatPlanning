// Work in cents so category totals and the reduced reserve reconcile exactly.
export function budgetSummary(parts) {
  const cents = row => Math.round(row.total * 100);
  const core = parts.filter(row => !row.optional);
  const coreCents = core.reduce((sum, row) => sum + cents(row), 0);
  const woodCents = core.filter(row => row.category === 'Wood').reduce((sum, row) => sum + cents(row), 0);
  const reserveCents = core.filter(row => row.id === 'contingency').reduce((sum, row) => sum + cents(row), 0);
  const withoutWoodBaseCents = coreCents - woodCents - reserveCents;
  const withoutWoodReserveCents = Math.round(withoutWoodBaseCents * 0.1);
  return {
    core: coreCents / 100,
    wood: woodCents / 100,
    withoutWoodBase: withoutWoodBaseCents / 100,
    withoutWoodReserve: withoutWoodReserveCents / 100,
    withoutWood: (withoutWoodBaseCents + withoutWoodReserveCents) / 100,
    woodSaving: (coreCents - withoutWoodBaseCents - withoutWoodReserveCents) / 100,
    categories: Object.fromEntries([...new Set(parts.map(row => row.category))].map(category => [category, parts.filter(row => row.category === category).reduce((sum, row) => sum + cents(row), 0) / 100])),
  };
}
