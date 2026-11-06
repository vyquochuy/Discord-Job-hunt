import { client } from './client';
import { MarketAnalytics } from '../types/market';

export function getMarketAnalytics(): Promise<MarketAnalytics> {
  return client.get('/market/analytics');
}
