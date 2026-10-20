import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { budgetSummary } from '../src/budget.mjs';

test('reclaimed wood comparison removes the timber reserve and keeps machining allowances', () => {
  const parts = [
    {id:'pipe',category:'Hardware',total:100},
    {id:'board',category:'Wood',total:100},
    {id:'waste',category:'Wood',total:15},
    {id:'light-cover',category:'Wood',total:20},
    {id:'machining',category:'Allowances',total:50},
    {id:'contingency',category:'Allowances',total:28.5},
    {id:'crate',category:'Crates',total:59.94,optional:true},
  ];
  const result=budgetSummary(parts);
  assert.equal(result.core,313.5);
  assert.equal(result.withoutWoodBase,150);
  assert.equal(result.withoutWoodReserve,15);
  assert.equal(result.withoutWood,165);
  assert.equal(result.woodSaving,148.5);
  assert.equal(result.categories.Crates,59.94);
});

test('published category subtotals reconcile with the full BOM in cents', () => {
  const {parts,meta}=JSON.parse(fs.readFileSync(new URL('../public/data/project.json',import.meta.url)));
  const result=budgetSummary(parts);
  assert.equal(result.core,meta.coreBudget);
  assert.equal(result.withoutWood,1821.64);
  assert.equal(result.withoutWoodReserve,165.6);
  assert.equal(Math.round((result.withoutWood+result.woodSaving)*100),Math.round(result.core*100));
  assert.equal(Object.values(result.categories).reduce((sum,total)=>sum+Math.round(total*100),0),parts.reduce((sum,row)=>sum+Math.round(row.total*100),0));
});
