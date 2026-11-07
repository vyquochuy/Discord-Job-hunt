import { client } from './client';
import type { MarketAnalytics, MarketFilterCatalog, MarketQuery, MarketResponses, MarketTab } from '../types/market';

export function getMarketAnalytics(): Promise<MarketAnalytics> {
  return client.get('/market/analytics');
}
export function getMarketFilters(signal?: AbortSignal): Promise<MarketFilterCatalog> {
  return client.get('/market/filters', { signal, maxRetries: 0 });
}
export function getMarketTab<K extends MarketTab>(tab: K, query: MarketQuery = {}, signal?: AbortSignal): Promise<MarketResponses[K]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== '') params.set(key, String(value));
  }
  const suffix = params.size ? `?${params}` : '';
  return client.get(`/market/${tab}${suffix}`, { signal, maxRetries: 0 });
}
export const getMarketOverview = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('overview', query, signal);
export const getHiringTrends = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('hiring-trends', query, signal);
export const getMarketSalaries = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('salaries', query, signal);
export const getMarketSkills = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('skills', query, signal);
export const getMarketRoles = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('roles', query, signal);
export const getMarketGeography = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('geography', query, signal);
export const getMarketEmployers = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('employers', query, signal);
export const getMarketInsights = (query: MarketQuery = {}, signal?: AbortSignal) => getMarketTab('insights', query, signal);
