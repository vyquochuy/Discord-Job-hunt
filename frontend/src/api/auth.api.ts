import { client } from './client';
import { User, AuthTokens } from '../types/auth';

export function register(email: string, password: string, fullName: string): Promise<AuthTokens & { user: User }> {
  return client.post('/auth/register', { email, password, full_name: fullName });
}

export function login(email: string, password: string): Promise<AuthTokens> {
  return client.post('/auth/login', { email, password });
}

export function getMe(): Promise<User> {
  return client.get('/auth/me');
}
