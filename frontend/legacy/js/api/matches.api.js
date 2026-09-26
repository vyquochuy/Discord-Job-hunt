/**
 * Job Hunter Platform — Matching Engine API Endpoints
 */

import { client } from './client.js';

export function getTopRecommendations(limit = 10) {
  return client.get(`/matches/recommendations/top?limit=${limit}`);
}

export function getMatchDetail(jobId) {
  return client.get(`/matches/${jobId}`);
}

export function calculateMatch(jobId, forceRecalculate = false) {
  return client.post(`/matches/calculate/${jobId}`, {
    force_recalculate: forceRecalculate,
  });
}
