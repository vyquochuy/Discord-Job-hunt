import { client } from './client';
import { JobMatch, TopRecommendation } from '../types/match';

export function getTopRecommendations(limit = 10): Promise<TopRecommendation[]> {
  return client.get(`/matches/recommendations/top?limit=${limit}`);
}

export function getMatchDetail(jobId: string): Promise<JobMatch> {
  return client.get(`/matches/${jobId}`);
}

export function calculateMatch(jobId: string, forceRecalculate = false): Promise<JobMatch> {
  return client.post(`/matches/calculate/${jobId}`, {
    force_recalculate: forceRecalculate,
  });
}
