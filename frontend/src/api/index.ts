export { client, ApiClient } from './client';
export * as authApi from './auth.api';
export * as jobsApi from './jobs.api';
export * as matchesApi from './matches.api';
export * as resumeApi from './resume.api';
export * as applicationsApi from './applications.api';
export * as profileApi from './profile.api';
export * as systemApi from './system.api';

import { client } from './client';
import * as authApi from './auth.api';
import * as jobsApi from './jobs.api';
import * as matchesApi from './matches.api';
import * as resumeApi from './resume.api';
import * as applicationsApi from './applications.api';
import * as profileApi from './profile.api';
import * as systemApi from './system.api';

export const api = {
  client,
  auth: authApi,
  jobs: jobsApi,
  matches: matchesApi,
  resume: resumeApi,
  applications: applicationsApi,
  profile: profileApi,
  system: systemApi,
};
