import { readFileSync } from 'node:fs';

const web = readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const rest = readFileSync(new URL('../src/Anvil/REST.cls', import.meta.url), 'utf8');

const requiredWebContracts = [
  "'/api/admin/login'",
  "'/v2/web-app?name='",
  "'/info'",
  "'/v2/processes?maxRows=100'",
  "'/v2/tasks?maxRows=100'",
  "Authorization:'Bearer '+sysAdminToken",
  "idempotencyKey:'ui-'+crypto.randomUUID()",
];

const requiredServerContracts = [
  'action\'="DEPLOY_WEB_APP"',
  'target\'="/anvil-demo"',
  'postcondition mismatch',
  'iris-anvil/receipt/v2|',
  'Security.Applications).Get',
];

for (const contract of requiredWebContracts) {
  if (!web.includes(contract)) throw new Error(`missing browser contract: ${contract}`);
}
for (const contract of requiredServerContracts) {
  if (!rest.includes(contract)) throw new Error(`missing server contract: ${contract}`);
}

if (/fetch\(['"]\/anvil\/admin[^\n]+method:\s*['"](?:PUT|DELETE)/.test(web)) {
  throw new Error('browser bypasses the official SysAdmin API for mutation');
}

console.log('IRIS Anvil contract gate passed');
