// Run: node scripts/check-market.mjs (no backend or test framework needed).
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const calls = [];
const client = { get: async (...args) => { calls.push(args); return {}; } };
const source = fs.readFileSync(new URL('../src/api/market.api.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const exports = {};
vm.runInNewContext(js, { exports, require: () => ({ client }), URLSearchParams });
assert.equal(typeof exports.getMarketOverview, 'function', 'typed overview API exists');
const controller = new AbortController();
await exports.getMarketSkills({ company: 'A & B', include_expired: false, search: 'C++', limit: 25 }, controller.signal);
const [url, options] = calls.pop();
assert.equal(new URL(url, 'https://example.com').searchParams.get('company'), 'A & B');
assert.equal(new URL(url, 'https://example.com').searchParams.get('search'), 'C++');
assert.equal(new URL(url, 'https://example.com').searchParams.get('include_expired'), 'false');
assert.equal(options.signal, controller.signal);
assert.equal(options.maxRetries, 0);
for (const [method, endpoint] of Object.entries({ getMarketOverview: 'overview', getHiringTrends: 'hiring-trends', getMarketSalaries: 'salaries', getMarketRoles: 'roles', getMarketGeography: 'geography', getMarketEmployers: 'employers', getMarketInsights: 'insights' })) {
  await exports[method]({}, controller.signal);
  assert.equal(calls.pop()[0], `/market/${endpoint}`);
}
await exports.getMarketFilters(controller.signal);
assert.equal(calls.pop()[0], '/market/filters');
// Render all eight panels with empty aggregates: no browser dependencies required.
const { createRequire } = await import('node:module');
const { fileURLToPath } = await import('node:url');
const path = await import('node:path');
const require = createRequire(import.meta.url);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
function loadTs(file) {
  const text = fs.readFileSync(file, 'utf8');
  const output = ts.transpileModule(text, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const exports = {};
  vm.runInNewContext(output, { exports, require: name => {
    if (!name.startsWith('.')) return require(name);
    const base = path.resolve(path.dirname(file), name);
    const found = ['.tsx', '.ts'].map(ext => base + ext).find(fs.existsSync);
    return loadTs(found);
  }});
  return exports;
}
const panels = loadTs(fileURLToPath(new URL('../src/pages/market/MarketPanels.tsx', import.meta.url)));
const meta = { status: 'empty', sample_size: 0, total_jobs: 0, coverage: 0, notes: [], generated_at: '2026-11-07', filters: {} };
const quality = { salary_coverage: { ratio: 0 }, date_range: { min: null, max: null, days: 0 }, missing_level: 0, missing_location: 0, missing_posted_at: 0, bulk_spikes: [] };
const emerging = { available: false, reason: 'Insufficient sample', items: [] };
const fixtures = {
  OverviewPanel: { totals: {}, recent: {}, distributions: { categories: [], levels: [], regions: [], sources: [], work_modes: [] }, data_quality: quality, sparkline: [] },
  HiringPanel: { summary: {}, series: [], stacked: [], sources: [], categories: [], levels: [], work_modes: [], caveats: [] },
  SalaryPanel: { normalized_vnd: {}, coverage: {}, native: [], histogram: [], by_level: [], by_category: [], by_region: [], by_source: [], top_companies: [] },
  SkillsPanel: { jobs_with_skills: 0, unique_skills: 0, top_skills: [], by_category: [], cooccurrence: [], by_level: [], emerging },
  RolesPanel: { top_titles: [], by_category: [], role_families: [], title_level_matrix: [], emerging },
  GeographyPanel: { remote_share: { remote_ratio: 0, flexible_ratio: 0 }, regions: [], cities: [], by_category: [], salary_by_region: [] },
  EmployersPanel: { concentration: { top10_share: 0, top20_share: 0 }, top_employers: [], by_category: [], new_entrants: [] },
  InsightsPanel: { disclaimer: 'Not a forecast', insights: [], methodology: [], data_quality: quality },
};
for (const [name, fixture] of Object.entries(fixtures)) {
  const html = renderToStaticMarkup(React.createElement(panels[name], { data: { meta, ...fixture }, drill() {} }));
  assert.ok(html.length > 100, `${name} renders empty data`);
  assert.ok(!html.includes('NaN'), `${name} does not show NaN`);
}
const charts = loadTs(fileURLToPath(new URL('../src/pages/market/MarketCharts.tsx', import.meta.url)));
const collapsedBars = renderToStaticMarkup(React.createElement(charts.Bars, { title: 'Nhóm nghề', initialLimit: 8, items: Array.from({ length: 12 }, (_, i) => ({ label: `Nhóm ${i}`, value: i + 1 })) }));
assert.ok(collapsedBars.includes('Xem tất cả (12 nhóm)'), 'long category list has expansion control');
assert.ok(collapsedBars.indexOf('Nhóm 8') > collapsedBars.indexOf('<details'), 'overflow categories are inside native disclosure');
assert.ok(collapsedBars.includes('Nhóm 11'), 'disclosure retains all categories');
const donut = renderToStaticMarkup(React.createElement(charts.Donut, { title: 'Nguồn', items: [{ label: 'A', value: 3 }, { label: 'B', value: 1 }] }));
assert.ok(donut.includes('75%') && donut.includes('25%'), 'donut shows real proportions');
assert.ok(!renderToStaticMarkup(React.createElement(charts.Donut, { title: 'Nguồn', items: [{ label: 'A', value: 0 }] })).includes('NaN'), 'empty donut remains safe');
const salarySource = fs.readFileSync(new URL('../src/pages/market/MarketPanels.tsx', import.meta.url), 'utf8');
assert.ok(!salarySource.includes('i.p90'), 'no unsupported percentile');
assert.ok(!salarySource.includes('rows={data.new_entrants}'), 'no inferred newcomer claims');
const trend = renderToStaticMarkup(React.createElement(charts.Trend, { title: 'Trend', points: [
  { bucket: '2026-11-01', label: '01/11', jobs: 0 },
  { bucket: '2026-11-02', label: '02/11', jobs: 100 },
  { bucket: '2026-11-03', label: '03/11', jobs: 0 },
] }));
assert.ok(trend.includes('>Tin</text>'), 'populated trend labels count axis');
assert.ok(trend.includes('>50</text>'), 'trend includes midpoint grid tick');
assert.ok(trend.includes('r="5"'), 'peak marker is emphasized');
assert.ok(trend.includes('02/11 · 100 tin'), 'peak date and true count remain visible');
assert.ok(trend.includes('Bảng số liệu theo thời gian'), 'trend keeps accessible data table');
const zeroTrend = renderToStaticMarkup(React.createElement(charts.Trend, { title: 'Zero', points: [{ bucket: '2026-11-01', label: '01/11', jobs: 0 }] }));
assert.ok(zeroTrend.includes('cao nhất 0 tin'), 'zero series does not claim scale ceiling as observed maximum');
const histogram = renderToStaticMarkup(React.createElement(charts.Histogram, { title: 'Salary', items: [{ label: '0–10', value: 0 }, { label: '10–20', value: 8 }] }));
assert.ok(histogram.includes('height:0px'), 'zero-count bin has no false bar');
assert.ok(histogram.includes('10–20') && histogram.includes('>8<'), 'histogram preserves bin labels and counts');
assert.ok(histogram.includes('Bảng phân bố'), 'histogram keeps exact values accessible');
console.log('Market API contract, empty-state and populated chart checks passed');
