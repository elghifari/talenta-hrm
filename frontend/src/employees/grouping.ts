import type { Employee } from './types';

export type GroupKey = 'branch' | 'division';
export type GroupMode = 'both' | GroupKey | 'none';
export type EmployeeGroup = { key: string; kind: GroupKey; label: string; count: number; depth: number; children: GroupNode[] };
export type GroupNode = EmployeeGroup | Employee;
export function groupOptions(employees: Employee[], kind: GroupKey) {
  const options = new Map<string, string>();
  const owners = new Map<string, string>();
  for (const employee of employees) options.set(employee[kind] ?? '__unset__', employee[kind + '_name' as 'branch_name' | 'division_name'] || (kind === 'branch' ? 'Cabang belum ditentukan' : 'Divisi belum ditentukan'));
  if (kind === 'division') {
    for (const employee of employees) if (employee.division) owners.set(employee.division, employee.branch_name || 'Cabang belum ditentukan');
    const counts = new Map<string, number>();
    for (const label of options.values()) { const key = label.toLocaleLowerCase('id'); counts.set(key, (counts.get(key) ?? 0) + 1); }
    for (const [id, label] of options) if (id !== '__unset__' && (counts.get(label.toLocaleLowerCase('id')) ?? 0) > 1) options.set(id, label + ' (' + owners.get(id) + ')');
  }
  return [...options].sort(([a, labelA], [b, labelB]) => a === '__unset__' ? 1 : b === '__unset__' ? -1 : labelA.localeCompare(labelB, 'id'));
}
export function groupEmployees(employees: Employee[], mode: GroupMode, depth = 0, path: string[] = []): GroupNode[] {
  const keys: GroupKey[] = mode === 'both' ? ['branch', 'division'] : mode === 'none' ? [] : [mode];
  if (depth >= keys.length) return employees;
  const kind = keys[depth];
  return groupOptions(employees, kind).map(([value, label]) => {
    const members = employees.filter(employee => (employee[kind] ?? '__unset__') === value);
    const route = [...path, kind + ':' + value];
    return { key: route.join('/'), label, kind, count: members.length, depth, children: groupEmployees(members, mode, depth + 1, route) };
  });
}
export function collectGroups(nodes: GroupNode[]): string[] {
  return nodes.flatMap(node => 'children' in node ? [node.key, ...collectGroups(node.children)] : []);
}