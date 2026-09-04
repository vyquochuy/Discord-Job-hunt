/**
 * Job Hunter Platform — Auth API Endpoints
 */

import { client } from './client.js';

export function register(email, password, fullName) {
  return client.post('/auth/register', { email, password, full_name: fullName });
}

export function login(email, password) {
  return client.post('/auth/login', { email, password });
}

export function getMe() {
  return client.get('/auth/me');
}
