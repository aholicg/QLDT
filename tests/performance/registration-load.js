import http from 'k6/http';
import { check, fail, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

/*
 * Gateway load test for the student course-registration portal.
 *
 * Safe default: MODE=read (login + GET /sections + GET /registrations/me).
 * Mutating mode: MODE=cycle, guarded by ALLOW_REGISTRATION_WRITES=true and
 * dedicated one-account-per-VU test users. Each successful POST is followed
 * by verification and deletion of that exact registration ID.
 */

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:8080').replace(/\/+$/, '');
const SEMESTER_ID = Number(__ENV.SEMESTER_ID || 0);
const PAGE_SIZE = Number(__ENV.PAGE_SIZE || 20);
const MODE = (__ENV.MODE || 'read').toLowerCase();
const PROFILE = (__ENV.PROFILE || 'load').toLowerCase();
const PASSWORD = __ENV.STUDENT_PASSWORD || '';
const REQUEST_TIMEOUT = __ENV.REQUEST_TIMEOUT || '10s';
const SECTION_ID = Number(__ENV.SECTION_ID || 0);
const USERNAME = __ENV.STUDENT_USERNAME || '';
const USERNAME_PREFIX = __ENV.STUDENT_USERNAME_PREFIX || '';
const STUDENT_START_NUMBER = Number(__ENV.STUDENT_START_NUMBER || 1);
const STUDENT_NUMBER_WIDTH = Number(__ENV.STUDENT_NUMBER_WIDTH || 4);
const ALLOW_WRITES = __ENV.ALLOW_REGISTRATION_WRITES === 'true';
const THINK_TIME_SECONDS = Number(
  __ENV.THINK_TIME_SECONDS || (MODE === 'cycle' ? 6 : 2),
);

const profiles = {
  smoke: [
    { duration: '15s', target: 1 },
    { duration: '30s', target: 1 },
    { duration: '5s', target: 0 },
  ],
  load: [
    { duration: '1m', target: 10 },
    { duration: '2m', target: 25 },
    { duration: '1m', target: 25 },
    { duration: '30s', target: 0 },
  ],
  stress: [
    { duration: '1m', target: 10 },
    { duration: '1m', target: 25 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  soak: [
    { duration: '1m', target: 10 },
    { duration: '10m', target: 20 },
    { duration: '1m', target: 0 },
  ],
};

if (!SEMESTER_ID || !Number.isInteger(SEMESTER_ID)) {
  throw new Error('Set SEMESTER_ID to the active semester ID.');
}
if (!PASSWORD) {
  throw new Error('Set STUDENT_PASSWORD; do not put credentials in this script.');
}
if (!profiles[PROFILE]) {
  throw new Error(`Unknown PROFILE=${PROFILE}; use smoke, load, stress, or soak.`);
}
if (!Number.isFinite(THINK_TIME_SECONDS) || THINK_TIME_SECONDS < 0) {
  throw new Error('THINK_TIME_SECONDS must be a non-negative number.');
}
if (!['read', 'cycle'].includes(MODE)) {
  throw new Error('MODE must be read or cycle.');
}
if (MODE === 'read' && !USERNAME) {
  throw new Error('Read mode requires STUDENT_USERNAME (one account may be shared safely).');
}
if (MODE === 'cycle') {
  if (!ALLOW_WRITES) {
    throw new Error('Cycle mode is disabled. Set ALLOW_REGISTRATION_WRITES=true explicitly.');
  }
  if (!SECTION_ID || !Number.isInteger(SECTION_ID) || !USERNAME_PREFIX) {
    throw new Error('Cycle mode requires SECTION_ID and STUDENT_USERNAME_PREFIX.');
  }
  if (STUDENT_START_NUMBER < 0 || STUDENT_NUMBER_WIDTH < 1) {
    throw new Error('Invalid student number range.');
  }
}

const registrationChecks = new Rate('registration_lifecycle_checks');
const sectionsDuration = new Trend('sections_list_duration', true);
const registrationsDuration = new Trend('registrations_me_duration', true);
const registrationPostDuration = new Trend('registration_post_duration', true);
const registrationDeleteDuration = new Trend('registration_delete_duration', true);

export const options = {
  scenarios: {
    registration_portal: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: profiles[PROFILE],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
    registration_lifecycle_checks: ['rate>0.99'],
    sections_list_duration: ['p(95)<2000'],
    registrations_me_duration: ['p(95)<2000'],
    ...(MODE === 'cycle' ? { registration_post_duration: ['p(95)<2000'] } : {}),
  },
};

let accessToken;
let loggedInUsername;

function currentUsername() {
  if (MODE === 'read') return USERNAME;
  const number = STUDENT_START_NUMBER + __VU - 1;
  return `${USERNAME_PREFIX}${String(number).padStart(STUDENT_NUMBER_WIDTH, '0')}`;
}

function authHeaders() {
  return { Authorization: `Bearer ${accessToken}` };
}

function requestOptions(tags, headers = {}) {
  return {
    headers,
    tags: { component: 'registration-portal', ...tags },
    timeout: REQUEST_TIMEOUT,
  };
}

function jsonBody(response) {
  try {
    return response.json();
  } catch (_error) {
    return null;
  }
}

function ensureLogin() {
  const username = currentUsername();
  if (accessToken && loggedInUsername === username) return;

  const response = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({ username, password: PASSWORD }),
    requestOptions({ endpoint: 'login' }, { 'Content-Type': 'application/json' }),
  );
  const body = jsonBody(response);
  const ok = check(response, {
    'login returns HTTP 200': (res) => res.status === 200,
    'login returns accessToken': () => Boolean(body && body.accessToken),
  });
  registrationChecks.add(ok);
  if (!ok) fail(`Login failed for ${username}: HTTP ${response.status}`);

  accessToken = body.accessToken;
  loggedInUsername = username;
}

function readPortal() {
  const catalog = http.get(
    `${BASE_URL}/api/sections?semesterId=${SEMESTER_ID}&page=1&size=${PAGE_SIZE}`,
    requestOptions({ endpoint: 'sections-list' }, authHeaders()),
  );
  sectionsDuration.add(catalog.timings.duration);
  const catalogBody = jsonBody(catalog);
  const catalogOk = check(catalog, {
    'section catalog returns HTTP 200': (res) => res.status === 200,
    'section catalog returns paginated items': () => Boolean(
      catalogBody && Array.isArray(catalogBody.items)
      && Number.isInteger(catalogBody.totalItems),
    ),
  });
  registrationChecks.add(catalogOk);

  const mine = http.get(
    `${BASE_URL}/api/registrations/me?semesterId=${SEMESTER_ID}`,
    requestOptions({ endpoint: 'registrations-me' }, authHeaders()),
  );
  registrationsDuration.add(mine.timings.duration);
  const mineBody = jsonBody(mine);
  const mineOk = check(mine, {
    'my registrations returns HTTP 200': (res) => res.status === 200,
    'my registrations returns items': () => Boolean(mineBody && Array.isArray(mineBody.items)),
  });
  registrationChecks.add(mineOk);
  return mineBody;
}

function registrationCycle(mineBody) {
  const alreadyRegistered = (mineBody?.items || []).some(
    (item) => item.section && item.section.id === SECTION_ID,
  );
  if (alreadyRegistered) {
    registrationChecks.add(false);
    console.error(`VU ${__VU}: ${currentUsername()} already owns section ${SECTION_ID}; not modifying it.`);
    return;
  }

  const created = http.post(
    `${BASE_URL}/api/registrations`,
    JSON.stringify({ sectionId: SECTION_ID }),
    requestOptions(
      { endpoint: 'registration-create' },
      { ...authHeaders(), 'Content-Type': 'application/json' },
    ),
  );
  registrationPostDuration.add(created.timings.duration);
  const createdBody = jsonBody(created);
  const createOk = check(created, {
    'registration POST returns HTTP 201': (res) => res.status === 201,
    'registration POST returns registration ID': () => Boolean(
      createdBody && Number.isInteger(createdBody.id) && createdBody.id > 0,
    ),
  });
  registrationChecks.add(createOk);
  if (!createOk) return;

  // Verify that the exact new registration is visible to the same student.
  const afterCreate = http.get(
    `${BASE_URL}/api/registrations/me?semesterId=${SEMESTER_ID}`,
    requestOptions({ endpoint: 'registrations-me-after-create' }, authHeaders()),
  );
  registrationsDuration.add(afterCreate.timings.duration);
  const afterCreateBody = jsonBody(afterCreate);
  const visible = check(afterCreate, {
    'registration is visible after POST': (res) => res.status === 200
      && Array.isArray(afterCreateBody?.items)
      && afterCreateBody.items.some((item) => item.id === createdBody.id),
  });
  registrationChecks.add(visible);

  // Always attempt to delete only the ID returned by this VU's own successful POST.
  const deleted = http.del(
    `${BASE_URL}/api/registrations/${createdBody.id}`,
    null,
    requestOptions({ endpoint: 'registration-cancel' }, authHeaders()),
  );
  registrationDeleteDuration.add(deleted.timings.duration);
  const deleteOk = check(deleted, {
    'registration DELETE returns HTTP 204': (res) => res.status === 204,
  });
  registrationChecks.add(deleteOk);

  const afterDelete = http.get(
    `${BASE_URL}/api/registrations/me?semesterId=${SEMESTER_ID}`,
    requestOptions({ endpoint: 'registrations-me-after-delete' }, authHeaders()),
  );
  registrationsDuration.add(afterDelete.timings.duration);
  const afterDeleteBody = jsonBody(afterDelete);
  const absent = check(afterDelete, {
    'registration is absent after DELETE': (res) => res.status === 200
      && Array.isArray(afterDeleteBody?.items)
      && !afterDeleteBody.items.some((item) => item.id === createdBody.id),
  });
  registrationChecks.add(absent);
}

export default function () {
  ensureLogin();
  const mine = readPortal();
  if (MODE === 'cycle' && mine) registrationCycle(mine);
  sleep(THINK_TIME_SECONDS);
}
