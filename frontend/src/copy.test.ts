import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from 'vitest';

function runtimeFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return entry.name === '__pycache__' ? [] : runtimeFiles(path);
    return /\.(tsx?|py)$/.test(entry.name) && !entry.name.includes('.test.') ? [path] : [];
  });
}

test('runtime copy uses upload/download and omits unnecessary re-upload reassurance', () => {
  const roots = [join(process.cwd(), 'src'), join(process.cwd(), '..', 'backend')];
  const violations = roots.flatMap(runtimeFiles).flatMap(path => {
    const text = readFileSync(path, 'utf8');
    return /unggah|unduh|(?:upload|mengirim) ulang (?:tidak diperlukan|tidak perlu)|tidak perlu (?:upload|mengirim) ulang/i.test(text) ? [path] : [];
  });
  expect(violations).toEqual([]);
});
