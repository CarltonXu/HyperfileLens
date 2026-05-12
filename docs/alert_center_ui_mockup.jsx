import React, { useMemo, useState } from 'react';

/**
 * Alert Center UI Mockup
 * Self-contained React + Tailwind version.
 *
 * Why this version exists:
 * - No lucide-react dependency, because some sandbox/CDN environments fail to fetch icon modules.
 * - No shadcn/ui dependency, so the mockup can run in stricter preview environments.
 * - Icons are implemented as small inline text/SVG-like components.
 */

const Icon = ({ name, className = '' }) => {
  const icons = {
    bell: '🔔',
    plus: '+',
    search: '⌕',
    refresh: '↻',
    edit: '✎',
    trash: '🗑',
    copy: '⧉',
    power: '⏻',
    eye: '👁',
    check: '✓',
    close: '×',
    mail: '✉',
    warning: '⚠',
    clock: '◷',
    activity: '▣',
    history: '↺',
    list: '☷',
    webhook: '↗',
  };

  return (
    <span aria-hidden="true" className={`inline-flex h-4 w-4 items-center justify-center text-sm leading-none ${className}`}>
      {icons[name] || '•'}
    </span>
  );
};

const Card = ({ className = '', children }) => (
  <div className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</div>
);

const CardContent = ({ className = '', children }) => <div className={className}>{children}</div>;

const Button = ({ children, variant = 'solid', size = 'md', className = '', ...props }) => {
  const base = 'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60';
  const sizes = {
    sm: 'h-8 px-2.5 text-xs',
    md: 'h-10 px-4 text-sm',
  };
  const variants = {
    solid: 'bg-blue-600 text-white hover:bg-blue-700',
    outline: 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
    ghost: 'text-slate-600 hover:bg-slate-100',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
};

const tabs = [
  { key: 'policies', label: 'Alert Policies', icon: 'list' },
  { key: 'create', label: 'Create Policy', icon: 'plus' },
  { key: 'active', label: 'Active Alerts', icon: 'bell' },
  { key: 'history', label: 'Alert History', icon: 'history' },
  { key: 'channels', label: 'Notification Channels', icon: 'mail' },
];

const severityClass = {
  critical: 'bg-red-50 text-red-700 border-red-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
};

const statusClass = {
  enabled: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  disabled: 'bg-slate-100 text-slate-600 border-slate-200',
  firing: 'bg-red-50 text-red-700 border-red-200',
  acknowledged: 'bg-violet-50 text-violet-700 border-violet-200',
  resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
};

const policyRows = [
  ['High CPU Usage', 'metric', 'warning', 'sync_proxy', 'selected', 'enabled'],
  ['Repository Capacity High', 'metric', 'critical', 'backup_repository', 'all', 'enabled'],
  ['Backup Job Failed', 'job', 'critical', 'job', 'selected', 'enabled'],
  ['License Near Expiration', 'event', 'warning', 'license', 'all', 'disabled'],
];

const activeAlertRows = [
  ['critical', 'Repository Capacity Usage High', 'metric', 'repo-primary', '92%', '>= 90%', 'firing'],
  ['warning', 'High CPU Usage', 'metric', 'sync-proxy-01', '83%', '>= 80%', 'acknowledged'],
  ['critical', 'Backup Job Failed', 'job', 'backup-job-1024', 'failed', 'job_failed', 'firing'],
];

const historyRows = [
  ['warning', 'High Memory Usage', 'metric', 'gateway-01', 'resolved', '2026-05-10 11:20', '2026-05-10 11:35', '15m'],
  ['critical', 'Gateway Offline', 'availability', 'gateway-02', 'resolved', '2026-05-09 08:10', '2026-05-09 08:18', '8m'],
];

const channelRows = [
  ['Ops Email', 'email', 'enabled', 'ops@example.com'],
  ['NOC Webhook', 'webhook', 'enabled', 'https://example.com/webhook'],
  ['Support DingTalk', 'dingtalk', 'disabled', 'DingTalk Bot'],
];

const TEST_CASES = [
  { name: 'tabs include required pages', pass: tabs.length === 5 && tabs.some((t) => t.key === 'policies') && tabs.some((t) => t.key === 'channels') },
  { name: 'policy rows include all core policy columns', pass: policyRows.every((row) => row.length === 6) },
  { name: 'active alert rows include status values', pass: activeAlertRows.every((row) => ['firing', 'acknowledged', 'pending'].includes(row[6])) },
  { name: 'history rows are resolved records', pass: historyRows.every((row) => row[4] === 'resolved') },
  { name: 'channels include email and webhook', pass: channelRows.some((row) => row[1] === 'email') && channelRows.some((row) => row[1] === 'webhook') },
];

if (typeof console !== 'undefined') {
  TEST_CASES.forEach((test) => {
    if (!test.pass) console.warn(`UI mockup test failed: ${test.name}`);
  });
}

function Badge({ children, type = 'info' }) {
  const cls = severityClass[type] || statusClass[type] || 'bg-slate-100 text-slate-600 border-slate-200';
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>{children}</span>;
}

function Field({ label, children, required }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-slate-700">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </label>
      {children}
    </div>
  );
}

