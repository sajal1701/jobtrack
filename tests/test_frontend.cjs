const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function main() {
  const handlers = {};
  const nodes = {};
  const buttons = [{disabled: false}, {disabled: false}];
  function node(id) {
    return nodes[id] ||= {
      value: '', hidden: false, textContent: '', children: [],
      addEventListener(event, callback) { handlers[`${id}:${event}`] = callback; },
      replaceChildren(...children) { this.children = children; },
      append(...children) { this.children.push(...children); },
      attributes: {},
      setAttribute(name, value) { this.attributes[name] = value; }, reset() { this.values = {}; },
      querySelectorAll() { return buttons; },
      querySelector() { return node('save-button'); },
    };
  }
  let mode = 'signed-out';
  let failLogout = false;
  let failList = false;
  let networkFailure = false;
  let emptyList = false;
  let listSize = 1;
  let total = 1;
  const listRequests = [];
  const authRequests = [];
  let confirmDelete = true;
  let deleteRequests = 0;
  let resolveDelete;
  let createRequests = 0;
  let resolveCreate;
  let createPayload;
  const fetch = async (path, options = {}) => {
    if (networkFailure) throw new TypeError('Failed to fetch');
    if (options.method === 'DELETE') {
      deleteRequests++;
      return new Promise(resolve => { resolveDelete = resolve; });
    }
    if (options.method === 'POST' && path === '/api/applications') {
      createRequests++;
      createPayload = JSON.parse(options.body);
      return new Promise(resolve => { resolveCreate = resolve; });
    }
    if (options.method === 'POST' && path.startsWith('/api/auth/')) authRequests.push(path);
    if (options.method === 'POST') assert.equal(options.headers['X-JobTrack'], '1');
    let status = 200;
    let payload;
    if (path === '/api/auth/me') { status = 401; payload = {detail: 'Please sign in.'}; }
    else if (path === '/api/auth/login' && mode === 'throttled') {
      status = 429; payload = {detail: 'Too many sign-in attempts. Try again in a minute.'};
    } else if (path === '/api/auth/login' && mode === 'signed-out') {
      status = 401; payload = {detail: 'Invalid username or password.'};
    } else if (path === '/api/auth/register') { mode = 'signed-in'; payload = {username: 'alice'}; }
    else if (path === '/api/auth/logout') {
      status = failLogout ? 500 : 204; payload = {detail: 'Try again.'};
    } else if (mode === 'expired') { status = 401; payload = {detail: 'Please sign in.'}; }
    else if (path.startsWith('/api/applications')) {
      listRequests.push(path);
      if (failList) return {ok: false, status: 500, json: async () => ({detail: 'Could not load applications.'})};
      payload = emptyList ? [] : Array.from({length: listSize}, (_, index) =>
        ({company: 'Private Company', role: 'Engineer', status: 'saved', id: index + 1}));
    } else if (path === '/api/stats') { payload = {total, by_status: {applied: 0, interview: 0, offer: 0}}; }
    else throw new Error(`Unexpected request: ${path}`);
    return {ok: status < 400, status, json: async () => payload};
  };
  const context = vm.createContext({
    document: {getElementById: node, createElement: (tagName) => ({
      ...node(Symbol()), tagName, events: {},
      addEventListener(name, callback) { this.events[name] = callback; },
    })},
    window: {confirm: () => confirmDelete},
    fetch, URLSearchParams, setTimeout, clearTimeout,
    FormData: class { constructor(form) { return Object.entries(form.values || {}); } },
  });
  vm.runInContext(fs.readFileSync('web/app.js', 'utf8'), context);
  await new Promise(setImmediate);
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('auth-panel').hidden, false);
  const password = node('auth-password');
  password.value = 'a-long-test-password';
  assert.equal(password.type, 'password');
  handlers['toggle-password:click']();
  assert.equal(password.type, 'text');
  assert.equal(password.value, 'a-long-test-password');
  assert.equal(node('toggle-password').textContent, 'Hide password');
  assert.equal(node('toggle-password').attributes['aria-pressed'], 'true');
  handlers['toggle-password:click']();
  assert.equal(password.type, 'password');
  assert.equal(node('toggle-password').textContent, 'Show password');
  assert.equal(node('toggle-password').attributes['aria-pressed'], 'false');
  const form = node('auth-form');
  form.values = {username: 'alice', password: 'a-long-test-password'};
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('notice').textContent, 'Invalid username or password.');
  assert.equal(buttons.every(button => !button.disabled), true);
  for (const submitter of [null, undefined]) {
    await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter});
    assert.equal(authRequests.at(-1), '/api/auth/login');
    assert.equal(node('notice').textContent, 'Invalid username or password.');
    assert.equal(node('tracker').hidden, true);
    assert.equal(buttons.every(button => !button.disabled), true);
  }
  networkFailure = true;
  const connectionMessage = 'Could not connect to JobTrack. Check that the server is running and try again.';
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('notice').textContent, connectionMessage);
  assert.equal(node('notice').hidden, false);
  assert.equal(node('notice').className, 'notice error');
  assert.equal(form.values.username, 'alice');
  assert.equal(form.values.password, 'a-long-test-password');
  assert.equal(buttons.every(button => !button.disabled), true);
  networkFailure = false;
  mode = 'throttled';
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'login'}});
  assert.equal(node('notice').textContent, 'Too many sign-in attempts. Try again in a minute.');
  assert.equal(node('notice').hidden, false);
  assert.equal(node('notice').className, 'notice error');
  assert.equal(node('tracker').hidden, true);
  assert.equal(buttons.every(button => !button.disabled), true);
  handlers['toggle-password:click']();
  await handlers['auth-form:submit']({preventDefault() {}, currentTarget: form, submitter: {value: 'register'}});
  assert.equal(authRequests.at(-1), '/api/auth/register');
  assert.equal(password.type, 'password');
  assert.equal(node('toggle-password').attributes['aria-pressed'], 'false');
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('auth-panel').hidden, true);
  assert.equal(node('account-name').textContent, 'Signed in as alice');
  assert.equal(node('total').textContent, 1);
  const applicationForm = node('application-form');
  applicationForm.values = {company: 'New Company', role: 'Engineer', follow_up_date: ''};
  const submitApplication = () => handlers['application-form:submit']({preventDefault() {}, currentTarget: applicationForm});
  const pendingSave = submitApplication();
  assert.equal(node('save-button').disabled, true);
  assert.equal(node('save-button').textContent, 'Saving…');
  assert.equal(createPayload.follow_up_date, null);
  await submitApplication();
  assert.equal(createRequests, 1);
  resolveCreate({ok: false, status: 500, json: async () => ({detail: 'Could not save application.'})});
  await pendingSave;
  assert.equal(applicationForm.values.company, 'New Company');
  assert.equal(node('notice').textContent, 'Could not save application.');
  assert.equal(node('save-button').disabled, false);
  assert.equal(node('save-button').textContent, 'Save application');
  const retriedSave = submitApplication();
  assert.equal(createRequests, 2);
  resolveCreate({ok: true, status: 201, json: async () => ({id: 2})});
  await retriedSave;
  assert.deepEqual(applicationForm.values, {});
  assert.equal(node('notice').textContent, 'Application saved.');
  assert.equal(node('save-button').disabled, false);
  assert.equal(node('save-button').textContent, 'Save application');
  const remove = node('applications').children[0].children.at(-1).children.at(-1);
  confirmDelete = false;
  await remove.events.click();
  assert.equal(deleteRequests, 0);
  confirmDelete = true;
  const pendingDelete = remove.events.click();
  assert.equal(remove.disabled, true);
  assert.equal(remove.textContent, 'Deleting…');
  await remove.events.click();
  assert.equal(deleteRequests, 1);
  resolveDelete({ok: false, status: 500, json: async () => ({detail: 'Could not delete application.'})});
  await pendingDelete;
  assert.equal(remove.disabled, false);
  assert.equal(remove.textContent, 'Delete');
  assert.equal(node('notice').textContent, 'Could not delete application.');
  assert.equal(node('applications').children.length, 1);
  const retryDelete = remove.events.click();
  assert.equal(deleteRequests, 2);
  emptyList = true;
  total = 0;
  resolveDelete({ok: true, status: 204});
  await retryDelete;
  assert.equal(node('notice').textContent, 'Application deleted.');
  assert.equal(node('total').textContent, 0);
  emptyList = false;
  total = 1;
  await vm.runInContext('load()', context);
  assert.equal(node('application-summary').textContent,
    'Showing 1 matching application. Statistics cover your whole tracker.');
  listSize = 100;
  total = 125;
  await vm.runInContext('load()', context);
  assert.equal(node('application-summary').textContent,
    'Showing the first 100 matching applications. Statistics cover your whole tracker.');
  listSize = 2;
  await vm.runInContext('load()', context);
  assert.equal(node('application-summary').textContent,
    'Showing 2 matching applications. Statistics cover your whole tracker.');
  listSize = 1;
  emptyList = true;
  total = 0;
  await vm.runInContext('load()', context);
  assert.equal(node('application-summary').textContent,
    'Showing 0 matching applications. Statistics cover your whole tracker.');
  assert.equal(node('applications').children[0].textContent,
    'No applications yet. Add your first opportunity using the form.');
  total = 1;
  node('search').value = 'No match';
  await vm.runInContext('load()', context);
  assert.equal(node('applications').children[0].textContent,
    'No applications match these filters. Try another search or use Clear filters.');
  assert.equal(node('total').textContent, 1);
  emptyList = false;
  await handlers['clear-filters:click']();
  assert.equal(node('applications').children[0].tagName, 'article');
  node('search').value = 'Private & Co';
  node('stage').value = 'interview';
  handlers['search:input']();
  const requestsBeforeClear = listRequests.length;
  await handlers['clear-filters:click']();
  assert.equal(node('search').value, '');
  assert.equal(node('stage').value, '');
  const clearedUrl = new URL(listRequests.at(-1), 'http://localhost');
  assert.equal(clearedUrl.searchParams.get('search'), '');
  assert.equal(clearedUrl.searchParams.has('status'), false);
  assert.equal(node('notice').hidden, true);
  await new Promise(resolve => setTimeout(resolve, 250));
  assert.equal(listRequests.length, requestsBeforeClear + 1);
  failList = true;
  await handlers['clear-filters:click']();
  assert.equal(node('notice').textContent, 'Could not load applications.');
  assert.equal(node('notice').className, 'notice error');
  failList = false;
  networkFailure = true;
  await handlers['logout:click']();
  assert.equal(node('notice').textContent, connectionMessage);
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('account-name').textContent, 'Signed in as alice');
  assert.equal(node('logout').disabled, false);
  networkFailure = false;
  failLogout = true;
  await handlers['logout:click']();
  assert.equal(node('tracker').hidden, false);
  assert.equal(node('notice').textContent, 'Try again.');
  failLogout = false;
  node('search').value = 'Pending search';
  handlers['search:input']();
  const requestsBeforeLogout = listRequests.length;
  vm.runInContext('setPasswordVisibility(true)', context);
  await handlers['logout:click']();
  assert.equal(password.type, 'password');
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('applications').children.length, 0);
  assert.equal(node('total').textContent, '0');
  await new Promise(resolve => setTimeout(resolve, 250));
  assert.equal(listRequests.length, requestsBeforeLogout);
  assert.equal(node('notice').textContent, 'Signed out.');
  assert.equal(node('application-summary').textContent, '');
  vm.runInContext('showAccount({username:"alice"})', context);
  mode = 'expired';
  await vm.runInContext('load().catch(() => {})', context);
  assert.equal(node('tracker').hidden, true);
  assert.equal(node('applications').children.length, 0);
  console.log('Frontend authentication checks passed: login failure, registration, logout failure/success, and session expiry.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