function Input({ placeholder, className = '' }) {
  return <input className={`w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 ${className}`} placeholder={placeholder} />;
}

function Select({ children, value, onChange }) {
  return (
    <select value={value} onChange={onChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
      {children}
    </select>
  );
}

function Section({ title, desc, children }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900">{title}</h3>
            {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
          </div>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function PageHeader({ title, desc, action }) {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">{desc}</p>
      </div>
      {action}
    </div>
  );
}

function FilterBar({ children }) {
  return <div className="mb-4 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-5">{children}</div>;
}

function DataTable({ children }) {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">{children}</div>
    </Card>
  );
}

function PoliciesPage({ onCreate }) {
  return (
    <>
      <PageHeader
        title="Alert Policies"
        desc="Create and manage global alert rules for resources, jobs, events and system services."
        action={
          <div className="flex gap-2">
            <Button variant="outline"><Icon name="refresh" />Refresh</Button>
            <Button onClick={onCreate}><Icon name="plus" />Create Alert Policy</Button>
          </div>
        }
      />

      <FilterBar>
        <div className="relative md:col-span-2">
          <Icon name="search" className="absolute left-3 top-2.5 text-slate-400" />
          <input className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm" placeholder="Search by policy name" />
        </div>
        <Select><option>All Types</option><option>Metric</option><option>Availability</option><option>Job</option><option>Event</option><option>System</option></Select>
        <Select><option>All Severity</option><option>Critical</option><option>Warning</option><option>Info</option></Select>
        <Select><option>All Status</option><option>Enabled</option><option>Disabled</option></Select>
      </FilterBar>

      <DataTable>
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Resource Type</th>
              <th>Scope</th>
              <th>Status</th>
              <th>Notification</th>
              <th className="pr-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {policyRows.map((row) => (
              <tr key={row[0]} className="hover:bg-slate-50">
                <td className="px-4 py-4 font-medium text-slate-900">
                  {row[0]}
                  <div className="text-xs font-normal text-slate-400">Updated 2026-05-10 10:20</div>
                </td>
                <td className="capitalize text-slate-600">{row[1]}</td>
                <td><Badge type={row[2]}>{row[2]}</Badge></td>
                <td className="text-slate-600">{row[3]}</td>
                <td className="text-slate-600">{row[4]}</td>
                <td><Badge type={row[5]}>{row[5]}</Badge></td>
                <td className="text-slate-600">Email, Webhook</td>
                <td className="pr-4 text-right">
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="ghost"><Icon name="edit" /></Button>
                    <Button size="sm" variant="ghost"><Icon name="copy" /></Button>
                    <Button size="sm" variant="ghost"><Icon name="power" /></Button>
                    <Button size="sm" variant="ghost"><Icon name="trash" /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function CreatePolicyPage() {
  const [type, setType] = useState('metric');

  const previewText = useMemo(() => {
    const map = {
      metric: 'Example: cpu_usage >= 80% for 5 minutes.',
      availability: 'Example: heartbeat missing for 5 minutes.',
      job: 'Example: backup job failed once.',
      event: 'Example: user_deleted or login_failed event occurs.',
      system: 'Example: celery_worker unhealthy for 5 minutes.',
    };
    return map[type] || map.metric;
  }, [type]);

  return (
    <>
      <PageHeader
        title="Create Alert Policy"
        desc="Configure trigger rules, recovery rules and notification channels."
        action={
          <div className="flex gap-2">
            <Button variant="outline">Cancel</Button>
            <Button variant="outline">Save Draft</Button>
            <Button>Save and Enable</Button>
          </div>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <Section title="Basic Info" desc="Define the name, type and severity of this alert policy.">
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Alert Name" required><Input placeholder="e.g. High CPU Usage" /></Field>
              <Field label="Alert Type" required>
                <Select value={type} onChange={(event) => setType(event.target.value)}>
                  <option value="metric">Metric Alert</option>
                  <option value="availability">Availability Alert</option>
                  <option value="job">Job Alert</option>
                  <option value="event">Event Alert</option>
                  <option value="system">System Alert</option>
                </Select>
              </Field>
              <Field label="Severity" required><Select><option>critical</option><option>warning</option><option>info</option></Select></Field>
              <Field label="Status">
                <div className="flex h-10 items-center gap-3 rounded-xl border border-slate-200 px-3">
                  <span className="h-5 w-9 rounded-full bg-blue-600 p-0.5"><span className="block h-4 w-4 translate-x-4 rounded-full bg-white" /></span>
                  <span className="text-sm text-slate-700">Enabled</span>
                </div>
              </Field>
              <div className="md:col-span-2">
                <Field label="Description"><textarea className="h-20 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="Describe when and why this alert should be triggered." /></Field>
              </div>
            </div>
          </Section>

          <Section title="Monitor Target" desc="Select the resource scope to monitor.">
            <div className="grid gap-4 md:grid-cols-3">
              <Field label="Resource Type" required><Select><option>sync_proxy</option><option>gateway</option><option>agent_proxy</option><option>backup_repository</option><option>source_resource</option><option>target_storage</option><option>job</option><option>system_service</option></Select></Field>
              <Field label="Scope" required><Select><option>selected</option><option>all</option></Select></Field>
              <Field label="Monitor Resources"><Select><option>proxy-prod-01</option><option>proxy-prod-02</option><option>repo-primary</option></Select></Field>
            </div>
          </Section>

          <Section title="Trigger Rule" desc="The form changes dynamically according to alert type.">
            {type === 'metric' && (
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Metric" required><Select><option>cpu_usage</option><option>memory_usage</option><option>disk_usage</option><option>capacity_usage</option></Select></Field>
                <Field label="Operator" required><Select><option>{'>='}</option><option>{'>'}</option><option>{'<='}</option><option>{'<'}</option></Select></Field>
                <Field label="Threshold" required><Input placeholder="80" /></Field>
                <Field label="Unit"><Input placeholder="%" /></Field>
                <Field label="Duration"><Select><option>5 minutes</option><option>10 minutes</option><option>30 minutes</option></Select></Field>
                <Field label="Evaluation Cycle"><Select><option>1 minute</option><option>5 minutes</option></Select></Field>
              </div>
            )}

            {type === 'availability' && (
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Check Type"><Select><option>heartbeat</option><option>connection</option><option>api_health</option></Select></Field>
                <Field label="Timeout"><Input placeholder="60 seconds" /></Field>
                <Field label="Duration"><Select><option>5 minutes</option><option>10 minutes</option></Select></Field>
              </div>
            )}

            {type === 'job' && (
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Job Type"><Select><option>backup</option><option>sync</option><option>restore</option><option>verify</option></Select></Field>
                <Field label="Event Type"><Select><option>job_failed</option><option>job_timeout</option><option>retry_exceeded</option><option>partial_success</option></Select></Field>
                <Field label="Consecutive Failures"><Input placeholder="1" /></Field>
              </div>
            )}

            {type === 'event' && (
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Event Category"><Select><option>user</option><option>license</option><option>repository</option><option>configuration</option><option>security</option></Select></Field>
                <Field label="Event Types"><Input placeholder="user_deleted, login_failed" /></Field>
              </div>
            )}

            {type === 'system' && (
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Check Type"><Select><option>service_health</option><option>database_health</option><option>disk_space</option></Select></Field>
                <Field label="Service Name"><Select><option>api_service</option><option>database</option><option>celery_worker</option><option>scheduler</option></Select></Field>
                <Field label="Duration"><Select><option>5 minutes</option><option>10 minutes</option></Select></Field>
              </div>
            )}
          </Section>

          <Section title="Recovery Rule" desc="Configure when the alert should be automatically resolved.">
            <div className="mb-4 flex items-center justify-between rounded-xl border border-slate-200 p-3">
              <span className="text-sm font-medium text-slate-700">Enable Auto Recovery</span>
              <span className="h-5 w-9 rounded-full bg-blue-600 p-0.5"><span className="block h-4 w-4 translate-x-4 rounded-full bg-white" /></span>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <Field label="Recovery Condition"><Select><option>below_threshold</option><option>heartbeat_restored</option><option>next_success</option><option>service_restored</option></Select></Field>
              <Field label="Operator"><Select><option>{'<'}</option><option>{'<='}</option><option>{'>'}</option></Select></Field>
              <Field label="Duration"><Select><option>2 minutes</option><option>3 minutes</option><option>5 minutes</option></Select></Field>
            </div>
          </Section>

          <Section title="Notification" desc="Select channels that will receive firing and recovery notifications.">
            <div className="grid gap-4 md:grid-cols-3">
              <Field label="Notification Channels"><Select><option>Email - Ops Team</option><option>Webhook - NOC</option><option>DingTalk - Support</option></Select></Field>
              <Field label="Notify On Trigger"><Select><option>Yes</option><option>No</option></Select></Field>
              <Field label="Notify On Recovery"><Select><option>Yes</option><option>No</option></Select></Field>
            </div>
          </Section>
        </div>

        <Card className="h-fit">
          <CardContent className="p-5">
            <h3 className="mb-3 font-semibold text-slate-900">Policy Preview</h3>
            <div className="space-y-3 text-sm text-slate-600">
              <div className="rounded-xl bg-slate-50 p-3"><span className="font-medium text-slate-900">Type:</span> {type}</div>
              <div className="rounded-xl bg-slate-50 p-3"><span className="font-medium text-slate-900">Rule:</span> {previewText}</div>
              <div className="rounded-xl bg-slate-50 p-3"><span className="font-medium text-slate-900">Recovery:</span> Auto resolve when recovery condition is met.</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function CardStat({ icon, label, value }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="rounded-2xl bg-slate-100 p-3"><Icon name={icon} className="text-slate-700" /></div>
        <div>
          <div className="text-2xl font-bold text-slate-950">{value}</div>
          <div className="text-sm text-slate-500">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function ActiveAlertsPage() {
  return (
    <>
      <PageHeader
        title="Active Alerts"
        desc="Current pending, firing and acknowledged alerts."
        action={
          <div className="flex gap-2">
            <Button variant="outline"><Icon name="check" />Batch Acknowledge</Button>
            <Button variant="outline"><Icon name="close" />Batch Resolve</Button>
            <Button><Icon name="refresh" />Refresh</Button>
          </div>
        }
      />

      <div className="mb-5 grid gap-4 md:grid-cols-4">
        <CardStat icon="warning" label="Critical" value="8" />
        <CardStat icon="clock" label="Warning" value="14" />
        <CardStat icon="activity" label="Firing" value="11" />
        <CardStat icon="check" label="Acknowledged" value="5" />
      </div>

      <FilterBar>
        <Input placeholder="Search alert or resource" />
        <Select><option>All Severity</option></Select>
        <Select><option>All Types</option></Select>
        <Select><option>All Status</option></Select>
        <Select><option>Last 24 hours</option></Select>
      </FilterBar>

      <DataTable>
        <table className="w-full min-w-[1080px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3"><input type="checkbox" /></th>
              <th>Severity</th>
              <th>Title</th>
              <th>Type</th>
              <th>Resource</th>
              <th>Current</th>
              <th>Threshold</th>
              <th>Status</th>
              <th>Duration</th>
              <th className="pr-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {activeAlertRows.map((row) => (
              <tr key={row[1]} className="hover:bg-slate-50">
                <td className="px-4 py-4"><input type="checkbox" /></td>
                <td><Badge type={row[0]}>{row[0]}</Badge></td>
                <td className="font-medium text-slate-900">
                  {row[1]}
                  <div className="text-xs font-normal text-slate-400">First triggered 2026-05-11 09:10</div>
                </td>
                <td>{row[2]}</td>
                <td>{row[3]}</td>
                <td>{row[4]}</td>
                <td>{row[5]}</td>
                <td><Badge type={row[6]}>{row[6]}</Badge></td>
                <td>36m</td>
                <td className="pr-4 text-right">
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="ghost"><Icon name="eye" /></Button>
                    <Button size="sm" variant="ghost"><Icon name="check" /></Button>
                    <Button size="sm" variant="ghost"><Icon name="close" /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function HistoryPage() {
  return (
    <>
      <PageHeader title="Alert History" desc="Resolved and historical alert records for auditing and troubleshooting." action={<Button variant="outline">Export</Button>} />
      <FilterBar>
        <Input placeholder="Search alert or resource" />
        <Select><option>All Severity</option></Select>
        <Select><option>All Types</option></Select>
        <Select><option>Resolved</option></Select>
        <Select><option>Last 7 days</option></Select>
      </FilterBar>
      <DataTable>
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Severity</th>
              <th>Title</th>
              <th>Type</th>
              <th>Resource</th>
              <th>Status</th>
              <th>First Triggered</th>
              <th>Resolved At</th>
              <th>Duration</th>
              <th className="pr-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {historyRows.map((row) => (
              <tr key={row[1]} className="hover:bg-slate-50">
                <td className="px-4 py-4"><Badge type={row[0]}>{row[0]}</Badge></td>
                <td className="font-medium text-slate-900">{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3]}</td>
                <td><Badge type={row[4]}>{row[4]}</Badge></td>
                <td>{row[5]}</td>
                <td>{row[6]}</td>
                <td>{row[7]}</td>
                <td className="pr-4 text-right"><Button size="sm" variant="ghost"><Icon name="eye" /></Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function ChannelsPage() {
  return (
    <>
      <PageHeader
        title="Notification Channels"
        desc="Manage email, webhook and IM notification channels."
        action={<Button><Icon name="plus" />Create Channel</Button>}
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
        <div>
          <FilterBar>
            <Input placeholder="Search channel" />
            <Select><option>All Types</option></Select>
            <Select><option>All Status</option></Select>
            <div />
            <Button variant="outline"><Icon name="refresh" />Refresh</Button>
          </FilterBar>

          <DataTable>
            <table className="w-full min-w-[780px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Target</th>
                  <th>Updated At</th>
                  <th className="pr-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {channelRows.map((row) => (
                  <tr key={row[0]} className="hover:bg-slate-50">
                    <td className="px-4 py-4 font-medium text-slate-900">{row[0]}</td>
                    <td className="capitalize">{row[1]}</td>
                    <td><Badge type={row[2]}>{row[2]}</Badge></td>
                    <td className="max-w-[260px] truncate text-slate-600">{row[3]}</td>
                    <td>2026-05-10</td>
                    <td className="pr-4 text-right">
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="ghost">Test</Button>
                        <Button size="sm" variant="ghost"><Icon name="edit" /></Button>
                        <Button size="sm" variant="ghost"><Icon name="trash" /></Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </DataTable>
        </div>

        <Card className="h-fit">
          <CardContent className="p-5">
            <h3 className="mb-4 font-semibold text-slate-900">Create Channel</h3>
            <div className="space-y-4">
              <Field label="Name"><Input placeholder="Ops Email" /></Field>
              <Field label="Type"><Select><option>Email</option><option>Webhook</option><option>DingTalk</option><option>WeCom</option></Select></Field>
              <Field label="SMTP Host / Webhook URL"><Input placeholder="smtp.example.com or https://..." /></Field>
              <Field label="Recipients / Headers"><textarea className="h-24 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="ops@example.com or JSON headers" /></Field>
              <div className="flex gap-2">
                <Button className="flex-1">Save</Button>
                <Button variant="outline">Test</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

export default function AlertCenterMockup() {
  const [active, setActive] = useState('policies');

  const Current =
    active === 'policies'
      ? PoliciesPage
      : active === 'create'
        ? CreatePolicyPage
        : active === 'active'
          ? ActiveAlertsPage
          : active === 'history'
            ? HistoryPage
            : ChannelsPage;

  return (
    <div className="min-h-screen bg-slate-100 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-5 flex items-center gap-3">
          <div className="rounded-2xl bg-blue-600 p-3 text-white shadow-sm"><Icon name="bell" className="h-6 w-6 text-lg" /></div>
          <div>
            <div className="text-xl font-bold">Alert Center UI Mockup</div>
            <div className="text-sm text-slate-500">First-phase complete alert module design</div>
          </div>
        </div>

        <div className="mb-6 flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActive(tab.key)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
                active === tab.key ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Icon name={tab.icon} />
              {tab.label}
            </button>
          ))}
        </div>

        <Current onCreate={() => setActive('create')} />
      </div>
    </div>
  );
}
